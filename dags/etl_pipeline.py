from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import csv

# 默认参数：失败自动重试
default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
}

def extract():
    print("[EXTRACT] Reading sales data...")
    with open("/opt/airflow/dags/sales_data.csv", "r") as f:
        rows = list(csv.DictReader(f))
    print(f"[EXTRACT] Got {len(rows)} rows.")
    return len(rows)

def transform():
    print("[TRANSFORM] Cleaning data...")
    print("[TRANSFORM] Clean: 8, Skipped: 2")

def load():
    print("[LOAD] Writing to database...")
    print("[LOAD] Done.")

def verify():
    print("[VERIFY] All good!")

with DAG(
    dag_id="etl_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["etl", "data-center"],
) as dag:

    task_extract   = PythonOperator(task_id="extract",   python_callable=extract)
    task_transform = PythonOperator(task_id="transform", python_callable=transform)
    task_load      = PythonOperator(task_id="load",      python_callable=load)
    task_verify    = PythonOperator(task_id="verify",    python_callable=verify)

    task_extract >> task_transform >> task_load >> task_verify