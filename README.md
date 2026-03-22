# 数据中心运维工具包

针对数据中心现场工程师日常工作场景构建的完整工具集，涵盖系统监控、ETL数据管道、可视化看板和自动化调度四个核心模块。

---

## 项目架构

```
原始数据（CSV）
     ↓
Python ETL 脚本
  ├── 数据提取（Extract）
  ├── 数据清洗（Transform）  ← 自动跳过脏数据
  └── 数据加载（Load）
     ↓
PostgreSQL 数据库
     ↓
Grafana 可视化看板
  ├── 门店收入柱状图
  ├── 产品收入柱状图
  └── 汇总统计面板

Airflow 调度器（独立运行）
  └── etl_pipeline DAG
        ├── extract → transform → load → verify
        └── 失败自动重试3次

psutil 系统监控（独立运行）
  ├── CPU / 内存 / 磁盘使用率
  └── 超阈值 → 桌面弹窗告警 + monitor.log
```

---

## 目录结构

```
.
├── README.md                  # 本文件
├── monitor.py                 # 系统监控脚本
├── etl.py                     # ETL管道（SQLite版，快速演示用）
├── etl_postgres.py            # ETL管道（PostgreSQL版，生产用）
├── sales_data.csv             # 示例数据（含故意插入的脏数据）
├── docker-compose.yaml        # 完整Docker环境（Airflow+PostgreSQL+Grafana）
├── dags/
│   └── etl_pipeline.py        # Airflow DAG（带重试机制）
└── docs/
    └── fault_diagnosis.md     # 故障排查手册（含真实案例）
```

---

## 模块一：系统监控脚本

**文件：** `monitor.py`

每隔5秒检测一次系统资源，超过阈值时触发桌面通知并写入日志。

**检测指标：**

| 指标       | 默认告警阈值 |
| ---------- | ------------ |
| CPU 使用率 | > 80%        |
| 内存使用率 | > 85%        |
| 磁盘使用率 | > 85%        |

**安装依赖：**

```bash
pip install psutil plyer
```

**运行：**

```bash
python monitor.py
```

**输出示例：**

```
=== Monitor started. Checking every 5 seconds ===

[2026-03-21 15:54:31] CPU=5.5% | MEM=71.9% (avail 4.4GB) | DISK=40.1% (free 271.6GB)
[2026-03-21 15:54:31] All systems normal.

[2026-03-21 15:56:04] CPU=11.0% | MEM=71.1% (avail 4.5GB) | DISK=40.1% (free 271.6GB)
[2026-03-21 15:56:04] *** ALERT: CPU usage high: 11.0% ***
[2026-03-21 15:56:04] *** ALERT: Memory usage high: 71.1% ***
```

**告警触发时：**

- 右下角弹出 Windows 桌面通知
- 告警内容写入 `monitor.log`，保留历史记录

**生产环境部署（Linux Cron）：**

```bash
# 每5分钟自动执行一次
*/5 * * * * python3 /opt/scripts/monitor.py
```

---

## 模块二：ETL 数据管道

**文件：** `etl_postgres.py`（生产版）/ `etl.py`（演示版）

完整的 Extract → Transform → Load 流程，处理真实的脏数据场景。

### 示例数据说明

`sales_data.csv` 包含10行数据，其中故意插入了2条问题数据：

```csv
date,store,product,quantity,price
2026-03-01,Amsterdam,Laptop,2,999.99
2026-03-04,Rotterdam,Laptop,          ← quantity 为空（脏数据）
2026-03-05,,Monitor,1,349.99          ← store 为空（脏数据）
```

### 各阶段说明

**Extract（提取）**

```
[EXTRACT] Read 10 rows.
```

**Transform（转换）**

```
[TRANSFORM] Clean rows: 8, Skipped: 2
  [SKIP] Incomplete row: {'store': 'Rotterdam', 'quantity': ''}
  [SKIP] Incomplete row: {'store': '', 'product': 'Monitor'}
```

自动检测并跳过不完整的记录，同时计算新字段：

```python
revenue = quantity × price
```

**Load（加载）**

```
[LOAD] Inserted 8 rows into PostgreSQL.
```

**Verify（验证）**

```
[VERIFY] Total rows: 8
         Revenue by store:
           Amsterdam    $2,939.88
           Rotterdam    $1,239.96
           Utrecht        $399.90
         Top product: Laptop → $2,999.97
```

### 运行

```bash
pip install psycopg2-binary
python etl_postgres.py
```

> 需要先启动 Docker 环境，PostgreSQL 暴露 5432 端口。

---

## 模块三：Docker 完整环境

**文件：** `docker-compose.yaml`

一条命令启动完整运维环境。

**包含的服务：**

| 服务              | 端口 | 用途                  |
| ----------------- | ---- | --------------------- |
| PostgreSQL        | 5432 | 数据库，存储 ETL 结果 |
| Airflow Webserver | 8080 | DAG 管理界面          |
| Airflow Scheduler | -    | 负责触发和调度 DAG    |
| Grafana           | 3000 | 数据可视化看板        |

**启动：**

```bash
docker compose up -d
```

**首次启动创建 Airflow 用户：**

```bash
docker compose run --rm airflow-init airflow users create \
  --username airflow --password airflow \
  --firstname Air --lastname Flow \
  --role Admin --email admin@example.com
```

**访问地址：**

```
Airflow：http://localhost:8080   账号/密码：airflow / airflow
Grafana： http://localhost:3000   账号/密码：admin / admin
```

---

## 模块四：Airflow DAG（自动调度）

**文件：** `dags/etl_pipeline.py`

将 ETL 流程封装为 Airflow DAG，支持失败重试和状态监控。

**DAG 结构：**

```
extract → transform → load → verify
```

**重试机制：**

```python
default_args = {
    'retries': 3,                        # 失败后最多重试3次
    'retry_delay': timedelta(minutes=1), # 每次间隔1分钟
}
```

日志中可以确认重试机制生效：

```
Starting attempt 1 of 4   ← 1次正常 + 3次重试 = 最多4次
```

**Task 状态说明：**

| 颜色   | 状态            | 含义                     |
| ------ | --------------- | ------------------------ |
| 🟢 绿色 | success         | 执行成功                 |
| 🔴 红色 | failed          | 执行失败，查看日志       |
| 🟠 橙色 | upstream_failed | 上游失败导致，修红色即可 |
| 🟣 粉色 | skipped         | 被跳过                   |

> 看到橙色不要慌，只需要修复第一个红色 Task，其余会自动接续。

---

## 模块五：Grafana 可视化看板

连接 PostgreSQL，将 ETL 写入的数据实时可视化。

**配置数据源：**

```
Connections → Data sources → Add → PostgreSQL
Host:     host.docker.internal:5432
Database: airflow
User:     airflow
Password: airflow
SSL Mode: disable
```

**看板包含3个面板：**

面板1 — Revenue by Store（门店收入柱状图）

```sql
SELECT store, SUM(revenue) as total_revenue
FROM sales GROUP BY store ORDER BY total_revenue DESC
```

面板2 — Revenue by Product（产品收入柱状图）

```sql
SELECT product, SUM(revenue) as total_revenue
FROM sales GROUP BY product ORDER BY total_revenue DESC
```

面板3 — Summary（汇总统计 Stat 面板）

```sql
SELECT COUNT(*) as total_orders,
       SUM(revenue) as total_revenue,
       ROUND(AVG(revenue)::numeric, 2) as avg_order_value
FROM sales
```

---

## 故障排查

详细流程和真实案例见：[docs/fault_diagnosis.md](docs/fault_diagnosis.md)

快速命令参考：

```bash
grep "ERROR" app.log | tail -20    # 查最近报错
df -h | grep -v tmpfs              # 检查磁盘
cat /proc/meminfo | head -3        # 检查内存
docker compose ps                  # 检查容器状态
```

---

## 技术栈

| 技术           | 版本   | 用途                 |
| -------------- | ------ | -------------------- |
| Python         | 3.12   | ETL脚本、监控脚本    |
| Apache Airflow | 2.8.0  | 任务调度             |
| PostgreSQL     | 13     | 目标数据库           |
| Grafana        | latest | 数据可视化           |
| Docker         | -      | 容器化部署           |
| psutil         | 5.9+   | 系统指标采集         |
| plyer          | -      | 跨平台桌面通知       |
| psycopg2       | -      | Python连接PostgreSQL |

---

## 对应工作职责

| 职责                          | 对应模块                  |
| ----------------------------- | ------------------------- |
| 监控系统性能并检测异常        | monitor.py                |
| 协助数据管道（ETL/ELT）的运行 | etl_postgres.py + Airflow |
| 确保系统间数据稳定传输        | PostgreSQL + Grafana 验证 |
| 协助系统部署                  | docker-compose.yaml       |
| 故障排查与处理                | docs/fault_diagnosis.md   |
| 遵守 GDPR 数据安全要求        | 日志中不记录个人信息      |

---

*最后更新：2026-03-22*
