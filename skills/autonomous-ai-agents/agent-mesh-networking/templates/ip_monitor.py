# -*- coding: utf-8 -*-
"""
本机局域网 IP 监控 (cron no_agent watchdog)
基线 = 每台机改成自己的 LAN IP
- IP 与基线一致 → 输出空 (不投递, 静默)
- IP 变化或检测失败 → 输出告警 (投递到 Telegram)
"""
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_IP = "192.168.0.XXX"  # <-- 改成该机自己的 IP

def get_lan_ip():
    """从 ipconfig 提取第一个活动网卡的 192.168.x.x IPv4 地址。"""
    try:
        out = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace"
        ).stdout
    except Exception as e:
        return None, f"ipconfig 执行失败: {e}"
    # 兼容中英文输出, 逐行找含 'IPv4' 的行
    current = None
    for line in out.splitlines():
        if "IPv4" in line or "IP Address" in line or "ipv4" in line.lower():
            m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            if m:
                ip = m.group(1)
                if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                    current = ip
                    break
    if current is None:
        # 兜底: 全输出里找 192.168.x
        m = re.search(r"192\.168\.\d{1,3}\.\d{1,3}", out)
        if m:
            current = m.group(0)
    return current, out

def main():
    ip, raw = get_lan_ip()
    if ip is None:
        print("⚠️ 本机局域网 IP 检测失败(可能断网/网卡异常)。ipconfig 输出片段:\n" + (raw or "")[:400])
        sys.exit(0)
    if ip != BASE_IP:
        print(
            f"⚠️ 本机局域网 IP 变了: {BASE_IP} → {ip}\n"
            f"这会影响牛来那台与本机的 A2A 直连(它的配置指向 {BASE_IP})。\n"
            f"请告诉牛来: 把 a2a_agents 里本机(妈妈)的 url 改为 http://{ip}:9900, "
            f"或更新其 .env 的 A2A_PUBLIC_URL。"
        )

if __name__ == "__main__":
    main()
