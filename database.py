import sqlite3
from contextlib import contextmanager

DB_PATH = "sales.db"


@contextmanager
def get_db():
    """数据库连接上下文管理器，自动提交/回滚和关闭"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_db(query, params=(), fetch=True):
    """执行查询：fetch=True 返回结果列表，fetch=False 执行写入"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        if fetch:
            return c.fetchall()
        return True


def query_one(query, params=()):
    """返回单条记录"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        return c.fetchone()


def _migrate_columns(c):
    """兼容旧版数据库：补加可能缺失的列"""
    migrations = {
        "customers": [("source", "TEXT"), ("remark", "TEXT")],
    }
    for table, cols in migrations.items():
        existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})")}
        for col_name, col_type in cols:
            if col_name not in existing:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass  # 列已存在或其他约束冲突，跳过


def init_db():
    """初始化数据库表结构和默认数据"""
    with get_db() as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS product_categories
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)''')

        c.execute('''CREATE TABLE IF NOT EXISTS products
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER,
                      name TEXT NOT NULL, cost_price REAL NOT NULL, sale_price REAL NOT NULL,
                      FOREIGN KEY (category_id) REFERENCES product_categories(id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS salespersons
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                      phone TEXT, base_salary REAL DEFAULT 0, commission_rate REAL DEFAULT 0.05)''')

        c.execute('''CREATE TABLE IF NOT EXISTS customer_sources
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)''')

        c.execute('''CREATE TABLE IF NOT EXISTS customers
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                      phone TEXT, address TEXT, source TEXT, remark TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS orders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE NOT NULL,
                      date TEXT NOT NULL, salesperson_id INTEGER, product_id INTEGER,
                      quantity INTEGER NOT NULL, unit_price REAL NOT NULL,
                      sales_amount REAL NOT NULL, cost REAL NOT NULL,
                      freight REAL DEFAULT 0, other_costs REAL DEFAULT 0,
                      commission REAL DEFAULT 0, profit REAL NOT NULL, customer_name TEXT,
                      customer_phone TEXT, customer_address TEXT,
                      source_id INTEGER, deposit REAL DEFAULT 0,
                      balance REAL NOT NULL, payment_status TEXT NOT NULL,
                      original_text TEXT, remark TEXT,
                      FOREIGN KEY (salesperson_id) REFERENCES salespersons(id),
                      FOREIGN KEY (product_id) REFERENCES products(id),
                      FOREIGN KEY (source_id) REFERENCES customer_sources(id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS deleted_orders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, order_no TEXT,
                      date TEXT, salesperson_id INTEGER, product_id INTEGER,
                      quantity INTEGER, unit_price REAL,
                      sales_amount REAL, cost REAL,
                      freight REAL, other_costs REAL,
                      commission REAL, profit REAL, customer_name TEXT,
                      customer_phone TEXT, customer_address TEXT,
                      source_id INTEGER, deposit REAL,
                      balance REAL, payment_status TEXT,
                      original_text TEXT, remark TEXT, deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        c.execute('''CREATE TABLE IF NOT EXISTS sales_targets
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, salesperson_id INTEGER NOT NULL,
                      year INTEGER NOT NULL, month INTEGER NOT NULL,
                      target_amount REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (salesperson_id) REFERENCES salespersons(id),
                      UNIQUE(salesperson_id, year, month))''')

        # 索引
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_salesperson ON orders(salesperson_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_phone ON orders(customer_phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_source ON orders(source_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id)")

        # 默认客户来源
        c.execute("SELECT COUNT(*) FROM customer_sources")
        if c.fetchone()[0] == 0:
            for source in ['抖音', '视频号', '微信', '电话', '线下', '其他']:
                c.execute("INSERT INTO customer_sources (name) VALUES (?)", (source,))

        # 兼容旧数据库：补加可能缺失的列
        _migrate_columns(c)
