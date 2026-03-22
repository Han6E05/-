import csv
import sqlite3
import datetime

# ============================================================
# EXTRACT：从 CSV 文件读取原始数据
# ============================================================
def extract(filepath):
    print(f"\n[EXTRACT] Reading from {filepath}...")
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"[EXTRACT] Read {len(rows)} rows.")
    return rows

# ============================================================
# TRANSFORM：清洗数据
# ============================================================
def transform(rows):
    print(f"\n[TRANSFORM] Cleaning data...")
    clean = []
    skipped = 0

    for row in rows:
        # 检查关键字段是否为空
        if not row["store"] or not row["quantity"] or not row["price"]:
            print(f"  [SKIP] Incomplete row: {row}")
            skipped += 1
            continue

        # 转换数据类型
        try:
            clean.append({
                "date":     row["date"],
                "store":    row["store"].strip(),
                "product":  row["product"].strip(),
                "quantity": int(row["quantity"]),
                "price":    float(row["price"]),
                "revenue":  int(row["quantity"]) * float(row["price"])  # 新增计算字段
            })
        except ValueError as e:
            print(f"  [SKIP] Bad data format: {row} → {e}")
            skipped += 1

    print(f"[TRANSFORM] Clean rows: {len(clean)}, Skipped: {skipped}")
    return clean

# ============================================================
# LOAD：写入数据库
# ============================================================
def load(rows, db_path):
    print(f"\n[LOAD] Writing to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 建表（如果不存在）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT,
            store    TEXT,
            product  TEXT,
            quantity INTEGER,
            price    REAL,
            revenue  REAL,
            loaded_at TEXT
        )
    """)

    # 写入数据
    loaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        cur.execute("""
            INSERT INTO sales (date, store, product, quantity, price, revenue, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (row["date"], row["store"], row["product"],
              row["quantity"], row["price"], row["revenue"], loaded_at))

    conn.commit()
    conn.close()
    print(f"[LOAD] Inserted {len(rows)} rows into database.")

# ============================================================
# VERIFY：查询验证数据写进去了
# ============================================================
def verify(db_path):
    print(f"\n[VERIFY] Checking database...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 总行数
    cur.execute("SELECT COUNT(*) FROM sales")
    total = cur.fetchone()[0]
    print(f"  Total rows in DB: {total}")

    # 按门店统计收入
    print(f"\n  Revenue by store:")
    cur.execute("""
        SELECT store, SUM(revenue) as total_revenue
        FROM sales
        GROUP BY store
        ORDER BY total_revenue DESC
    """)
    for row in cur.fetchall():
        print(f"    {row[0]:<12} ${row[1]:,.2f}")

    # 最高收入产品
    print(f"\n  Top product:")
    cur.execute("""
        SELECT product, SUM(revenue) as total
        FROM sales GROUP BY product
        ORDER BY total DESC LIMIT 1
    """)
    top = cur.fetchone()
    print(f"    {top[0]} → ${top[1]:,.2f}")

    conn.close()

# ============================================================
# 主流程：把三步串起来
# ============================================================
print("=" * 50)
print("ETL Pipeline Started")
print("=" * 50)

raw_data   = extract("sales_data.csv")
clean_data = transform(raw_data)
load(clean_data, "sales.db")
verify("sales.db")

print("\n" + "=" * 50)
print("ETL Pipeline Finished Successfully")
print("=" * 50)