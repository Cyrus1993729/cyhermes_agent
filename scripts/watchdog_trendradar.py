"""
TrendRadar 看门狗（Hermes cron 调用，no_agent 模式）
逻辑：
1. run.log 新鲜（< 4 小时有更新）→ 正常，静默退出（无输出）
2. run.log 旧 + 上次未触发过 → 触发 start_trendradar.bat，写触发标记，静默（给一次机会）
3. run.log 旧 + 上次已触发过（本次仍旧）→ 真挂了，输出告警（投递通知用户）
"""
import os
import subprocess
import sys
import time

BASE = r"D:\Workspace\Projects\TrendRadar"
LOG = os.path.join(BASE, "output", "logs", "run.log")
FLAG = os.path.join(BASE, "output", "logs", ".watchdog_triggered")
STALE_SECONDS = 4 * 3600  # 4 小时无运行记录视为异常

def main():
    if not os.path.exists(LOG):
        # 尚无运行记录（部署初期）：静默等待，首次运行由计划任务触发
        return

    age = time.time() - os.path.getmtime(LOG)
    if age < STALE_SECONDS:
        # 正常，清除触发标记（如有）
        if os.path.exists(FLAG):
            os.remove(FLAG)
        return  # 静默

    # 日志陈旧
    if os.path.exists(FLAG):
        # 上次触发过仍无更新 → 真挂了
        print(f"🚨 TrendRadar 疑似故障：{int(age/3600)} 小时无运行记录，自动重启未生效。请检查：")
        print(f"   1. start_trendradar.bat 是否可执行（双击测试）")
        print(f"   2. 计划任务 TrendRadarRun 是否被禁用")
        print(f"   3. 运行日志: {LOG}")
    else:
        _trigger()
        print(f"⚠️ TrendRadar {int(age/3600)} 小时无运行记录，已自动触发一次重启。")

def _trigger():
    try:
        subprocess.Popen(
            [os.path.join(BASE, "start_trendradar.bat")],
            cwd=BASE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        os.makedirs(os.path.dirname(FLAG), exist_ok=True)
        with open(FLAG, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        print(f"🚨 看门狗触发重启失败: {e}")

if __name__ == "__main__":
    main()
