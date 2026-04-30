import re
import uuid
import pandas as pd
from datetime import datetime, date
from io import BytesIO
from database import query_db, query_one


def generate_order_no():
    return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


def calc_profit(quantity, unit_price, cost_price, freight=0, other_costs=0, commission=0):
    """统一利润计算：返回 (销售额, 成本, 净利润)"""
    sales_amount = round(quantity * unit_price, 2)
    cost = round(quantity * cost_price, 2)
    net_profit = round(sales_amount - cost - freight - other_costs - commission, 2)
    return sales_amount, cost, net_profit


def get_payment_status(deposit, sales_amount):
    if deposit <= 0:
        return '待收款'
    elif deposit >= sales_amount:
        return '已收齐'
    return '部分收款'


def calc_growth(current, previous):
    """计算增长率，无对比数据返回 None"""
    if previous == 0:
        return None if current == 0 else None
    return ((current - previous) / previous) * 100


def export_excel(df, sheet_name, prefix):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output, f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


def parse_order_text(text):
    """智能解析订单文本"""
    if not text or not text.strip():
        return {}

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    current_year = datetime.now().year
    result = {}
    product_parts = []

    for line in lines:
        # 日期
        if not result.get('date'):
            m = re.search(r'(\d{1,2})[\.\-/月](\d{1,2})[日号]?', line)
            if m:
                try:
                    month, day = int(m.group(1)), int(m.group(2))
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        result['date'] = date(current_year, month, day)
                        after = re.sub(r'(?:下单|签单|接单)$', '', line[m.end():].strip())
                        if after and len(after) >= 2 and not any(c.isdigit() for c in after):
                            result['salesman'] = after
                except ValueError:
                    pass

        # 电话
        if not result.get('customer_phone'):
            pm = re.search(r'1[3-9]\d{9}', line)
            if pm:
                result['customer_phone'] = pm.group()

        # 客户姓名
        if not result.get('customer_name'):
            nm = re.match(r'(?:姓名|客户|收货人|联系人|购买人)[：:]\s*(.+)', line)
            if nm:
                result['customer_name'] = nm.group(1).strip().rstrip('，,。.')

        # 地址
        if not result.get('address'):
            am = re.match(r'(?:地址|收货地址|寄到|发往)[：:]\s*(.+)', line)
            if am:
                result['address'] = am.group(1).strip().rstrip('，,。.')

        # 金额
        if not result.get('amount'):
            mm = re.search(r'(?:总[价格额]|金额|合计|售价|报价)[：:]?\s*([\d,.]+)', line)
            if mm:
                try:
                    result['amount'] = float(mm.group(1).replace(',', ''))
                except ValueError:
                    pass

        # 定金（排除尾款）
        if not result.get('deposit') and '尾款' not in line:
            dm = re.search(r'(?:定金|预付|首付)[：:]?\s*([\d,.]+)', line)
            if dm:
                try:
                    result['deposit'] = float(dm.group(1).replace(',', ''))
                except ValueError:
                    pass

        # 备注
        if not result.get('remark'):
            rm = re.match(r'(?:备注|附注|说明)[：:]\s*(.+)', line)
            if rm:
                result['remark'] = rm.group(1).strip()

        # 产品信息
        product_kw = ['型号', '机器', '电机', '提升机', '筛', '泵', '机', '设备', '千瓦', '伏', '米机']
        if '型号' in line and ('：' in line or ':' in line):
            product_parts.append(line.split('：', 1)[-1] if '：' in line else line.split(':', 1)[-1])
        elif any(kw in line for kw in product_kw):
            if not any(line in str(v) for v in result.values() if isinstance(v, str)):
                product_parts.append(line)

    if product_parts:
        result['product'] = '，'.join(product_parts)

    # 补充销售员
    if not result.get('salesman'):
        for line in lines[:3]:
            if re.match(r'^[一-鿿]{2,4}(?:下单|签单|接单)?$', line):
                result['salesman'] = re.sub(r'(?:下单|签单|接单)$', '', line)
                break

    if result.get('customer_phone') and not result.get('customer_name'):
        result['customer_name'] = '未知客户'

    return result


def get_stats_by_date_range(start_date, end_date):
    row = query_one(
        '''SELECT COALESCE(SUM(sales_amount), 0),
                  COALESCE(SUM(profit), 0),
                  COUNT(*)
           FROM orders WHERE date BETWEEN ? AND ?''',
        (start_date, end_date)
    )
    return row if row else (0, 0, 0)


def get_daily_sales():
    from database import get_db
    with get_db() as conn:
        return pd.read_sql("""
            SELECT date, SUM(sales_amount) as total
            FROM orders
            WHERE date >= date('now', '-30 days')
            GROUP BY date ORDER BY date
        """, conn)


def get_product_sales():
    from database import get_db
    with get_db() as conn:
        return pd.read_sql("""
            SELECT p.name, SUM(o.sales_amount) as total
            FROM orders o JOIN products p ON o.product_id = p.id
            GROUP BY p.name
        """, conn)


def get_sales_ranking(period='month'):
    from database import get_db
    period_map = {
        'today': "date = date('now')",
        'month': "strftime('%Y-%m', date) = strftime('%Y-%m', 'now')",
        'year': "strftime('%Y', date) = strftime('%Y', 'now')",
    }
    condition = period_map.get(period, period_map['month'])

    with get_db() as conn:
        return pd.read_sql(f"""
            SELECT s.name as salesman, COALESCE(SUM(o.sales_amount), 0) as total_sales,
                   COALESCE(SUM(o.profit), 0) as total_profit
            FROM salespersons s
            LEFT JOIN orders o ON s.id = o.salesperson_id AND {condition}
            GROUP BY s.id, s.name
            ORDER BY total_sales DESC
        """, conn)


def validate_phone(phone):
    """验证手机号格式"""
    if not phone:
        return True
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


def load_salesperson_options():
    rows = query_db("SELECT id, name, commission_rate FROM salespersons ORDER BY id")
    return {r["name"]: (r["id"], r["commission_rate"]) for r in rows}


def load_product_options():
    rows = query_db("SELECT id, name, cost_price, sale_price FROM products ORDER BY id")
    return {r["name"]: (r["id"], r["cost_price"], r["sale_price"]) for r in rows}


def load_source_options():
    rows = query_db("SELECT id, name FROM customer_sources ORDER BY id")
    return {r["name"]: r["id"] for r in rows}


def try_save_customer(name, phone, address, source):
    """尝试保存客户信息，若电话已存在则跳过"""
    if not phone:
        return
    existing = query_one("SELECT id FROM customers WHERE phone = ?", (phone,))
    if not existing:
        query_db(
            "INSERT INTO customers (name, phone, address, source, remark) VALUES (?, ?, ?, ?, ?)",
            (name or '', phone, address or '', source or '', '订单自动创建'),
            fetch=False
        )
