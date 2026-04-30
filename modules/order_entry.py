import streamlit as st
from datetime import datetime, date

from database import query_db, query_one
from utils import (
    parse_order_text, get_payment_status,
    generate_order_no, load_salesperson_options, load_product_options,
    load_source_options, try_save_customer, validate_phone
)


def _calc_order_preview(quantity, unit_price, cost_price, freight, other_costs,
                         commission_rate, deposit):
    """纯计算函数：返回订单预览数据，不渲染 UI"""
    sales_amount = round(quantity * unit_price, 2)
    cost = round(quantity * cost_price, 2)
    gross = round(sales_amount - cost, 2)
    commission = round(gross * commission_rate, 2)
    net_profit = round(gross - freight - other_costs - commission, 2)
    balance = round(sales_amount - deposit, 2)
    payment_status = get_payment_status(deposit, sales_amount)
    return sales_amount, cost, commission, net_profit, balance, payment_status


def _render_profit_preview(calc_result, freight, other_costs):
    """渲染利润预览 UI"""
    sales_amount, cost, commission, net_profit, balance, payment_status = calc_result

    st.subheader("💰 利润预览")
    cols = st.columns(6)
    cols[0].metric("总销售额", f"¥{sales_amount:,.2f}")
    cols[1].metric("总成本", f"¥{cost:,.2f}")
    cols[2].metric("运费", f"¥{freight:,.2f}")
    cols[3].metric("其他成本", f"¥{other_costs:,.2f}")
    cols[4].metric("提成", f"¥{commission:,.2f}")
    cols[5].metric("净利润", f"¥{net_profit:,.2f}")
    st.info(f"尾款: ¥{balance:,.2f} | 收款状态: {payment_status}")


def _submit_order(date_val, salesperson_name, product_name, quantity, unit_price,
                  cost_price, freight, other_costs, customer_name, customer_phone,
                  customer_address, source_name, deposit, remark, original_text,
                  sp_options, prod_options, source_options):
    """统一的订单提交逻辑"""
    sp_id, commission_rate = sp_options[salesperson_name]
    prod_id, _, _ = prod_options[product_name]
    source_id = source_options.get(source_name) if source_name else None

    calc_result = _calc_order_preview(quantity, unit_price, cost_price, freight,
                                       other_costs, commission_rate, deposit)
    sales_amount, cost, commission, net_profit, balance, payment_status = calc_result

    if not st.button("确认提交", type="primary", key=f"submit_{datetime.now().timestamp()}"):
        return False

    if not validate_phone(customer_phone):
        st.error("手机号格式不正确！")
        return False

    order_no = generate_order_no()
    try:
        query_db(
            """INSERT INTO orders
               (order_no, date, salesperson_id, product_id, quantity, unit_price,
                sales_amount, cost, freight, other_costs, commission, profit, customer_name,
                customer_phone, customer_address, source_id, deposit, balance,
                payment_status, original_text, remark)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_no, date_val.strftime('%Y-%m-%d'), sp_id, prod_id, quantity,
             unit_price, sales_amount, cost, freight, other_costs, commission, net_profit,
             customer_name, customer_phone, customer_address, source_id, deposit,
             balance, payment_status, original_text, remark),
            fetch=False
        )
        st.success(f"订单提交成功！订单号：{order_no}")
        try_save_customer(customer_name, customer_phone, customer_address, source_name or '')
        return True
    except Exception as e:
        st.error(f"提交失败：{e}")
        return False


def show_order_entry():
    st.header("📝 订单录入")

    sp_options = load_salesperson_options()
    if not sp_options:
        st.warning("请先在基础设置中添加销售人员！")
        st.stop()

    prod_options = load_product_options()
    source_options = load_source_options()

    tab1, tab2 = st.tabs(["📋 粘贴识别", "✍️ 手动录入"])

    # ========== Tab1: 粘贴识别 ==========
    with tab1:
        raw_text = st.text_area(
            "粘贴订单文本", height=200,
            placeholder="请粘贴订单文本，例如：\n日期：4.28张三\n型号：60型粗糠单碾米机\n金额：3500\n定金：1000\n地址：湖南省长沙市岳麓区XX路XX号\n李四。13800138000"
        )

        if 'parsed_data' not in st.session_state:
            st.session_state.parsed_data = None

        if st.button("识别订单", type="primary", key="parse_btn"):
            if raw_text and raw_text.strip():
                st.session_state.parsed_data = parse_order_text(raw_text)
            else:
                st.warning("请先粘贴订单文本")

        if st.session_state.parsed_data is not None:
            parsed = st.session_state.parsed_data
            st.subheader("✏️ 请补全信息并提交")

            # Show original text for comparison
            with st.expander("📄 查看原始文本"):
                st.text(raw_text if raw_text else "(空)")

            c1, c2 = st.columns(2)
            with c1:
                parsed_date = st.date_input(
                    "订单日期",
                    parsed['date'] if isinstance(parsed.get('date'), date) else datetime.now(),
                    key="p_date"
                )
                sp_names = list(sp_options.keys())
                # 智能匹配销售员
                sp_idx = 0
                if parsed.get('salesman'):
                    for i, n in enumerate(sp_names):
                        if parsed['salesman'] in n or n in parsed['salesman']:
                            sp_idx = i
                            break
                selected_sp = st.selectbox("销售员", sp_names, index=sp_idx, key="p_sp")

                prod_names = list(prod_options.keys())
                prod_idx = 0
                if parsed.get('product'):
                    for i, n in enumerate(prod_names):
                        if parsed['product'] in n or n in parsed['product']:
                            prod_idx = i
                            break
                selected_prod = st.selectbox("产品", prod_names, index=prod_idx, key="p_prod") if prod_names else None
                quantity = st.number_input("数量", min_value=1, value=1, key="p_qty")

            with c2:
                default_price = prod_options[selected_prod][2] if selected_prod else 0.0
                default_cost = prod_options[selected_prod][1] if selected_prod else 0.0

                unit_price = st.number_input("单价", min_value=0.0,
                    value=parsed.get('amount', default_price) or default_price, key="p_price")
                cost_price = st.number_input("成本价", min_value=0.0, value=default_cost, key="p_cost")
                freight = st.number_input("运费", min_value=0.0, value=0.0, key="p_freight")
                other_costs = st.number_input("其他成本支出", min_value=0.0, value=0.0, key="p_other")

                customer_name = st.text_input("客户姓名", value=parsed.get('customer_name', ''), key="p_cname")
                customer_phone = st.text_input("客户电话", value=parsed.get('customer_phone', ''), key="p_cphone")
                customer_address = st.text_area("客户地址", value=parsed.get('address', ''), key="p_caddr")

                src_names = list(source_options.keys())
                selected_source = st.selectbox("客户来源", src_names, key="p_src") if src_names else None

                deposit = st.number_input("定金", min_value=0.0,
                    value=parsed.get('deposit', 0.0) or 0.0, key="p_deposit")
                remark = st.text_area("备注", value=raw_text, key="p_remark")

            if selected_prod and selected_sp:
                sp_id, comm_rate = sp_options[selected_sp]
                calc_result = _calc_order_preview(
                    quantity, unit_price, cost_price, freight, other_costs,
                    comm_rate, deposit
                )
                _render_profit_preview(calc_result, freight, other_costs)
                if _submit_order(parsed_date, selected_sp, selected_prod, quantity, unit_price,
                                 cost_price, freight, other_costs, customer_name, customer_phone,
                                 customer_address, selected_source, deposit, remark, raw_text,
                                 sp_options, prod_options, source_options):
                    st.session_state.parsed_data = None
                    st.rerun()

    # ========== Tab2: 手动录入 ==========
    with tab2:
        _show_manual_form(sp_options, prod_options, source_options)


def _show_manual_form(sp_options, prod_options, source_options):
    """手动录入表单"""
    # Track previous product selection to auto-update price/cost
    if "m_prev_prod" not in st.session_state:
        st.session_state.m_prev_prod = None

    c1, c2 = st.columns(2)
    with c1:
        order_date = st.date_input("订单日期", datetime.now(), key="m_date")
        sp_names = list(sp_options.keys())
        selected_sp = st.selectbox("销售员", sp_names, key="m_sp")
        prod_names = list(prod_options.keys())
        selected_prod = st.selectbox("产品", prod_names, key="m_prod") if prod_names else None
        quantity = st.number_input("数量", min_value=1, value=1, key="m_qty")

    # Auto-fill price/cost when product changes
    if selected_prod and selected_prod != st.session_state.m_prev_prod:
        st.session_state.m_price = prod_options[selected_prod][2]
        st.session_state.m_cost = prod_options[selected_prod][1]
        st.session_state.m_prev_prod = selected_prod

    with c2:
        unit_price = st.number_input("单价", min_value=0.0, key="m_price")
        cost_price = st.number_input("成本价", min_value=0.0, key="m_cost")
        freight = st.number_input("运费", min_value=0.0, value=0.0, key="m_freight")
        other_costs = st.number_input("其他成本支出", min_value=0.0, value=0.0, key="m_other")

        customer_name = st.text_input("客户姓名", key="m_cname")
        customer_phone = st.text_input("客户电话", key="m_cphone")
        customer_address = st.text_area("客户地址", key="m_caddr")

        src_names = list(source_options.keys())
        selected_source = st.selectbox("客户来源", src_names, key="m_src") if src_names else None

        deposit = st.number_input("定金", min_value=0.0, value=0.0, key="m_deposit")
        remark = st.text_area("备注", key="m_remark")

    if selected_prod and selected_sp:
        sp_id, comm_rate = sp_options[selected_sp]
        calc_result = _calc_order_preview(
            quantity, unit_price, cost_price, freight, other_costs,
            comm_rate, deposit
        )
        _render_profit_preview(calc_result, freight, other_costs)
        if _submit_order(order_date, selected_sp, selected_prod, quantity, unit_price,
                         cost_price, freight, other_costs, customer_name, customer_phone,
                         customer_address, selected_source, deposit, remark, '',
                         sp_options, prod_options, source_options):
            st.rerun()
