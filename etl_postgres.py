import psycopg2
import csv
import datetime

# PostgreSQL连接配置（用Airflow那个现成的）
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "airflow",
    "user":     "airflow",
    "password": "airflow"
}

# ============================================================
# EXTRACT
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
# TRANSFORM
# ============================================================
def transform(rows):
    print(f"\n[TRANSFORM] Cleaning data...")
    clean = []
    skipped = 0

    for row in rows:
        if not row["store"] or not row["quantity"] or not row["price"]:
            print(f"  [SKIP] Incomplete row: {row}")
            skipped += 1
            continue
        try:
            clean.append({
                "date":     row["date"],
                "store":    row["store"].strip(),
                "product":  row["product"].strip(),
                "quantity": int(row["quantity"]),
                "price":    float(row["price"]),
                "revenue":  int(row["quantity"]) * float(row["price"])
            })
        except ValueError as e:
            print(f"  [SKIP] Bad format: {e}")
            skipped += 1

    print(f"[TRANSFORM] Clean: {len(clean)}, Skipped: {skipped}")
    return clean

# ============================================================
# LOAD → PostgreSQL
# ============================================================
def load(rows):
    print(f"\n[LOAD] Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    # 建表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id         SERIAL PRIMARY KEY,
            date       DATE,
            store      VARCHAR(100),
            product    VARCHAR(100),
            quantity   INTEGER,
            price      NUMERIC(10,2),
            revenue    NUMERIC(10,2),
            loaded_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    # 写入
    for row in rows:
        cur.execute("""
            INSERT INTO sales
              (date, store, product, quantity, price, revenue)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (row["date"], row["store"], row["product"],
              row["quantity"], row["price"], row["revenue"]))

    conn.commit()
    cur.close()
    conn.close()
    print(f"[LOAD] Inserted {len(rows)} rows into PostgreSQL.")

# ============================================================
# VERIFY
# ============================================================
def verify():
    print(f"\n[VERIFY] Querying database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM sales")
    print(f"  Total rows: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT store, SUM(revenue)
        FROM sales
        GROUP BY store
        ORDER BY SUM(revenue) DESC
    """)
    print(f"  Revenue by store:")
    for row in cur.fetchall():
        print(f"    {row[0]:<12} ${row[1]:,.2f}")

    cur.close()
    conn.close()

# ============================================================
# 主流程
# ============================================================
print("=" * 50)
print("ETL Pipeline (PostgreSQL)")
print("=" * 50)

raw   = extract("sales_data.csv")
clean = transform(raw)
load(clean)
verify()

print("\n" + "=" * 50)
print("Done!")
print("=" * 50)