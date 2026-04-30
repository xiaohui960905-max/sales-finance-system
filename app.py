import streamlit as st

st.set_page_config(page_title="销售业绩管理系统", layout="wide", page_icon="📊")

from database import init_db
from modules import (
    show_dashboard, show_order_entry, show_order_list,
    show_customer_mgmt, show_sales_detail, show_ranking,
    show_analysis, show_settings
)

# ── 钉钉风格自定义 CSS ──────────────────────────────────────
st.markdown("""
<style>
/* ── 字体 ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans SC', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 全局背景 ── */
.stApp {
    background: #F0F2F5;
}
.stMainBlockContainer {
    padding-top: 1.5rem;
    max-width: 100% !important;
}

/* ── 隐藏不需要的元素 ── */
header[data-testid="stHeader"] { background: #FFFFFF; border-bottom: 1px solid #E5E7EB; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* ── 页面标题 ── */
h1 {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #1F2937 !important;
    padding: 0.125rem 0 0.5rem 0 !important;
    letter-spacing: -0.01em;
}

/* ═══════════════════════════════════════════════════════
   侧边栏
   ═══════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E5E7EB;
    box-shadow: 2px 0 8px rgba(0,0,0,0.04);
}
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px;
    padding: 0 4px;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 10px 14px;
    border-radius: 8px;
    transition: all 0.15s ease;
    font-size: 0.9rem;
    color: #4B5563;
    margin-bottom: 0;
    font-weight: 500;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #F0F5FF;
    color: #1677FF;
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: #E6F4FF;
    color: #1677FF;
    font-weight: 600;
}

/* ═══════════════════════════════════════════════════════
   指标卡片
   ═══════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 1.125rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 16px rgba(22,119,255,0.08);
    border-color: #BFD9FF;
}
[data-testid="stMetric"] label {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #9CA3AF !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    color: #1F2937 !important;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* ═══════════════════════════════════════════════════════
   容器卡片
   ═══════════════════════════════════════════════════════ */
div[class*="block-container"] > div > div[data-testid="stVerticalBlock"] {
    background: transparent;
}

/* ═══════════════════════════════════════════════════════
   表格
   ═══════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #E5E7EB;
}
[data-testid="stDataFrame"] table {
    border-collapse: separate;
    border-spacing: 0;
}
[data-testid="stDataFrame"] thead th {
    background: #FAFBFC !important;
    color: #6B7280 !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    padding: 0.7rem 0.55rem !important;
    border-bottom: 1px solid #E5E7EB !important;
    white-space: nowrap !important;
}
[data-testid="stDataFrame"] thead th * {
    writing-mode: horizontal-tb !important;
    text-orientation: upright !important;
    white-space: nowrap !important;
    overflow: visible !important;
}
[data-testid="stDataFrame"] tbody td {
    padding: 0.6rem 1rem !important;
    font-size: 0.875rem !important;
    color: #374151 !important;
    border-bottom: 1px solid #F3F4F6 !important;
    background: #FFFFFF;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: #F0F5FF;
}

/* ═══════════════════════════════════════════════════════
   按钮
   ═══════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s ease !important;
    padding: 0.4rem 1.25rem !important;
}
.stButton > button[kind="primary"] {
    background: #1677FF !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #4096FF !important;
    box-shadow: 0 2px 8px rgba(22,119,255,0.25) !important;
}
.stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    border: 1px solid #D1D5DB !important;
    color: #374151 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #1677FF !important;
    color: #1677FF !important;
}

/* ═══════════════════════════════════════════════════════
   输入控件
   ═══════════════════════════════════════════════════════ */
input, textarea {
    border-radius: 6px !important;
    border-color: #D1D5DB !important;
}
input:focus, textarea:focus {
    border-color: #1677FF !important;
    box-shadow: 0 0 0 2px rgba(22,119,255,0.1) !important;
}

/* ═══════════════════════════════════════════════════════
   标题层级
   ═══════════════════════════════════════════════════════ */
h2 {
    font-weight: 600 !important;
    font-size: 1.15rem !important;
    color: #1F2937 !important;
    margin-top: 1rem !important;
    padding-bottom: 0.5rem !important;
}
h3 {
    font-weight: 600 !important;
    font-size: 1rem !important;
    color: #374151 !important;
}

/* ═══════════════════════════════════════════════════════
   展开面板
   ═══════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    border-radius: 8px !important;
    border: 1px solid #E5E7EB !important;
    background: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #1F2937 !important;
}

/* ═══════════════════════════════════════════════════════
   Radio / Tabs
   ═══════════════════════════════════════════════════════ */
[data-testid="stRadio"] [role="radiogroup"] {
    gap: 6px;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E5E7EB;
}
.stTabs [data-baseweb="tab"] {
    color: #6B7280;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
    padding: 0.6rem 1.25rem;
}
.stTabs [aria-selected="true"] {
    color: #1677FF;
}

/* ═══════════════════════════════════════════════════════
   Info/Success/Warning 消息
   ═══════════════════════════════════════════════════════ */
[data-testid="stInfo"] {
    background: #F0F5FF !important;
    border: 1px solid #BFD9FF !important;
    border-radius: 8px !important;
    color: #1F2937 !important;
}

/* ═══════════════════════════════════════════════════════
   Select / Multiselect
   ═══════════════════════════════════════════════════════ */
.stSelectbox > div > div {
    border-radius: 6px !important;
    border-color: #D1D5DB !important;
}

/* ═══════════════════════════════════════════════════════
   分隔线
   ═══════════════════════════════════════════════════════ */
hr {
    border-color: #E5E7EB !important;
}

/* ═══════════════════════════════════════════════════════
   KPI 分组标签
   ═══════════════════════════════════════════════════════ */
.kpi-section-label {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.75rem 0 0.5rem 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6B7280;
    letter-spacing: 0.02em;
}
.kpi-section-label::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 16px;
    background: #1677FF;
    border-radius: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── 初始化数据库 ──
init_db()

# ── 侧边栏 ──
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:0.5rem 0.25rem 0.75rem 0.25rem;">
        <div style="width:36px;height:36px;background:#1677FF;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;font-size:1.2rem;">
            📊
        </div>
        <div>
            <p style="font-size:1rem;font-weight:700;color:#1F2937;margin:0;line-height:1.3;">
                销售管理系统
            </p>
            <p style="font-size:0.7rem;color:#9CA3AF;margin:0;">
                Sales Performance
            </p>
        </div>
    </div>
    <div style="height:1px;background:#F0F2F5;margin-bottom:0.75rem;"></div>
    """, unsafe_allow_html=True)

    menu = ["首页看板", "订单录入", "订单列表", "客户管理", "销售详情", "排行榜", "统计分析", "基础设置"]
    choice = st.radio("", menu, key="nav", label_visibility="collapsed")

    st.markdown("""
    <div style="position:fixed;bottom:1.5rem;left:1.5rem;width:13rem;">
        <div style="height:1px;background:#F0F2F5;margin-bottom:0.75rem;"></div>
        <span style="font-size:0.7rem;color:#C5C9D2;">v2.0 · Powered by Streamlit</span>
    </div>
    """, unsafe_allow_html=True)

# ── 路由 ──
page_map = {
    "首页看板": show_dashboard,
    "订单录入": show_order_entry,
    "订单列表": show_order_list,
    "客户管理": show_customer_mgmt,
    "销售详情": show_sales_detail,
    "排行榜": show_ranking,
    "统计分析": show_analysis,
    "基础设置": show_settings,
}

st.header(choice)
st.divider()
page_map[choice]()
