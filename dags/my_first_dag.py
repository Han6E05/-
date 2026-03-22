from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='my_first_dag',
    start_date=datetime(2024, 1, 1),
    schedule=None,  # 手动触发
    catchup=False,
) as dag:

    # 任务1：检查磁盘空间
    check_disk = BashOperator(
        task_id='check_disk',
        bash_command='echo "磁盘检查开始" && df -h && echo "磁盘检查完成"',
    )

    # 任务2：检查内存
    check_memory = BashOperator(
        task_id='check_memory',
        bash_command='echo "内存检查开始" && cat /proc/meminfo | head -5 && echo "内存检查完成"',
    )

    # 任务3：汇总报告
    summary = BashOperator(
        task_id='summary_report',
        bash_command='echo "所有检查完成！系统运行正常。"',
    )

    # 定义顺序：先检查磁盘和内存，再出报告
    [check_disk, check_memory] >> summary