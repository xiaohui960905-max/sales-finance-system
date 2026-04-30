import streamlit as st
import pandas as pd

from database import query_db, query_one
from utils import export_excel, load_source_options


def show_customer_mgmt():
    st.header("👥 客户管理")

    search = st.text_input("搜索客户", placeholder="输入客户姓名或电话")

    # 新增客户
    with st.expander("➕ 新增客户"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("客户姓名", key="new_cust_name")
            new_phone = st.text_input("客户电话", key="new_cust_phone")
            new_addr = st.text_area("客户地址", key="new_cust_addr")
        with c2:
            srcs = load_source_options()
            src_list = list(srcs.keys())
            new_src = st.selectbox("客户来源", src_list, key="new_cust_src") if src_list else None
            new_notes = st.text_area("备注", key="new_cust_notes")

        if st.button("保存客户", type="primary", key="save_new_cust"):
            if not new_name or not new_phone:
                st.warning("请填写姓名和电话")
            else:
                try:
                    query_db(
                        "INSERT INTO customers (name, phone, address, source, remark) VALUES (?, ?, ?, ?, ?)",
                        (new_name, new_phone, new_addr, new_src or '', new_notes),
                        fetch=False
                    )
                    st.success("客户添加成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"添加失败：{e}")

    # 客户列表
    base_query = """SELECT c.id, c.name, c.phone, c.address, c.source, c.remark, c.created_at,
                           COUNT(o.id) as order_count,
                           COALESCE(SUM(o.sales_amount), 0) as total_spent
                    FROM customers c
                    LEFT JOIN orders o ON c.phone = o.customer_phone"""
    if search:
        customers = query_db(
            base_query + " WHERE c.name LIKE ? OR c.phone LIKE ?"
            " GROUP BY c.id ORDER BY c.created_at DESC",
            (f"%{search}%", f"%{search}%")
        )
    else:
        customers = query_db(
            base_query + " GROUP BY c.id ORDER BY c.created_at DESC"
        )

    df = pd.DataFrame(customers, columns=['编号', '姓名', '电话', '地址', '来源', '备注', '创建时间', '订单数', '累计消费'])
    st.dataframe(df, use_container_width=True)

    # 导出
    if not df.empty:
        output, filename = export_excel(df, '客户列表', '客户列表')
        st.download_button(
            label="📥 导出客户列表",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 选择客户查看详情
        choices = [f"{r['姓名']} - {r['电话']}" for _, r in df.iterrows()]
        sel = st.selectbox("选择客户查看详情", choices, key="cust_select")
        if sel:
            idx = choices.index(sel)
            row = df.iloc[idx]
            cust_id = int(row['编号'])

            st.subheader(f"📋 {row['姓名']} 的详情")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"**姓名**：{row['姓名']}")
                st.info(f"**电话**：{row['电话']}")
                st.info(f"**来源**：{row['来源']}")
            with c2:
                st.info(f"**地址**：{row['地址']}")
                st.info(f"**备注**：{row['备注']}")
                st.info(f"**创建时间**：{row['创建时间']}")

            # 历史订单
            st.subheader("📦 历史订单")
            cust_orders = query_db(
                """SELECT o.order_no, o.date, p.name, o.sales_amount, o.profit, o.payment_status
                   FROM orders o JOIN products p ON o.product_id = p.id
                   WHERE o.customer_phone = ? ORDER BY o.date DESC""",
                (str(row['电话']),)
            )
            if cust_orders:
                df_orders = pd.DataFrame(cust_orders, columns=['订单号', '日期', '产品', '销售额', '利润', '收款状态'])
                st.dataframe(df_orders, use_container_width=True)
            else:
                st.info("暂无订单记录")

            # 编辑客户
            with st.expander("✏️ 编辑客户"):
                edit_name = st.text_input("姓名", value=str(row['姓名']), key="edit_cust_name")
                edit_phone = st.text_input("电话", value=str(row['电话']), key="edit_cust_phone")
                edit_addr = st.text_area("地址", value=str(row['地址']), key="edit_cust_addr")
                edit_notes = st.text_area("备注", value=str(row['备注']), key="edit_cust_notes")

                if st.button("保存修改", type="primary", key="save_edit_cust"):
                    query_db(
                        "UPDATE customers SET name=?, phone=?, address=?, notes=? WHERE id=?",
                        (edit_name, edit_phone, edit_addr, edit_notes, cust_id),
                        fetch=False
                    )
                    st.success("客户信息已更新！")
                    st.rerun()

            # 删除客户
            with st.expander("🗑️ 删除客户"):
                st.warning(f"确定要删除客户 {row['姓名']} 吗？")
                if st.button("确认删除", type="secondary", key="del_cust"):
                    query_db("DELETE FROM customers WHERE id=?", (cust_id,), fetch=False)
                    st.success("客户已删除！")
                    st.rerun()
