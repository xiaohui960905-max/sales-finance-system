import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime

from database import query_db, query_one


def show_settings():
    st.header("⚙️ 基础设置")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["产品分类", "产品管理", "销售人员", "客户来源", "销售目标", "数据管理"])

    with tab1:
        _show_category_settings()
    with tab2:
        _show_product_settings()
    with tab3:
        _show_salesperson_settings()
    with tab4:
        _show_source_settings()
    with tab5:
        _show_target_settings()
    with tab6:
        _show_data_management()


def _show_category_settings():
    st.subheader("产品分类管理")
    new_cat = st.text_input("新增分类名称", key="new_cat")
    if st.button("添加分类", key="add_cat"):
        if new_cat:
            try:
                query_db("INSERT INTO product_categories (name) VALUES (?)", (new_cat,), fetch=False)
                st.success("分类添加成功！")
                st.rerun()
            except Exception:
                st.error("分类已存在！")

    cats = query_db("SELECT id, name FROM product_categories ORDER BY id")
    if cats:
        df = pd.DataFrame(cats, columns=['编号', '分类名称'])
        st.dataframe(df, use_container_width=True)


def _show_product_settings():
    st.subheader("产品管理")

    cats = query_db("SELECT id, name FROM product_categories")
    cat_opts = {c["name"]: c["id"] for c in cats}
    if not cat_opts:
        st.warning("请先在产品分类中添加分类！")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_cat = st.selectbox("产品分类", list(cat_opts.keys()), key="prod_cat")
    with c2:
        prod_name = st.text_input("产品名称", key="prod_name")
    with c3:
        cost_price = st.number_input("成本价", min_value=0.0, value=0.0, key="prod_cost")
    with c4:
        sale_price = st.number_input("售价", min_value=0.0, value=0.0, key="prod_price")

    if st.button("添加产品", key="add_prod"):
        if sel_cat and prod_name:
            try:
                query_db(
                    "INSERT INTO products (category_id, name, cost_price, sale_price) VALUES (?, ?, ?, ?)",
                    (cat_opts[sel_cat], prod_name, cost_price, sale_price),
                    fetch=False
                )
                st.success("产品添加成功！")
                st.rerun()
            except Exception as e:
                st.error(f"添加失败：{e}")

    prods = query_db(
        """SELECT p.id, c.name, p.name, p.cost_price, p.sale_price
           FROM products p JOIN product_categories c ON p.category_id = c.id ORDER BY p.id"""
    )
    if prods:
        df = pd.DataFrame(prods, columns=['编号', '分类', '产品名称', '成本价', '售价'])
        st.dataframe(df, use_container_width=True)

        # 删除产品
        st.subheader("删除产品")
        del_opts = {f"{p['name']} (ID: {p['id']})": p["id"] for p in query_db("SELECT id, name FROM products")}
        if del_opts:
            sel_del = st.selectbox("选择要删除的产品", list(del_opts.keys()), key="del_prod")
            if st.button("删除产品", type="secondary", key="btn_del_prod"):
                prod_id = del_opts[sel_del]
                related = query_db("SELECT COUNT(*) as cnt FROM orders WHERE product_id = ?", (prod_id,))
                if related and related[0]["cnt"] > 0:
                    st.warning(f"该产品有 {related[0]['cnt']} 条关联订单，无法删除！")
                else:
                    query_db("DELETE FROM products WHERE id=?", (prod_id,), fetch=False)
                    st.success("产品已删除！")
                    st.rerun()


def _show_salesperson_settings():
    st.subheader("销售人员管理")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sp_name = st.text_input("姓名", key="sp_name")
    with c2:
        sp_phone = st.text_input("电话", key="sp_phone")
    with c3:
        sp_base = st.number_input("底薪", min_value=0.0, value=0.0, key="sp_base")
    with c4:
        sp_comm = st.number_input("提成比例", min_value=0.0, max_value=1.0, value=0.05, key="sp_comm")

    if st.button("添加销售人员", key="add_sp"):
        if sp_name:
            try:
                query_db(
                    "INSERT INTO salespersons (name, phone, base_salary, commission_rate) VALUES (?, ?, ?, ?)",
                    (sp_name, sp_phone, sp_base, sp_comm),
                    fetch=False
                )
                st.success("销售人员添加成功！")
                st.rerun()
            except Exception as e:
                st.error(f"添加失败：{e}")

    sps = query_db("SELECT id, name, phone, base_salary, commission_rate FROM salespersons ORDER BY id")
    if sps:
        df = pd.DataFrame(sps, columns=['编号', '姓名', '电话', '底薪', '提成比例'])
        st.dataframe(df, use_container_width=True)

        # 删除销售人员
        st.subheader("删除销售人员")
        sp_opts = {f"{s['name']} (ID: {s['id']})": s["id"] for s in sps}
        sel_sp = st.selectbox("选择要删除的销售人员", list(sp_opts.keys()), key="del_sp")

        if st.button("删除销售人员", key="btn_del_sp", type="secondary"):
            sp_id = sp_opts[sel_sp]
            related = query_db("SELECT COUNT(*) as cnt FROM orders WHERE salesperson_id = ?", (sp_id,))
            if related and related[0]["cnt"] > 0:
                st.warning(f"该销售人员有 {related[0]['cnt']} 条关联订单，无法删除！请先删除或转移关联订单。")
            else:
                query_db("DELETE FROM salespersons WHERE id = ?", (sp_id,), fetch=False)
                st.success("销售人员删除成功！")
                st.rerun()


def _show_source_settings():
    st.subheader("客户来源管理")
    new_src = st.text_input("新增来源名称", key="new_src")
    if st.button("添加来源", key="add_src"):
        if new_src:
            try:
                query_db("INSERT INTO customer_sources (name) VALUES (?)", (new_src,), fetch=False)
                st.success("来源添加成功！")
                st.rerun()
            except Exception:
                st.error("来源已存在！")

    srcs = query_db("SELECT id, name FROM customer_sources ORDER BY id")
    if srcs:
        df = pd.DataFrame(srcs, columns=['编号', '来源名称'])
        st.dataframe(df, use_container_width=True)


def _show_target_settings():
    st.subheader("🎯 销售目标管理")

    # Month/year selector
    today = datetime.now()
    c1, c2 = st.columns(2)
    with c1:
        target_year = st.selectbox("年份", range(today.year - 1, today.year + 2),
                                    index=1, key="target_year")
    with c2:
        target_month = st.selectbox("月份", range(1, 13),
                                     index=today.month - 1, key="target_month")

    # Get all salespersons
    sps = query_db("SELECT id, name, base_salary FROM salespersons ORDER BY id")
    if not sps:
        st.info("请先添加销售人员")
        return

    # Get existing targets for this month
    existing = query_db(
        "SELECT salesperson_id, target_amount FROM sales_targets WHERE year=? AND month=?",
        (target_year, target_month)
    )
    existing_map = {r["salesperson_id"]: r["target_amount"] for r in existing}

    st.divider()
    st.caption(f"设定 {target_year} 年 {target_month} 月的销售目标")

    for sp in sps:
        sp_id = sp["id"]
        current_target = existing_map.get(sp_id, 0.0)
        c1, c2 = st.columns([3, 1])
        with c1:
            new_target = st.number_input(
                f"{sp['name']} 目标金额",
                min_value=0.0, value=current_target, step=1000.0,
                key=f"target_{sp_id}"
            )
        with c2:
            actual = query_one(
                """SELECT COALESCE(SUM(sales_amount), 0) as actual
                   FROM orders WHERE salesperson_id=?
                   AND strftime('%Y', date)=? AND strftime('%m', date)=?""",
                (sp_id, str(target_year), f"{target_month:02d}")
            )
            actual_val = actual[0] if actual else 0
            pct = round(actual_val / new_target * 100, 1) if new_target > 0 else 0
            st.metric("完成率", f"{pct}%")

    if st.button("💾 保存目标", type="primary", key="save_targets"):
        for sp in sps:
            sp_id = sp["id"]
            val = st.session_state.get(f"target_{sp_id}", 0.0)
            if val > 0:
                query_db(
                    """INSERT OR REPLACE INTO sales_targets
                       (salesperson_id, year, month, target_amount)
                       VALUES (?, ?, ?, ?)""",
                    (sp_id, target_year, target_month, val),
                    fetch=False
                )
        st.success("销售目标已保存！")
        st.rerun()

    # Show target history table
    st.divider()
    st.caption("目标设定记录")
    targets = query_db(
        """SELECT s.name, st.year, st.month, st.target_amount
           FROM sales_targets st JOIN salespersons s ON st.salesperson_id = s.id
           ORDER BY st.year DESC, st.month DESC, s.name"""
    )
    if targets:
        df = pd.DataFrame(targets, columns=["销售员", "年份", "月份", "目标金额"])
        df["目标金额"] = df["目标金额"].apply(lambda x: f"¥{x:,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)


def _show_data_management():
    st.subheader("💾 数据管理")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    if st.button("📥 一键备份", type="primary", key="btn_backup"):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"sales_backup_{ts}.db"
        shutil.copy2('sales.db', os.path.join(backup_dir, backup_file))
        st.success(f"备份成功！备份文件：{backup_file}")
        st.rerun()

    backup_files = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
    if not backup_files:
        st.info("暂无备份文件")
        return

    st.subheader("📁 备份文件列表")
    sel_backup = st.selectbox("选择备份文件", backup_files, key="sel_backup")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📤 一键恢复", type="secondary", key="btn_restore"):
            st.session_state.confirm_restore = True
    with c2:
        if st.session_state.get('confirm_restore'):
            if st.button("⚠️ 确认恢复（此操作将覆盖当前数据）", type="primary", key="confirm_restore_btn"):
                shutil.copy2(os.path.join(backup_dir, sel_backup), 'sales.db')
                st.session_state.confirm_restore = False
                st.success("恢复成功！请重新启动应用。")
                st.rerun()
            if st.button("取消", key="cancel_restore"):
                st.session_state.confirm_restore = False
                st.rerun()

    st.divider()
    st.subheader("最近备份")
    for f in backup_files[:5]:
        fp = os.path.join(backup_dir, f)
        size_kb = os.path.getsize(fp) / 1024
        st.info(f"{f} - {size_kb:.2f} KB")
