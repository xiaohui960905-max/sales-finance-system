import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from database import query_db, query_one
from utils import export_excel, load_salesperson_options, load_product_options
from utils import get_payment_status


def show_order_list():
    st.header("📋 订单列表")

    # Initialize date range in session state
    today = datetime.now().date()
    if "ol_start" not in st.session_state:
        st.session_state.ol_start = today - timedelta(days=30)
    if "ol_end" not in st.session_state:
        st.session_state.ol_end = today

    # Quick date presets
    st.caption("快捷日期")
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    cq1, cq2, cq3, cq4, cq5, cq6, cq7 = st.columns(7)
    with cq1:
        if st.button("今天", key="q_today", use_container_width=True):
            st.session_state.ol_start = today; st.session_state.ol_end = today
    with cq2:
        if st.button("昨天", key="q_yday", use_container_width=True):
            yday = today - timedelta(days=1)
            st.session_state.ol_start = yday; st.session_state.ol_end = yday
    with cq3:
        if st.button("本周", key="q_week", use_container_width=True):
            st.session_state.ol_start = week_start; st.session_state.ol_end = today
    with cq4:
        if st.button("本月", key="q_month", use_container_width=True):
            st.session_state.ol_start = month_start; st.session_state.ol_end = today
    with cq5:
        if st.button("近30天", key="q_30d", use_container_width=True):
            st.session_state.ol_start = today - timedelta(days=30); st.session_state.ol_end = today
    with cq6:
        if st.button("全部", key="q_all", use_container_width=True):
            st.session_state.ol_start = today - timedelta(days=3650); st.session_state.ol_end = today

    # Date inputs (synced with session state)
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("开始日期", st.session_state.ol_start, key="ol_start")
    with c2:
        end_date = st.date_input("结束日期", st.session_state.ol_end, key="ol_end")

    # 筛选条件行2
    sp_dict = {"全部": 0}
    for r in query_db("SELECT id, name FROM salespersons ORDER BY id"):
        sp_dict[r["name"]] = r["id"]

    prod_dict = {"全部": 0}
    for r in query_db("SELECT id, name FROM products ORDER BY id"):
        prod_dict[r["name"]] = r["id"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_sp = st.selectbox("销售员", list(sp_dict.keys()), key="filter_sp")
    with c2:
        sel_prod = st.selectbox("产品", list(prod_dict.keys()), key="filter_prod")
    with c3:
        sel_status = st.selectbox("收款状态", ["全部", "待收款", "部分收款", "已收齐"], key="filter_status")
    with c4:
        customer_search = st.text_input("客户搜索", placeholder="姓名或电话", key="filter_customer")

    # 构建查询
    query = """SELECT o.id, o.order_no, o.date, s.name as sp_name, p.name as prod_name,
                      o.quantity, o.unit_price, o.sales_amount, o.cost, o.freight, o.other_costs,
                      o.commission, o.profit, o.deposit, o.balance, o.payment_status,
                      o.customer_name, o.customer_phone, o.customer_address,
                      COALESCE(cs.name, '') as source_name, o.remark
               FROM orders o
               LEFT JOIN salespersons s ON o.salesperson_id = s.id
               LEFT JOIN products p ON o.product_id = p.id
               LEFT JOIN customer_sources cs ON o.source_id = cs.id
               WHERE o.date BETWEEN ? AND ?"""
    params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]

    if sp_dict[sel_sp] != 0:
        query += " AND o.salesperson_id = ?"
        params.append(sp_dict[sel_sp])
    if prod_dict[sel_prod] != 0:
        query += " AND o.product_id = ?"
        params.append(prod_dict[sel_prod])
    if sel_status != "全部":
        query += " AND o.payment_status = ?"
        params.append(sel_status)
    if customer_search:
        query += " AND (o.customer_name LIKE ? OR o.customer_phone LIKE ?)"
        params.extend([f"%{customer_search}%", f"%{customer_search}%"])

    query += " ORDER BY o.date DESC, o.id DESC"

    orders = query_db(query, params)
    columns = ['编号', '订单号', '日期', '销售员', '产品', '数量', '单价', '销售额', '成本', '运费',
               '其他成本', '提成', '利润', '定金', '尾款', '收款状态',
               '客户姓名', '客户电话', '客户地址', '来源', '备注']
    df_orders = pd.DataFrame(orders, columns=columns)

    # Summary stats
    if not df_orders.empty:
        total_count = len(df_orders)
        total_sales = df_orders['销售额'].sum()
        total_profit = df_orders['利润'].sum()
        total_balance = df_orders['尾款'].sum()
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("订单数", f"{total_count} 笔")
        sc2.metric("销售额", f"¥{total_sales:,.2f}")
        sc3.metric("利润", f"¥{total_profit:,.2f}")
        sc4.metric("应收尾款", f"¥{total_balance:,.2f}")
    else:
        st.info("暂无匹配的订单数据")

    # Payment status highlighting + overdue days
    if not df_orders.empty:
        status_map = {"已收齐": "🟢 已收齐", "部分收款": "🟡 部分收款", "待收款": "🔴 待收款"}
        df_orders['收款状态'] = df_orders['收款状态'].map(status_map).fillna(df_orders['收款状态'])

        # Overdue days for unpaid/partial orders
        today = datetime.now().date()
        def calc_overdue(row):
            if row['收款状态'] in ['🔴 待收款', '🟡 部分收款']:
                order_date = datetime.strptime(str(row['日期']), '%Y-%m-%d').date()
                days = (today - order_date).days
                return days if days > 0 else 0
            return 0
        df_orders['逾期天数'] = df_orders.apply(calc_overdue, axis=1)

    st.dataframe(
        df_orders[['编号', '订单号', '日期', '销售员', '产品', '数量',
                   '销售额', '利润', '定金', '尾款', '收款状态', '逾期天数', '客户姓名', '客户电话']],
        use_container_width=True,
        column_config={
            '逾期天数': st.column_config.NumberColumn(format='%d 天'),
        }
    )

    # 导出按钮
    if not df_orders.empty:
        output, filename = export_excel(df_orders, '订单列表', '订单列表')
        st.download_button(
            label="📥 导出Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.divider()

        # 选择订单编辑
        order_choices = [f"{r['订单号']} - {r['客户姓名']}" for _, r in df_orders.iterrows()]
        selected_order = st.selectbox("选择订单进行管理", order_choices, key="ol_select")

        if selected_order:
            idx = order_choices.index(selected_order)
            row = df_orders.iloc[idx]
            order_id = int(row['编号'])

            _show_order_editor(row, order_id, sp_dict, prod_dict)

    # 删除记录
    with st.expander("🗑️ 回收站"):
        deleted = query_db(
            """SELECT id, order_id, order_no, date, customer_name, customer_phone,
                      sales_amount, profit, deposit, deleted_at
               FROM deleted_orders ORDER BY deleted_at DESC"""
        )
        if deleted:
            st.caption(f"共 {len(deleted)} 条已删除订单")
            df_del = pd.DataFrame(deleted, columns=['回收ID', '原订单ID', '订单号', '日期', '客户姓名', '客户电话',
                                                     '销售额', '利润', '定金', '删除时间'])
            st.dataframe(df_del, use_container_width=True, hide_index=True)

            st.divider()
            restore_opts = {f"{r['order_no']} - {r['customer_name']} - ¥{r['sales_amount']}": r['id'] for r in deleted}
            sel_restore = st.selectbox("选择要恢复的订单", list(restore_opts.keys()), key="restore_select")

            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("🔄 恢复订单", type="primary", key="btn_restore"):
                    del_id = restore_opts[sel_restore]
                    deleted_row = query_one("SELECT * FROM deleted_orders WHERE id = ?", (del_id,))
                    if deleted_row:
                        # 恢复到 orders 表（使用原订单号，避免冲突则新生成）
                        restore_order_no = deleted_row["order_no"]
                        existing = query_one("SELECT id FROM orders WHERE order_no = ?", (restore_order_no,))
                        if existing:
                            from utils import generate_order_no
                            restore_order_no = generate_order_no()

                        query_db(
                            """INSERT INTO orders
                               (order_no, date, salesperson_id, product_id, quantity, unit_price,
                                sales_amount, cost, freight, other_costs, commission, profit, customer_name,
                                customer_phone, customer_address, source_id, deposit, balance,
                                payment_status, original_text, remark)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (restore_order_no, deleted_row["date"], deleted_row["salesperson_id"],
                             deleted_row["product_id"], deleted_row["quantity"], deleted_row["unit_price"],
                             deleted_row["sales_amount"], deleted_row["cost"], deleted_row["freight"],
                             deleted_row["other_costs"], deleted_row["commission"], deleted_row["profit"],
                             deleted_row["customer_name"], deleted_row["customer_phone"],
                             deleted_row["customer_address"], deleted_row["source_id"], deleted_row["deposit"],
                             deleted_row["balance"], deleted_row["payment_status"],
                             deleted_row["original_text"], deleted_row["remark"]),
                            fetch=False
                        )
                        query_db("DELETE FROM deleted_orders WHERE id = ?", (del_id,), fetch=False)
                        st.success(f"订单 {restore_order_no} 已恢复！")
                        st.rerun()
            with c2:
                if st.button("🗑️ 永久删除", type="secondary", key="btn_permanent_del"):
                    perm_del_id = restore_opts[sel_restore]
                    query_db("DELETE FROM deleted_orders WHERE id = ?", (perm_del_id,), fetch=False)
                    st.success("已永久删除！")
                    st.rerun()
        else:
            st.info("暂无删除记录")


def _show_order_editor(row, order_id, sp_dict, prod_dict):
    """订单编辑展开面板"""
    sp_names = list(sp_dict.keys())[1:]  # 去掉"全部"
    prod_names = list(prod_dict.keys())[1:]

    with st.expander("✏️ 编辑订单", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            date_val = datetime.strptime(str(row['日期']), '%Y-%m-%d')
            edit_date = st.date_input("订单日期", date_val, key="edit_date")
            sp_idx = sp_names.index(str(row['销售员'])) if str(row['销售员']) in sp_names else 0
            edit_sp = st.selectbox("销售员", sp_names, index=sp_idx, key="edit_sp")
            prod_idx = prod_names.index(str(row['产品'])) if str(row['产品']) in prod_names else 0
            edit_prod = st.selectbox("产品", prod_names, index=prod_idx, key="edit_prod")
            edit_qty = st.number_input("数量", min_value=1, value=int(row['数量']), key="edit_qty")

        with c2:
            edit_price = st.number_input("单价", min_value=0.0, value=float(row['单价']), key="edit_price")
            cost_each = float(row['成本']) / int(row['数量']) if int(row['数量']) > 0 else 0.0
            edit_cost = st.number_input("成本价", min_value=0.0, value=cost_each, key="edit_cost")
            edit_freight = st.number_input("运费", min_value=0.0, value=float(row['运费']), key="edit_freight")
            edit_other = st.number_input("其他成本支出", min_value=0.0, value=float(row['其他成本']), key="edit_other")

        edit_cname = st.text_input("客户姓名", value=str(row['客户姓名']), key="edit_cname")
        edit_cphone = st.text_input("客户电话", value=str(row['客户电话']), key="edit_cphone")

        with st.expander("✏️ 更多信息"):
            edit_caddr = st.text_area("客户地址", value=str(row.get('客户地址', '')), key="edit_caddr")
            edit_deposit = st.number_input("定金", min_value=0.0, value=float(row['定金']), key="edit_deposit")
            edit_remark = st.text_area("备注", value=str(row['备注']), key="edit_remark")

            # 获取产品售价/成本和销售员提成
            sp_row = query_one("SELECT commission_rate FROM salespersons WHERE name = ?", (edit_sp,))
            comm_rate = sp_row["commission_rate"] if sp_row else 0.05
            prod_row = query_one("SELECT cost_price, sale_price FROM products WHERE name = ?", (edit_prod,))

            sales_amount = round(edit_qty * edit_price, 2)
            cost = round(edit_qty * edit_cost, 2)
            gross = round(sales_amount - cost, 2)
            commission = round(gross * float(comm_rate), 2)
            profit = round(gross - edit_freight - edit_other - commission, 2)
            balance = round(sales_amount - edit_deposit, 2)
            payment_status = get_payment_status(edit_deposit, sales_amount)

            c_prev = st.columns(6)
            c_prev[0].metric("销售额", f"¥{sales_amount:,.2f}")
            c_prev[1].metric("成本", f"¥{cost:,.2f}")
            c_prev[2].metric("运费", f"¥{edit_freight:,.2f}")
            c_prev[3].metric("提成", f"¥{commission:,.2f}")
            c_prev[4].metric("净利润", f"¥{profit:,.2f}")
            c_prev[5].metric("尾款", f"¥{balance:,.2f}")

        # 操作按钮
        col_save, col_del = st.columns([3, 1])
        with col_save:
            if st.button("💾 保存修改", type="primary", key="save_edit"):
                sp_id = sp_dict.get(edit_sp, 0)
                prod_id = prod_dict.get(edit_prod, 0)
                query_db(
                    """UPDATE orders SET date=?, salesperson_id=?, product_id=?, quantity=?,
                       unit_price=?, sales_amount=?, cost=?, freight=?, other_costs=?,
                       commission=?, profit=?, customer_name=?, customer_phone=?,
                       customer_address=?, deposit=?, balance=?, payment_status=?, remark=?
                       WHERE id=?""",
                    (edit_date.strftime('%Y-%m-%d'), sp_id, prod_id, edit_qty, edit_price,
                     sales_amount, cost, edit_freight, edit_other, commission, profit,
                     edit_cname, edit_cphone, edit_caddr, edit_deposit, balance,
                     payment_status, edit_remark, order_id),
                    fetch=False
                )
                st.success("订单已更新！")
                st.rerun()
        with col_del:
            st.warning(f"⚠️ {row['订单号']}")
            if st.button("🗑️ 删除订单", type="secondary", key="delete_order"):
                # 先保存到删除记录
                query_db(
                    """INSERT INTO deleted_orders
                       (order_id, order_no, date, salesperson_id, product_id, quantity, unit_price,
                        sales_amount, cost, freight, other_costs, commission, profit, customer_name,
                        customer_phone, customer_address, source_id, deposit, balance,
                        payment_status, original_text, remark, deleted_at)
                       SELECT id, order_no, date, salesperson_id, product_id, quantity, unit_price,
                              sales_amount, cost, freight, other_costs, commission, profit, customer_name,
                              customer_phone, customer_address, source_id, deposit, balance,
                              payment_status, original_text, remark, datetime('now')
                       FROM orders WHERE id = ?""",
                    (order_id,), fetch=False
                )
                query_db("DELETE FROM orders WHERE id = ?", (order_id,), fetch=False)
                st.success("订单已删除！")
                st.rerun()
