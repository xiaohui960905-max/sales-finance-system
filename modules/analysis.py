import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import query_db
from utils import export_excel

CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}
FONT_FAMILY = "Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif"
DINGTALK_BLUE = "#1677FF"
DINGTALK_GRADIENT = [(0, "#E6F4FF"), (1, "#1677FF")]
DINGTALK_PALETTE = ["#1677FF", "#52C41A", "#FA8C16", "#F5222D", "#722ED1", "#13C2C2"]


def _apply_chart_style(fig):
    """统一图表样式：浅色背景 + 锁定缩放"""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", family=FONT_FAMILY),
        title=dict(font=dict(color="#1F2937", size=14, family=FONT_FAMILY)),
        margin=dict(l=8, r=8, t=36, b=8),
        dragmode=False,
        xaxis=dict(gridcolor="#F0F2F5", fixedrange=True),
        yaxis=dict(gridcolor="#F0F2F5", fixedrange=True),
    )
    return fig


def show_analysis():
    st.caption("多维度数据对比 · 图表分析")

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=90), key="ana_start")
    with c2:
        end_date = st.date_input("结束日期", datetime.now(), key="ana_end")

    analysis_type = st.radio("分析维度", ["按销售", "按产品", "按来源"], horizontal=True, key="ana_type")
    start = start_date.strftime('%Y-%m-%d')
    end = end_date.strftime('%Y-%m-%d')

    if analysis_type == "按销售":
        st.markdown('<p style="color:#6B7280;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;margin:0.5rem 0 0.25rem 0;">销售员业绩分析</p>', unsafe_allow_html=True)
        data = query_db(
            """SELECT s.name, SUM(o.sales_amount) as sales, SUM(o.profit) as profit, COUNT(o.id) as orders
               FROM orders o JOIN salespersons s ON o.salesperson_id = s.id
               WHERE o.date BETWEEN ? AND ? GROUP BY s.id""",
            (start, end)
        )
        df = pd.DataFrame(data, columns=['销售员', '销售额', '利润', '订单数'])
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(df, x='销售员', y='销售额', title='销售额对比',
                            text='销售额', color='销售额',
                            color_continuous_scale=DINGTALK_GRADIENT)
                fig.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside',
                                  textfont=dict(color="#374151", size=11))
                fig.update_xaxes(fixedrange=True)
                fig.update_yaxes(fixedrange=True, showticklabels=False, showgrid=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            with c2:
                fig = px.bar(df, x='销售员', y='利润', title='利润对比',
                            text='利润', color='利润',
                            color_continuous_scale=DINGTALK_GRADIENT)
                fig.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside',
                                  textfont=dict(color="#374151", size=11))
                fig.update_xaxes(fixedrange=True)
                fig.update_yaxes(fixedrange=True, showticklabels=False, showgrid=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            st.dataframe(df, use_container_width=True)
            _export_button(df, '销售员分析')
        else:
            st.info("所选日期范围内暂无订单数据")

    elif analysis_type == "按产品":
        st.markdown('<p style="color:#6B7280;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;margin:0.5rem 0 0.25rem 0;">产品销售分析</p>', unsafe_allow_html=True)
        data = query_db(
            """SELECT p.name, SUM(o.quantity) as qty, SUM(o.sales_amount) as sales, SUM(o.profit) as profit
               FROM orders o JOIN products p ON o.product_id = p.id
               WHERE o.date BETWEEN ? AND ? GROUP BY p.id""",
            (start, end)
        )
        df = pd.DataFrame(data, columns=['产品', '销量', '销售额', '利润'])
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(df, values='销售额', names='产品', title='销售额占比',
                            color_discrete_sequence=DINGTALK_PALETTE)
                fig.update_traces(textinfo='percent+label', textfont=dict(color="#374151", size=12))
                fig.update_layout(dragmode=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            with c2:
                fig = px.bar(df, x='产品', y='销售额', title='销售额对比',
                            text='销售额', color='销售额',
                            color_continuous_scale=DINGTALK_GRADIENT)
                fig.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside',
                                  textfont=dict(color="#374151", size=11))
                fig.update_xaxes(fixedrange=True)
                fig.update_yaxes(fixedrange=True, showticklabels=False, showgrid=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            st.dataframe(df, use_container_width=True)
            _export_button(df, '产品分析')
        else:
            st.info("所选日期范围内暂无订单数据")

    else:
        st.markdown('<p style="color:#6B7280;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;margin:0.5rem 0 0.25rem 0;">客户来源分析</p>', unsafe_allow_html=True)
        data = query_db(
            """SELECT cs.name, COUNT(o.id) as orders, SUM(o.sales_amount) as sales, SUM(o.profit) as profit
               FROM orders o JOIN customer_sources cs ON o.source_id = cs.id
               WHERE o.date BETWEEN ? AND ? GROUP BY cs.id""",
            (start, end)
        )
        df = pd.DataFrame(data, columns=['来源', '订单数', '销售额', '利润'])
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(df, values='订单数', names='来源', title='订单数占比',
                            color_discrete_sequence=DINGTALK_PALETTE)
                fig.update_traces(textinfo='percent+label', textfont=dict(color="#374151", size=12))
                fig.update_layout(dragmode=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            with c2:
                fig = px.bar(df, x='来源', y='销售额', title='销售额对比',
                            text='销售额', color='销售额',
                            color_continuous_scale=DINGTALK_GRADIENT)
                fig.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside',
                                  textfont=dict(color="#374151", size=11))
                fig.update_xaxes(fixedrange=True)
                fig.update_yaxes(fixedrange=True, showticklabels=False, showgrid=False)
                st.plotly_chart(_apply_chart_style(fig), use_container_width=True, config=CHART_CONFIG)
            st.dataframe(df, use_container_width=True)
            _export_button(df, '来源分析')
        else:
            st.info("所选日期范围内暂无订单数据")


def _export_button(df, prefix):
    output, filename = export_excel(df, prefix, prefix)
    st.download_button(
        label="📥 导出报表",
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
