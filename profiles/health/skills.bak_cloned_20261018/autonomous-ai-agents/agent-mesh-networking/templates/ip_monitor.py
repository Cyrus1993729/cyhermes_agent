# -*- coding: utf-8 -*-
"""本机局域网 IP 监控 + A2A 通知 (cron no_agent watchdog) —— 复制到 hermes/scripts/ 后改两行即可用

改这两行:
    BASE_IP  = 该机自己的 LAN IP
    PEER_URL = 对端机器 (另一台) 的 A2A 地址 http://<对端IP>:9900/

逻辑:
    IP == BASE_IP            -> 输出空 (no_agent 空 stdout 不投递 = 静默)
    IP != BASE_IP / 检测失败  -> ① 直接 A2A 通知对端更新配置 ② stdout 告警投递到 Telegram
    --test-a2a                -> 只测 A2A 通知通道 (不判 IP)，改完 PEER_URL 必跑

实测坑 (2026-09/10):
    - ipconfig 输出是 UTF-16 -> MSYS grep 报 Binary file matches；必须 python 解析
    - cron no_agent stdout 是管道，中文系统按 GBK -> 含 ⚠️ 会 UnicodeEncodeError 静默崩溃
      -> 顶部必须 sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    - 本机常驻 HTTP_PROXY=127.0.0.1:10808 时 python 裸 urlopen 打 LAN 会走代理 -> 失败，
      且 except 吞掉原因 = 「静默哑」；必须用 ProxyHandler({}) 无代理 opener (下 _NO_PROXY)
    - BASE_IP 长期 stale 会导致每 30m 反复误报同一个「IP 变了」-> 对端 A2A 日志风暴
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_IP = "192.168.0.XXX"                       # <-- 改成该机自己的 IP
PEER_URL = "http://192.168.0.XXX:9900/"         # <-- 改成对端机器 (另一台) 的地址
HERMES_HOME = Path(r"C:\Users\<用户名>\AppData\Local\hermes")   # <-- 改成该机 hermes 目录
SELF_NAME = "本机"                               # 告警文案里自称 (如 牛来 / 妈妈)

# 无代理 opener：LAN 直连的生命线 (curl 对应姿势 --noproxy '*')
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))

A2A_NOTE_TEMPLATE = (
    "【A2A 配置同步】{self}局域网 IP 变了: {old} → {new}。"
    "请把 a2a_agents 里{self}的 url 改为 http://{new}:9900。"
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


def send_a2a_note(text, timeout=30):
    """通过 A2A 直接通知对端。失败静默 (监控不因通知失败崩溃) —— 但用 --test-a2a 显式验证。"""
    tok = _read_a2a_token()
    if not tok:
        return False
    try:
        body = json.dumps({
            "jsonrpc": "2.0", "id": 9000, "method": "SendMessage",
            "params": {"message": {
                "messageId": "ipmon-" + str(int(time.time() * 1000)),
                "role": "ROLE_USER", "parts": [{"text": text}]}},
        }).encode("utf-8")
        req = urllib.request.Request(PEER_URL, data=body, headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + tok})
        with _NO_PROXY.open(req, timeout=timeout) as resp:   # 必须无代理，别用裸 urlopen
            resp.read()
        return True
    except Exception as e:
        if "--debug" in sys.argv:
            print("send_a2a_note 失败: %s: %s" % (type(e).__name__, e))
        return False


def main():
    if "--test-a2a" in sys.argv:
        ok = send_a2a_note("【IP监控链路测试】%s → 对端机的 A2A 自动通知通道测试, 收到无需回复。" % SELF_NAME)
        print("A2A 测试:", "OK" if ok else "FAIL (先 curl --noproxy '*' <PEER_URL>/.well-known/agent-card.json 确认对端活着)")
        sys.exit(0)

    ip, raw = get_lan_ip()
    if ip is None:
        print("⚠️ 本机局域网 IP 检测失败(可能断网/网卡异常)。ipconfig 输出片段:\n" + (raw or "")[:400])
        sys.exit(0)

    if ip != BASE_IP:
        note = A2A_NOTE_TEMPLATE.format(self=SELF_NAME, old=BASE_IP, new=ip)
        send_a2a_note(note)          # ① 直接通知对端
        print("⚠️ 本机局域网 IP 变了: %s → %s\n%s" % (BASE_IP, ip, note))   # ② 告警用户


if __name__ == "__main__":
    main()
