from plyer import notification
import psutil
import datetime
import time

# 告警阈值设置
THRESHOLD_CPU = 1
THRESHOLD_MEM = 5
THRESHOLD_DISK = 5

# 日志文件路径
LOG_FILE = "monitor.log"

def check_system():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alerts = []

    # CPU
    cpu = psutil.cpu_percent(interval=1)
    if cpu > THRESHOLD_CPU:
        alerts.append(f"CPU usage high: {cpu}%")

    # 内存
    mem = psutil.virtual_memory()
    mem_pct = mem.percent
    mem_avail = mem.available / (1024**3)
    if mem_pct > THRESHOLD_MEM:
        alerts.append(f"Memory usage high: {mem_pct}%")

    # 磁盘
    disk = psutil.disk_usage("C:/")
    disk_pct = disk.percent
    disk_free = disk.free / (1024**3)
    if disk_pct > THRESHOLD_DISK:
        alerts.append(f"Disk usage high: {disk_pct}%")

    # 组装状态行
    status = (
        f"[{now}] "
        f"CPU={cpu}% | "
        f"MEM={mem_pct}% (avail {mem_avail:.1f}GB) | "
        f"DISK={disk_pct}% (free {disk_free:.1f}GB)"
    )

    # 打印到屏幕
    print(status)

    # 如果有告警，打印并写入日志
    if alerts:
        alert_msg = "\n".join(alerts)
        # 写日志
        for alert in alerts:
            alert_line = f"[{now}] *** ALERT: {alert} ***"
            print(alert_line)
            with open(LOG_FILE, "a") as f:
                f.write(alert_line + "\n")
        # 弹出桌面通知
        notification.notify(
            title="*** 系统告警 ***",
            message=alert_msg,
            timeout=10
        )
    else:
        print(f"[{now}] All systems normal.")

    print()

# 每5秒检查一次，共检查5次
print("=== Monitor started. Checking every 5 seconds ===\n")
for i in range(5):
    check_system()
    if i < 4:
        time.sleep(5)

print("=== Monitor finished. Check monitor.log for alerts ===")