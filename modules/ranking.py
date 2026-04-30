import streamlit as st
import pandas as pd
from datetime import datetime

from database import query_db
from utils import get_sales_ranking, export_excel


def _medal(rank):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return medals.get(rank, f"  {rank}")


MEDALS = ["🥇", "🥈", "🥉"]


def show_ranking():
    st.header("🏆 排行榜")

    period = st.radio("统计周期", ["今日", "本月", "本年"], horizontal=True, key="rank_period")
    period_map = {"今日": "today", "本月": "month", "本年": "year"}
    period_code = period_map[period]

    period_cond = {
        "today": "date = date('now')",
        "month": "strftime('%Y-%m', date) = strftime('%Y-%m', 'now')",
        "year": "strftime('%Y', date) = strftime('%Y', 'now')",
    }
    condition = period_cond[period_code]

    tab1, tab2, tab3 = st.tabs(["销售额排行", "提成排行", "薪酬汇总"])

    # ════ Tab 1: 销售额排行 ════
    with tab1:
        df_rank = get_sales_ranking(period_code)
        if not df_rank.empty:
            df_rank.insert(0, '排名', range(1, len(df_rank) + 1))

            # Top 3 cards
            top3 = df_rank.head(3)
            c1, c2, c3 = st.columns(3)
            for i, (col, (_, row)) in enumerate(zip([c1, c2, c3], top3.iterrows())):
                with col:
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
                                padding:1rem;text-align:center;">
                        <div style="font-size:2rem;">{MEDALS[i]}</div>
                        <div style="font-weight:700;font-size:1rem;color:#1F2937;">{row['salesman']}</div>
                        <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.25rem;">销售额</div>
                        <div style="font-weight:700;font-size:1.1rem;color:#1677FF;">
                            ¥{row['total_sales']:,.0f}
                        </div>
                        <div style="font-size:0.75rem;color:#9CA3AF;">利润 ¥{row['total_profit']:,.0f}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            df_display = df_rank.rename(columns={
                'salesman': '销售员',
                'total_sales': '销售额',
                'total_profit': '利润'
            })
            df_display['排名'] = [_medal(r) for r in df_display['排名']]
            st.dataframe(
                df_display[['排名', '销售员', '销售额', '利润']],
                use_container_width=True, hide_index=True,
                column_config={
                    '排名': st.column_config.TextColumn(width='small'),
                    '销售额': st.column_config.NumberColumn(format='¥%.2f'),
                    '利润': st.column_config.NumberColumn(format='¥%.2f'),
                }
            )
        else:
            st.info("暂无数据")

    # ════ Tab 2: 提成排行 ════
    with tab2:
        rows = query_db(f"""
            SELECT s.name, COALESCE(SUM(o.commission), 0) as total_commission,
                   COUNT(o.id) as orders
            FROM salespersons s
            LEFT JOIN orders o ON s.id = o.salesperson_id AND {condition}
            GROUP BY s.id, s.name
            ORDER BY total_commission DESC
        """)

        if rows and any(r["total_commission"] > 0 for r in rows):
            df_comm = pd.DataFrame(rows, columns=["销售员", "提成金额", "订单数"])

            top3_comm = df_comm.head(3)
            c1, c2, c3 = st.columns(3)
            for i, (col, (_, row)) in enumerate(zip([c1, c2, c3], top3_comm.iterrows())):
                with col:
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
                                padding:1rem;text-align:center;">
                        <div style="font-size:2rem;">{MEDALS[i]}</div>
                        <div style="font-weight:700;font-size:1rem;color:#1F2937;">{row['销售员']}</div>
                        <div style="font-size:0.75rem;color:#9CA3AF;margin-top:0.25rem;">提成金额</div>
                        <div style="font-weight:700;font-size:1.1rem;color:#1677FF;">
                            ¥{row['提成金额']:,.2f}
                        </div>
                        <div style="font-size:0.75rem;color:#9CA3AF;">{row['订单数']} 笔订单</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            df_comm['排名'] = [_medal(i) for i in range(1, len(df_comm) + 1)]
            st.dataframe(
                df_comm[['排名', '销售员', '提成金额', '订单数']],
                use_container_width=True, hide_index=True,
                column_config={
                    '排名': st.column_config.TextColumn(width='small'),
                    '提成金额': st.column_config.NumberColumn(format='¥%.2f'),
                }
            )
        else:
            st.info("暂无提成数据")

    # ════ Tab 3: 薪酬汇总 ════
    with tab3:
        today = datetime.now()
        c1, c2 = st.columns(2)
        with c1:
            payroll_year = st.selectbox("年份", range(today.year - 1, today.year + 2),
                                         index=1, key="payroll_year")
        with c2:
            payroll_month = st.selectbox("月份", range(1, 13),
                                          index=today.month - 1, key="payroll_month")
        month_str = f"{payroll_year}-{payroll_month:02d}"

        rows = query_db(f"""
            SELECT s.name, s.base_salary,
                   COALESCE(SUM(o.commission), 0) as total_commission
            FROM salespersons s
            LEFT JOIN orders o ON s.id = o.salesperson_id
                AND strftime('%Y-%m', o.date) = '{month_str}'
            GROUP BY s.id, s.name, s.base_salary
            ORDER BY total_commission DESC
        """)

        if rows and any(r["base_salary"] or r["total_commission"] for r in rows):
            df_payroll = pd.DataFrame(rows, columns=["销售员", "底薪", "提成"])
            df_payroll["应发合计"] = df_payroll["底薪"] + df_payroll["提成"]
            total_pay = df_payroll["应发合计"].sum()

            st.markdown(
                f'<p style="color:#6B7280;font-size:0.8rem;margin:0.5rem 0;">'
                f'{month_str} 薪酬汇总 · 应发合计 '
                f'<b style="color:#1677FF;">¥{total_pay:,.2f}</b></p>',
                unsafe_allow_html=True,
            )

            st.dataframe(
                df_payroll,
                use_container_width=True, hide_index=True,
                column_config={
                    '底薪': st.column_config.NumberColumn(format='¥%.2f'),
                    '提成': st.column_config.NumberColumn(format='¥%.2f'),
                    '应发合计': st.column_config.NumberColumn(format='¥%.2f'),
                }
            )

            output, filename = export_excel(df_payroll, '薪酬汇总', f'薪酬汇总_{month_str}')
            st.download_button(
                label="📥 导出薪酬报表",
                data=output,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("暂无薪酬数据")
