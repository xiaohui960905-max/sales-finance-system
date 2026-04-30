# 销售财务管理系统

基于 Streamlit + SQLite 的轻量级企业财务核算系统，为中小型销售团队提供订单管理、应收催收、提成工资、销售目标等核心财务功能。

## 功能模块

| 页面 | 功能 |
|------|------|
| 首页看板 | KPI 指标卡片、30 天销售趋势、产品/销售员排行、客户来源分布 |
| 订单录入 | 文本粘贴智能识别 + 手动录入双模式，自动计算利润提成 |
| 订单列表 | 多维度筛选、汇总统计、编辑/删除/回收站恢复、逾期天数 |
| 客户管理 | 客户 CRUD、订单数统计、累计消费金额 |
| 销售详情 | 单人业绩指标、近 30 天趋势、目标完成率对比 |
| 排行榜 | 销售额排行 + 提成排行 + 薪酬汇总（底薪+提成），支持 Excel 导出 |
| 统计分析 | 按销售员/产品/来源多维度图表分析 |
| 基础设置 | 产品分类、产品、销售人员、客户来源、销售目标管理 |

## 技术栈

- **前端**：Streamlit + 钉钉风格自定义 CSS
- **后端**：Python + SQLite（WAL 模式）
- **图表**：Plotly（锁定缩放、浅色主题）
- **测试**：Playwright 自动化页面验证

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run app.py
```

浏览器访问 http://localhost:8501

## 项目结构

```
├── app.py              # 主入口，路由分发 + 自定义 CSS
├── database.py         # 数据库初始化、迁移、连接管理
├── utils.py            # 工具函数（统计、导出、解析、验证）
├── modules/
│   ├── dashboard.py    # 首页看板
│   ├── order_entry.py  # 订单录入
│   ├── order_list.py   # 订单列表
│   ├── customer_mgmt.py # 客户管理
│   ├── sales_detail.py # 销售详情
│   ├── ranking.py      # 排行榜 + 薪酬汇总
│   ├── analysis.py     # 统计分析
│   └── settings.py     # 基础设置 + 销售目标
├── requirements.txt
└── .streamlit/config.toml
```

## 数据库表

- `orders` — 订单主表
- `deleted_orders` — 已删除订单（回收站）
- `customers` — 客户信息
- `products` / `product_categories` — 产品与分类
- `salespersons` — 销售人员（底薪 + 提成比例）
- `customer_sources` — 客户来源
- `sales_targets` — 月度销售目标

## 构建方式

本项目全程使用 [Claude Code](https://claude.com/claude-code) 辅助开发，从单文件 1300+ 行重构为多模块架构，并通过多轮对话完成 UI 优化、Bug 修复和功能迭代。
