# -*- coding: utf-8 -*-
"""
本机局域网 IP 监控 (cron no_agent watchdog)
基线 = 192.168.0.112 (pc-b, Hermes 本机)
- IP 与基线一致 → 输出空 (不投递, 完全静默)
- IP 变化 → ① 直接 A2A 通知妈妈机更新配置 ② 输出告警 (投递到 Telegram 给用户)
- --test-a2a → 仅测试 A2A 通知通道 (发一条测试消息给妈妈机)
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_IP = "192.168.0.112"
PEER_URL = "http://192.168.0.106:9900/"          # 妈妈机 (pc-a)
HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")

A2A_NOTE_TEMPLATE = (
    "【A2A 配置同步】牛来局域网 IP 变了: {old} → {new}。"
    "请把 a2a_agents 里牛来的 url 改为 http://{new}:9900。"
)


def get_lan_ip():
    """从 ipconfig 提取第一个活动网卡的局域网 IPv4 地址。"""
    try:
        out = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace"
        ).stdout
    except Exception as e:
        return None, "ipconfig 执行失败: %s" % e
    current = None
    for line in out.splitlines():
        if "IPv4" in line or "IP Address" in line:
            m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            if m:
                ip = m.group(1)
                if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                    current = ip
                    break
    if current is None:
        m = re.search(r"192\.168\.\d{1,3}\.\d{1,3}", out)
        if m:
            current = m.group(0)
    return current, out


def _read_a2a_token():
    env_path = HERMES_HOME / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("A2A_BEARER_TOKEN="):
            return line.split("=", 1)[1].strip()
    return ""


def send_a2a_note(text, timeout=15):
    """直接通过 A2A 发消息给妈妈机。失败静默 (监控不因通知失败崩溃)。"""
    tok = _read_a2a_token()
    if not tok:
        return False
    try:
        body = json.dumps({
            "jsonrpc": "2.0", "id": 9000, "method": "SendMessage",
            "params": {"message": {
                "messageId": "ipmon-" + str(int(time.time() * 1000)),
                "role": "ROLE_USER", "parts": [{"text": text}]}}
        }).encode("utf-8")
        req = urllib.request.Request(PEER_URL, data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
        return True
    except Exception:
        return False


def main():
    if "--test-a2a" in sys.argv:
        ok = send_a2a_note("【IP监控链路测试】牛来 → 妈妈机的 A2A 自动通知通道工作正常, 收到无需回复。")
        print("A2A 测试:", "OK" if ok else "FAIL")
        sys.exit(0)

    ip, raw = get_lan_ip()
    if ip is None:
        print("⚠️ 本机局域网 IP 检测失败(可能断网/网卡异常)。ipconfig 输出片段:\n" + (raw or "")[:400])
        sys.exit(0)

    if ip != BASE_IP:
        note = A2A_NOTE_TEMPLATE.format(old=BASE_IP, new=ip)
        send_a2a_note(note)   # ① 直接通知妈妈机
        print("⚠️ 本机局域网 IP 变了: %s → %s\n%s" % (BASE_IP, ip, note))  # ② 告警用户


if __name__ == "__main__":
    main()