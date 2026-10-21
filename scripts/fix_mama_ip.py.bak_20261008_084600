#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""妈妈机 IP 监控自愈守候 (cron no_agent 模式; stdout 非空才投递, 空=静默)

背景 (2026-10-07 复盘)
  妈妈机 (pc-a) 自己的 scripts/ip_monitor.py 里 BASE_IP 是写死的基线。
  它的局域网 IP 早在 9/7 就已变成 192.168.0.113, 但基线一直停在旧值,
  于是每 31 分钟触发一次 "IP 变了" 假告警 —— 9/6 起共 237 条,
  每条都会在本机拉起一个完整 agent 会话去读配置/验证/写回复, 白烧额度
  (实测单次 api_calls 3~10、耗时 60~220 秒)。

  旧版本脚本把「旧 IP」写死成 .106, 而对方实际停在 .110,
  替换条件永远不匹配 → 空转一个月没修上。这就是根因。

本版做法 (方案 A, 2026-10-07 用户拍板)
  不猜旧值。用「我连得上它的那个地址」直接告诉它当前 IP 是多少, 要求它:
    ① BASE_IP 已等于当前 IP → 回一句「已是新IP」, 什么都不动;
    ② 不等于 → 只改 BASE_IP 这一个值 (止血);
    ③ 顺手把「告警后把新 IP 写回 BASE_IP」这一步补上 (根治, 以后自愈)。
  本机侧用 state 文件记住「已确认修好的 IP」, 同一个 IP 只确认一次,
  之后每轮只做 8 秒 agent-card 探活, 完全静默, 不再拉起 agent。

坑位 (agent-mesh-networking skill 实测)
  - 本机 env HTTP_PROXY=10808 会劫持 LAN 直连 → urllib 必须用无代理 opener
  - token 取 .env 的 A2A_BEARER_TOKEN (双机共享同一 token)
  - Windows 中文 stdout 需 reconfigure utf-8 (GBK 无 ✅⚠️ 字符)
  - 妈妈机未开机 → 空输出静默, 下轮再试

用法
  python fix_mama_ip.py            # 常规守候 (cron 每 30 分钟)
  python fix_mama_ip.py --force    # 忽略 state, 强制重新确认一次
  python fix_mama_ip.py --probe    # 只探活, 不发送任何指令
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PEER_URL = "http://192.168.0.113:9900"
MAMA_SCRIPT = "C:/Users/1/AppData/Local/hermes/scripts/ip_monitor.py"
ENV_PATH = r"C:\Users\Administrator\AppData\Local\hermes\.env"
STATE_PATH = Path(r"C:\Users\Administrator\AppData\Local\hermes\scripts\fix_mama_ip_state.json")
CARD_TIMEOUT = 8
SEND_TIMEOUT = 150

PEER_IP = urllib.parse.urlparse(PEER_URL).hostname or ""

CONFIRM_WORDS = ("已是新IP", "已是新 IP", "已更新", "已改为", "已修改", "已完成", "修改成功")
FAIL_WORDS = ("错误", "失败", "无法", "不存在", "没有权限", "拒绝", "找不到")


def load_token() -> str:
    try:
        for line in open(ENV_PATH, encoding="utf-8", errors="replace"):
            m = re.match(r"\s*A2A_BEARER_TOKEN\s*=\s*(.+)", line.strip())
            if m:
                return m.group(1).strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(d: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def opener_noproxy():
    """无代理 opener (绕过本机 HTTP_PROXY=10808 对 LAN 直连的劫持)"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe_card(opener, token):
    try:
        req = urllib.request.Request(
            PEER_URL + "/.well-known/agent-card.json",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with opener.open(req, timeout=CARD_TIMEOUT) as r:
            card = json.loads(r.read().decode("utf-8"))
            return True, card.get("name", "?")
    except Exception:
        return False, ""


def build_instruction() -> str:
    return (
        "【IP 监控自愈修复 · 来自牛来(192.168.0.112)】\n"
        f"你的当前局域网 IP 是 {PEER_IP} —— 我就是从这个地址连上你的，你不用再自己查 ipconfig。\n"
        f"你机器上的监控脚本 {MAMA_SCRIPT} 里有个 BASE_IP 常量，它的值停在旧 IP 上，"
        "所以你每 31 分钟就误报一次『IP 变了』；牛来这边从 9/6 起已经收到 237 条一模一样的重复告警，"
        "每条都会拉起我这边一个完整的会话，成本很高。\n\n"
        "请按下面步骤处理。除 BASE_IP 外不要改动任何其他内容，也不要动其他文件：\n"
        f"① 读取 {MAMA_SCRIPT}，找到 BASE_IP 那一行，读出它的当前值；\n"
        f'② 如果该值已经等于 "{PEER_IP}" → 不要做任何修改，直接回复『已是新IP』；\n'
        f'③ 如果该值不等于 "{PEER_IP}" → 只把这一个字符串值改成 "{PEER_IP}"，'
        "这一行其他字符一个都不要动；改完重新读取该文件，把 BASE_IP 这一行「改动前 → 改动后」的原文贴出来；\n"
        f"④ 再补一步根治：在 {MAMA_SCRIPT} 里「检测到 IP 变化、发出告警」这个分支的最后，"
        "追加一行——把新 IP 写回 BASE_IP 再退出，让基线告警后自动跟上，以后就不会再循环误报了。"
        "只加这一处，不要重构、不要改其他逻辑；改完把这一小段代码贴出来。\n"
        "⑤ 如果文件打不开、路径不存在或没有写权限，不要换别的路径、不要乱试，"
        "直接把报错原文回复给我。\n\n"
        "无论成不成，都请用一句话明确回复结果。"
    )


def send_instruction(opener, token):
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"text": build_instruction()}],
                    "metadata": {"taskId": f"fix-mama-ip-{int(time.time())}"},
                }
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        PEER_URL + "/",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "A2A-Version": "1.0",
            "Authorization": f"Bearer {token}",
        },
    )
    t0 = time.time()
    with opener.open(req, timeout=SEND_TIMEOUT) as r:
        resp = json.loads(r.read().decode("utf-8"))
    st = resp.get("result", {}).get("status", {})
    parts = st.get("message", {}).get("parts", [])
    reply = parts[0].get("text", "") if parts else ""
    return reply, time.time() - t0


def should_warn(msg: str, state: dict) -> bool:
    """告警去重: 同一句话只报一次, 之后每 24 小时最多提醒一次。
    防止把「妈妈端重复刷屏」换成「本守候自己重复刷屏」。"""
    sig = msg[:120]
    if sig == state.get("last_warn_msg") and (time.time() - state.get("last_warn_ts", 0)) < 86400:
        return False
    state["last_warn_msg"] = sig
    state["last_warn_ts"] = time.time()
    save_state(state)
    return True


def warn(msg: str, state: dict) -> None:
    if should_warn(msg, state):
        print(msg)


def main():
    force = "--force" in sys.argv
    probe_only = "--probe" in sys.argv

    state = load_state()

    token = load_token()
    if not token:
        warn("⚠️ 妈妈机IP自愈守候: 本机 .env 读不到 A2A_BEARER_TOKEN", state)
        return
    if not PEER_IP:
        warn(f"⚠️ 妈妈机IP自愈守候: PEER_URL 解析不出 IP ({PEER_URL})", state)
        return

    already_fixed = (state.get("fixed_peer_ip") == PEER_IP) and not force

    opener = opener_noproxy()
    ok, name = probe_card(opener, token)
    if not ok:
        return  # 妈妈机未开机 → 静默, 下轮再试
    if probe_only:
        print(f"妈妈机在线: {name} ({PEER_IP}) | state: {state or '空'}")
        return
    if already_fixed:
        return  # 这个 IP 已确认修好过 → 彻底静默, 不再拉起 agent

    try:
        reply, dt = send_instruction(opener, token)
    except Exception as e:
        warn(f"⚠️ 妈妈机在线({name})但指令未完成确认(超时/异常 {e})，30分钟后自动重试", state)
        return

    if not reply:
        warn(f"⚠️ 妈妈机({name})响应为空，30分钟后重试", state)
        return

    head = reply.strip().replace("\n", " ")[:200]
    if any(w in reply for w in CONFIRM_WORDS) and not any(w in reply for w in FAIL_WORDS):
        state["fixed_peer_ip"] = PEER_IP
        state["confirmed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        state["peer_name"] = name
        save_state(state)
        print(
            f"✅ 妈妈机({name}) IP 监控自愈修复完成: {head}\n"
            f"已记入 state (fixed_peer_ip={PEER_IP})，之后本守候将完全静默，"
            "只有在它 IP 再次变化时才会重新介入。"
        )
    else:
        warn(f"⚠️ 妈妈机({name})回复未确认修复成功，30分钟后重试。回复原文: {head}", state)


if __name__ == "__main__":
    main()
