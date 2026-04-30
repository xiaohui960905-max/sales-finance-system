import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import query_db
from utils import get_stats_by_date_range, calc_growth, get_daily_sales, get_product_sales

# ── Plotly 浅色模板 ──
CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False, "responsive": True}
CHART_MARGIN = dict(l=8, r=8, t=36, b=8)
FONT_FAMILY = "Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif"

PLOTLY_LIGHT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#6B7280", family=FONT_FAMILY),
    title=dict(font=dict(color="#1F2937", size=14, family=FONT_FAMILY)),
    xaxis=dict(gridcolor="#F0F2F5", zerolinecolor="#E5E7EB", linecolor="#E5E7EB", fixedrange=True),
    yaxis=dict(gridcolor="#F0F2F5", zerolinecolor="#E5E7EB", linecolor="#E5E7EB", fixedrange=True),
    legend=dict(font=dict(color="#6B7280")),
    margin=CHART_MARGIN,
    hoverlabel=dict(font_size=13, font_family=FONT_FAMILY),
    dragmode=False,
)

COLORS = ["#1677FF", "#52C41A", "#FA8C16", "#F5222D", "#722ED1", "#13C2C2", "#EB2F96"]


def _delta_str(current, previous, suffix=""):
    mom = calc_growth(current, previous)
    if mom is None:
        return "暂无对比"
    sign = "+" if mom >= 0 else ""
    return f"{sign}{mom:.1f}% ({suffix})"


def _section_label(text):
    st.markdown(
        f'<div class="kpi-section-label">{text}</div>',
        unsafe_allow_html=True,
    )


def _card_container():
    """返回一个带白色卡片样式的容器"""
    return st.container()


def show_dashboard():
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')

    this_month_start = today.replace(day=1).strftime('%Y-%m-%d')
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
    last_month_end = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

    this_year_start = today.replace(month=1, day=1).strftime('%Y-%m-%d')
    last_year_start = f"{today.year - 1}-01-01"
    last_year_end = f"{today.year - 1}-12-31"

    today_sales, today_profit, today_orders = get_stats_by_date_range(today_str, today_str)
    yesterday_sales, yesterday_profit, yesterday_orders = get_stats_by_date_range(yesterday, yesterday)
    month_sales, month_profit, month_orders = get_stats_by_date_range(this_month_start, today_str)
    last_month_sales, last_month_profit, last_month_orders = get_stats_by_date_range(last_month_start, last_month_end)
    year_sales, year_profit, year_orders = get_stats_by_date_range(this_year_start, today_str)
    last_year_sales, last_year_profit, last_year_orders = get_stats_by_date_range(last_year_start, last_year_end)

    # ════ 今日指标 ════
    _section_label("今日业绩")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("今日销售额", f"¥{today_sales:,.2f}", delta=_delta_str(today_sales, yesterday_sales, "环比"))
    c2.metric("今日利润", f"¥{today_profit:,.2f}", delta=_delta_str(today_profit, yesterday_profit, "环比"))
    c3.metric("今日订单数", str(today_orders), delta=_delta_str(today_orders, yesterday_orders, "环比"))
    c4.metric("本月销售额", f"¥{month_sales:,.2f}", delta=_delta_str(month_sales, last_month_sales, "环比"))

    # ════ 月度 & 年度 ════
    _section_label("月度 · 年度概览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本月利润", f"¥{month_profit:,.2f}", delta=_delta_str(month_profit, last_month_profit, "环比"))
    c2.metric("本月订单数", str(month_orders), delta=_delta_str(month_orders, last_month_orders, "环比"))
    c3.metric("本年销售额", f"¥{year_sales:,.2f}", delta=_delta_str(year_sales, last_year_sales, "同比"))
    c4.metric("本年利润", f"¥{year_profit:,.2f}", delta=_delta_str(year_profit, last_year_profit, "同比"))

    # ════ 30天趋势 ════
    _section_label("近30天销售趋势")
    df_trend = get_daily_sales()
    if not df_trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trend["date"], y=df_trend["total"],
            mode="lines",
            line=dict(color="#1677FF", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(22,119,255,0.06)",
            hovertemplate="<b>%{x}</b><br>销售额: ¥%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(PLOTLY_LIGHT, height=300, xaxis_title=None, yaxis_title=None, hovermode="x")
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#F0F2F5")
        st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)
    else:
        st.info("暂无数据")

    # ════ 产品 vs 销售员 ════
    _section_label("产品 · 销售员对比")
    c1, c2 = st.columns(2)

    with c1:
        df_prod = get_product_sales()
        if not df_prod.empty:
            fig = px.bar(
                df_prod, y="name", x="total", orientation="h",
                text="total", color="total",
                color_continuous_scale=[(0, "#E6F4FF"), (0.5, "#69B1FF"), (1, "#1677FF")],
            )
            fig.update_traces(
                texttemplate="¥%{x:,.0f}", textposition="outside",
                textfont=dict(color="#374151", size=12),
                hovertemplate="<b>%{y}</b><br>销售额: ¥%{x:,.0f}<extra></extra>",
                marker=dict(cornerradius=4),
            )
            fig.update_layout(
                PLOTLY_LIGHT, height=290, title="产品销售排行",
                xaxis_title=None, yaxis_title=None,
                showlegend=False, coloraxis_showscale=False,
            )
            fig.update_xaxes(showgrid=False, showticklabels=False)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    with c2:
        rows = query_db(
            """SELECT s.name, COALESCE(SUM(o.sales_amount), 0) as sales
               FROM salespersons s LEFT JOIN orders o ON s.id = o.salesperson_id
               GROUP BY s.id"""
        )
        if rows:
            df_sp = pd.DataFrame(rows, columns=["name", "sales"])
            fig = px.bar(
                df_sp, y="name", x="sales", orientation="h",
                text="sales", color="sales",
                color_continuous_scale=[(0, "#F0F5FF"), (0.5, "#85A5FF"), (1, "#2F54EB")],
            )
            fig.update_traces(
                texttemplate="¥%{x:,.0f}", textposition="outside",
                textfont=dict(color="#374151", size=12),
                hovertemplate="<b>%{y}</b><br>销售额: ¥%{x:,.0f}<extra></extra>",
                marker=dict(cornerradius=4),
            )
            fig.update_layout(
                PLOTLY_LIGHT, height=290, title="销售员业绩排行",
                xaxis_title=None, yaxis_title=None,
                showlegend=False, coloraxis_showscale=False,
            )
            fig.update_xaxes(showgrid=False, showticklabels=False)
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    # ════ 客户来源 ════
    _section_label("客户来源分布")
    rows = query_db(
        """SELECT cs.name, COUNT(o.id) as cnt
           FROM customer_sources cs LEFT JOIN orders o ON cs.id = o.source_id
           GROUP BY cs.id"""
    )
    if rows:
        df_src = pd.DataFrame(rows, columns=["name", "cnt"])
        total = int(df_src["cnt"].sum())

        c1, c2 = st.columns([1.4, 1])

        with c1:
            fig = px.pie(
                df_src, values="cnt", names="name",
                hole=0.58, color_discrete_sequence=COLORS,
            )
            fig.update_traces(
                textinfo="percent+label",
                textfont=dict(color="#374151", size=13, family=FONT_FAMILY),
                marker=dict(line=dict(color="#FFFFFF", width=3)),
                hovertemplate="<b>%{label}</b><br>订单数: %{value}<br>占比: %{percent}<extra></extra>",
            )
            fig.update_layout(
                PLOTLY_LIGHT, height=320,
                annotations=[dict(
                    text=f"总订单<br><b style='font-size:1.4rem'>{total}</b>",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color="#9CA3AF", family=FONT_FAMILY),
                )],
            )
            st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

        with c2:
            # 来源排行榜
            df_src["占比"] = (df_src["cnt"] / total * 100).round(1)
            df_src = df_src.sort_values("cnt", ascending=False).reset_index(drop=True)
            df_src.index = df_src.index + 1
            df_src.index.name = "#"

            st.markdown(
                "<p style='font-size:0.85rem;font-weight:600;color:#6B7280;margin-top:0.75rem;'>来源排行</p>",
                unsafe_allow_html=True,
            )
            st.dataframe(
                df_src[["name", "cnt", "占比"]].rename(
                    columns={"name": "来源", "cnt": "订单数", "占比": "占比(%)"}
                ),
                use_container_width=True,
                hide_index=False,
            )
