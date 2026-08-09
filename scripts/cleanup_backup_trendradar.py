"""
TrendRadar 数据维护：清理过期报告 + 每周备份（Hermes cron 每周调用）
- 清理：output/html/ 与 output/news|rss/ 下超过 90 天的文件
- 备份：config/ + run_secrets.bat + 数据库打包到 D:\\Workspace\\Backups\\TrendRadar\\<日期>.zip，保留最近 4 份
"""
import os
import shutil
import time
import zipfile

BASE = r"D:\Workspace\Projects\TrendRadar"
BACKUP_DIR = r"D:\Workspace\Backups\TrendRadar"
KEEP_DAYS = 90
KEEP_BACKUPS = 4

def clean(dirpath, keep_days):
    removed = 0
    if not os.path.isdir(dirpath):
        return 0
    cutoff = time.time() - keep_days * 86400
    for name in os.listdir(dirpath):
        p = os.path.join(dirpath, name)
        try:
            if os.path.getmtime(p) < cutoff:
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    return removed

def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    date = time.strftime("%Y-%m-%d")
    target = os.path.join(BACKUP_DIR, f"trendradar_{date}.zip")
    if os.path.exists(target):
        return "备份已存在，跳过"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE):
            rel = os.path.relpath(root, BASE)
            # 跳过虚拟环境和 output（output 数据量随年月增长，只需数据库与报告之外的配置）
            if ".venv" in rel or rel == "output":
                dirs[:] = []
                continue
            for f in files:
                if f.endswith((".pyc", ".db")):
                    continue
                full = os.path.join(root, f)
                zf.write(full, os.path.join(rel, f))
    # 清理旧备份
    backups = sorted(
        (os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.startswith("trendradar_")),
        key=os.path.getmtime,
    )
    for old in backups[:-KEEP_BACKUPS]:
        os.remove(old)
    return f"备份完成: {target}"

if __name__ == "__main__":
    n1 = clean(os.path.join(BASE, "output", "html"), KEEP_DAYS)
    n2 = clean(os.path.join(BASE, "output", "news"), KEEP_DAYS)
    n3 = clean(os.path.join(BASE, "output", "rss"), KEEP_DAYS)
    msg = backup()
    print(f"[TrendRadar维护] 清理: html={n1}, news={n2}, rss={n3} 个过期文件 | {msg}")
