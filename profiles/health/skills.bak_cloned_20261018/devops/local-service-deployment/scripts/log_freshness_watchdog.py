"""
通用日志新鲜度看门狗（Hermes cron no_agent 模式调用）
用法：复制本文件到 ~/AppData/Local/hermes/scripts/，修改下方 BASE/LOG/START_CMD/FLAG，
     然后 cronjob create: script=<文件名>.py, no_agent=true, schedule='*/30 * * * *', repeat=0
逻辑（三态）：
1. 日志新鲜（< STALE_SECONDS 有更新）→ 清除触发标记，静默退出（无输出 = 不打扰）
2. 日志陈旧 + 无触发标记 → 触发 START_CMD，写标记，静默（给一次机会）
3. 日志陈旧 + 已有触发标记 → 真挂了，输出告警文本（会被投递给用户）
注意：输出非空 = 投递；空 = 静默。部署初期日志不存在时静默等待。
"""
import os
import subprocess
import time

BASE = r"D:\path\to\service"                    # 服务根目录
LOG = os.path.join(BASE, "output", "logs", "run.log")  # 运行日志路径
START_CMD = os.path.join(BASE, "start_service.bat")    # 启动脚本
FLAG = os.path.join(BASE, "output", "logs", ".watchdog_triggered")
STALE_SECONDS = 4 * 3600                        # 超过 N 秒无更新视为异常

def main():
    if not os.path.exists(LOG):
        return  # 部署初期：静默，首次运行由计划任务负责
    age = time.time() - os.path.getmtime(LOG)
    if age < STALE_SECONDS:
        if os.path.exists(FLAG):
            os.remove(FLAG)
        return  # 正常，静默
    if os.path.exists(FLAG):
        print(f"🚨 服务疑似故障：{int(age/3600)} 小时无运行记录，自动重启未生效。请检查：")
        print(f"   1. {START_CMD} 是否可执行（双击测试）")
        print(f"   2. 计划任务是否被禁用")
        print(f"   3. 运行日志: {LOG}")
    else:
        _trigger()
        print(f"⚠️ 服务 {int(age/3600)} 小时无运行记录，已自动触发一次重启。")

def _trigger():
    try:
        subprocess.Popen([START_CMD], cwd=BASE,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        os.makedirs(os.path.dirname(FLAG), exist_ok=True)
        with open(FLAG, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        print(f"🚨 看门狗触发重启失败: {e}")

if __name__ == "__main__":
    main()
