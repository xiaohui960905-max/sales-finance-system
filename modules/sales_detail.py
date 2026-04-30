import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from database import query_db, query_one
from utils import load_salesperson_options

CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}


def show_sales_detail():
    st.header("👤 销售详情")

    sp_options = load_salesperson_options()
    if not sp_options:
        st.warning("请先在基础设置中添加销售人员！")
        st.stop()

    selected_sp = st.selectbox("选择销售员", list(sp_options.keys()), key="detail_sp")

    if not selected_sp:
        return

    sp_id = sp_options[selected_sp][0]

    period = st.radio("统计周期", ["今日", "本月", "本年"], horizontal=True, key="detail_period")

    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    if period == "今日":
        date_from = today_str
        date_to = today_str
    elif period == "本月":
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
        date_to = today_str
    else:
        date_from = today.replace(month=1, day=1).strftime('%Y-%m-%d')
        date_to = today_str

    row = query_one(
        """SELECT COALESCE(SUM(sales_amount), 0),
                  COALESCE(SUM(profit), 0),
                  COALESCE(SUM(commission), 0),
                  COUNT(*)
           FROM orders WHERE salesperson_id = ? AND date BETWEEN ? AND ?""",
        (sp_id, date_from, date_to)
    )

    if row:
        total_sales, total_profit, total_commission, order_count = row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("销售额", f"¥{total_sales:,.2f}")
        c2.metric("利润", f"¥{total_profit:,.2f}")
        c3.metric("提成", f"¥{total_commission:,.2f}")
        c4.metric("订单数", order_count)

    # Target completion
    st.divider()
    targets = query_db(
        """SELECT year, month, target_amount
           FROM sales_targets WHERE salesperson_id=?
           ORDER BY year DESC, month DESC""",
        (sp_id,)
    )
    if targets:
        st.subheader("🎯 目标完成情况")
        target_data = []
        for t in targets:
            actual = query_one(
                """SELECT COALESCE(SUM(sales_amount), 0)
                   FROM orders WHERE salesperson_id=?
                   AND strftime('%Y', date)=? AND strftime('%m', date)=?""",
                (sp_id, str(t["year"]), f"{t['month']:02d}")
            )
            actual_val = actual[0] if actual else 0
            target_val = t["target_amount"]
            pct = round(actual_val / target_val * 100, 1) if target_val > 0 else 0
            target_data.append({
                "月份": f"{t['year']}-{t['month']:02d}",
                "目标": f"¥{target_val:,.0f}",
                "实际": f"¥{actual_val:,.0f}",
                "完成率": pct,
                "状态": "✅" if pct >= 100 else ("⚠️" if pct >= 80 else "❌")
            })

        if target_data:
            df_targets = pd.DataFrame(target_data)
            # Progress bar for current month
            if target_data:
                current_pct = target_data[0]["完成率"]
                st.progress(min(current_pct / 100, 1.0))
                st.caption(f"本月目标完成率: {current_pct}%")
            st.dataframe(df_targets, use_container_width=True, hide_index=True)

    # 近30天趋势
    st.subheader("📊 近30天业绩趋势")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    trend = query_db(
        """SELECT date, SUM(sales_amount) as sales, SUM(profit) as profit
           FROM orders WHERE salesperson_id = ? AND date >= ?
           GROUP BY date ORDER BY date""",
        (sp_id, thirty_days_ago)
    )
    if trend:
        df_trend = pd.DataFrame(trend, columns=['日期', '销售额', '利润'])
        fig = px.line(df_trend, x='日期', y=['销售额', '利润'],
                      title=f'{selected_sp} 近30天业绩趋势')
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#6B7280"),
            margin=dict(l=8, r=8, t=36, b=8),
            dragmode=False,
            xaxis=dict(gridcolor="#F0F2F5", fixedrange=True),
            yaxis=dict(gridcolor="#F0F2F5", fixedrange=True),
        )
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    else:
        st.info("暂无趋势数据")
