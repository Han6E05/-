# 故障排查手册

数据中心日常运维故障处理记录，持续更新。

---

## 如何使用这份文档

遇到问题时，按以下顺序操作：
1. 先看**现象**，找到对应的故障类型
2. 按**排查步骤**逐步执行
3. 找到根本原因后，按**修复方法**处理
4. 处理完成后，记录到**故障日志**

---

## 故障排查通用流程（5W法）

```
What  → 什么出问题了？（哪个服务、哪个DAG、哪个接口）
When  → 什么时候开始的？（看日志时间戳）
Where → 哪个环节出问题？（哪个Task、哪台服务器）
Why   → 为什么出问题？（看具体报错信息）
How   → 怎么修？（按流程处理，或上报高级工程师）
```

---

## 日志阅读法：只看3行

遇到任务失败，日志很长但只需要找这三个关键位置：

```
1. Running command:   → 这个Task实际执行了什么
2. Output:           → 命令的输出结果
3. return code       → 0=成功，非0=失败
```

搜索技巧：
```bash
grep "ERROR" app.log          # 找所有报错
grep "return code" task.log   # 直接找结果
tail -n 50 app.log            # 看最近50行
```

---

## 常见错误代码

| Return Code | 含义 | 常见原因 |
|-------------|------|---------|
| 0 | 成功 | 正常完成 |
| 1 | 通用错误 | 看具体报错信息 |
| 127 | 命令不存在 | 容器里没有安装这个命令 |
| 126 | 权限不足 | 需要 chmod 或 sudo |
| 137 | 被强制终止 | 内存不足（OOM Kill） |

---

## 案例一：Airflow Task 失败（FileNotFoundError）

### 时间
2026-03-21

### 现象
```
Airflow DAG 列表中，etl_pipeline 变红
进入DAG详情：
  extract    → 红色（FAILED）
  transform  → 橙色（upstream_failed）
  load       → 橙色（upstream_failed）
  verify     → 橙色（upstream_failed）
```

### 排查步骤

**第一步：确认哪个Task失败了**
```
左边任务列表中，extract 是红色
其余三个是橙色（upstream_failed）
→ 说明根本问题在 extract，其余是连锁反应
→ 只需要修复 extract，不要管橙色的
```

**第二步：点进 extract → 查看 Logs**

在日志里找到关键报错：
```
FileNotFoundError: [Errno 2] No such file or directory:
'/opt/airflow/dags/sales_data.csv'

Command exited with return code 1
Marking task as FAILED.
```

**第三步：分析根本原因**
```
报错：FileNotFoundError
含义：程序要读取的文件不存在
位置：/opt/airflow/dags/sales_data.csv（容器内路径）

原因：文件存在于宿主机（Windows），
      但没有复制到 Docker 容器内部
```

### 修复方法

```bash
# 把文件从宿主机复制进容器
docker cp C:\etl-demo\sales_data.csv \
  airflow-demo-airflow-scheduler-1:/opt/airflow/dags/sales_data.csv

# 验证文件已经进去了
docker exec airflow-demo-airflow-scheduler-1 \
  ls /opt/airflow/dags/
```

**重跑Task：**
```
1. 点击 extract 那个红色圆点
2. 选择 Clear task
3. 确认
4. 等待 Task 自动重新执行
```

### 结果验证
```
extract    → 绿色（success）
transform  → 绿色（success）
load       → 绿色（success）
verify     → 绿色（success）

日志最后一行：
return code 0
Marking task as SUCCESS.
```

### 关键教训
```
upstream_failed 不是真正的错误
= 上游失败导致我没法跑

只需要修复第一个红色的Task
其余的在重跑后会自动接续执行

不要逐个去修橙色的Task，那是浪费时间
```

---

## 案例二：命令不存在（return code 127）

### 时间
2026-03-21

### 现象
```
my_first_dag 中 check_memory Task 失败
return code 127
```

### 排查步骤

查看日志：
```
Running command: 'echo "内存检查开始" && free -h'
Output:
  内存检查开始
  /usr/bin/bash: line 1: free: command not found
Command exited with return code 127
```

### 根本原因
```
free 命令在精简版 Linux 容器（如 Airflow 容器）中没有安装
return code 127 = 命令不存在
```

### 修复方法

**方案1：用替代命令**
```python
# 改用 cat /proc/meminfo，任何 Linux 都有
bash_command='cat /proc/meminfo | head -5'
```

**方案2：在容器里安装命令**
```bash
docker exec -it 容器名 bash
apt-get update && apt-get install -y procps
```

### 关键教训
```
精简版容器不包含所有 Linux 命令
遇到 command not found，先想替代方案
/proc/meminfo 是读取内存信息最通用的方法
```

---

## 案例三：磁盘空间不足

### 现象
```
Grafana 监控面板出现磁盘告警
df -h 显示 Use% > 85%
```

### 排查步骤

```bash
# 查看磁盘使用情况
df -h

# 找出哪个目录占用最多
du -sh /* 2>/dev/null | sort -rh | head -10

# 查看日志目录大小
du -sh /var/log/
```

### 常见原因及修复

**原因1：日志文件堆积**
```bash
# 查看日志文件
ls -lh /var/log/

# 清理超过30天的日志
find /var/log/ -name "*.log" -mtime +30 -delete
```

**原因2：Docker 镜像/容器占用**
```bash
# 查看Docker占用
docker system df

# 清理不用的镜像和容器
docker system prune -f
```

**原因3：数据库增长过快**
```bash
# 查看数据库大小（PostgreSQL）
SELECT pg_size_pretty(pg_database_size('airflow'));
```

---

## 日常巡检清单

每次上班后先执行以下检查（约5分钟）：

**1. 看 Airflow**
```
□ DAG 列表有没有红色
□ 昨晚的定时任务有没有全部成功
□ 有没有长时间卡在 running 状态的 Task
```

**2. 看系统资源**
```bash
□ df -h | grep -v tmpfs          # 磁盘 Use% < 85%
□ cat /proc/meminfo | head -3    # MemAvailable 充足
□ ps aux | head -20              # 没有异常进程
```

**3. 看监控日志**
```bash
□ cat monitor.log                # 有没有 ALERT 记录
□ tail -n 50 /var/log/syslog     # 系统有没有异常
```

**4. 简单连通性测试**
```bash
□ ping 8.8.8.8                   # 外网连通
□ curl http://localhost:8080     # Airflow 界面正常
□ curl http://localhost:3000     # Grafana 界面正常
```

---

## 上报标准

以下情况**立即上报**高级工程师，不要自己处理：

```
❗ 多个 DAG 同时失败
❗ 服务器 CPU 持续 > 90% 超过10分钟
❗ 磁盘使用率 > 90%
❗ 数据库连接失败
❗ 网络完全中断
❗ 看不懂报错信息，无法判断原因
```

以下情况**自行处理后记录**：

```
✅ 单个 Task 失败，原因明确
✅ 命令不存在（127错误），有替代方案
✅ 日志文件清理
✅ 重跑已失败的 Task
```

---

## 故障日志模板

每次处理完故障，记录以下信息：

```
日期：
故障现象：
影响范围：
根本原因：
处理过程：
处理结果：
预防措施：
处理人：
```

---

*最后更新：2026-03-22*
