#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Telegram 投递看门狗（方案B，已上线）—— 纯外围脚本，不碰 Hermes 核心。

部署位置：~/AppData/Local/hermes/scripts/tg_delivery_watchdog.py
本文件是可重建副本；迁移/重装机器时拷回去，再用 .bat 注册计划任务（见下）。

背景：gateway 的投递台账（state.db / delivery_obligations）会把失败的最终回复
落盘（last_error='send_path_degraded'），但核心自带的补发只在
 ①网关重启（sweep_recoverable）②适配器被整体重建（sweep_failed_for_runtime）
时触发。本类抖动是「几十秒自己缓过来」型，两种都不触发 → 记录烂在库里 24h 后过期 → 消息永久丢。

行为（每分钟一次）：
  1. 只接管 telegram + last_error='send_path_degraded' 的 failed 记录
  2. 失败超 SETTLE_S 秒才接管（留给网关自己的重试/重建窗口）
  3. 原子认领（state->attempting，靠 rowcount 判胜负），防与网关/并发实例双发
  4. 经 127.0.0.1:10808 直连 Bot API 补发，10 次重试、超长分块
  5. 成功后标 delivered（网关后续不会再发 → 无重复）
  6. 上限与核心台账一致：attempts<3、24h 内

注册计划任务（MSYS bash 下不要用 cmd //c 拼 schtasks，参数会被转义破坏；写 .bat 再执行）：
    @echo off
    schtasks /Create /TN hermes_tg_delivery_watchdog /TR "<venv>\\Scripts\\pythonw.exe <hermes>\\scripts\\tg_delivery_watchdog.py" /SC MINUTE /MO 1 /F
    schtasks /Query /TN hermes_tg_delivery_watchdog /V /FO LIST
（用 pythonw.exe 而非 python.exe：否则每分钟闪一次黑窗。）

日志：~/AppData/Local/hermes/logs/tg_delivery_watchdog.log
"""
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request

HOME = os.path.join(os.environ["LOCALAPPDATA"], "hermes")
DB = os.path.join(HOME, "state.db")
ENV = os.path.join(HOME, ".env")
LOG = os.path.join(HOME, "logs", "tg_delivery_watchdog.log")
PROXY = "http://127.0.0.1:10808"
SETTLE_S = 60.0          # 失败后等待窗口, 秒
MAX_ATTEMPTS = 3         # 与 delivery_ledger.MAX_ATTEMPTS 一致
STALE_S = 24 * 3600      # 与 delivery_ledger.STALE_AFTER_SECONDS 一致
CHUNK = 4000             # Telegram 单条上限 4096, 留余量
RETRIES = 10
RETRY_DELAY = 4.0
MARKER = "♻️ 自动补发（刚才发送时通道抖动，内容已由看门狗重发，可能重复）：\n\n"
ALLOWED_ERRORS = ("send_path_degraded",)


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def get_token() -> str:
    for ln in open(ENV, encoding="utf-8", errors="ignore"):
        m = re.match(r"^\s*TELEGRAM_BOT_TOKEN\s*=\s*['\"]?([^'\"]+)", ln)
        if m:
            return m.group(1).strip()
    raise SystemExit("token not found in .env")


def json_ok(s: str):
    import json
    try:
        return json.loads(s).get("ok")
    except Exception:
        return False


def send_chunk(token: str, chat_id: str, text: str, thread_id=None) -> bool:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    data = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    if thread_id:
        data["message_thread_id"] = thread_id
    body = urllib.parse.urlencode(data).encode()
    for a in range(RETRIES):
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=body
            )
            if json_ok(opener.open(req, timeout=25).read().decode()):
                return True
        except Exception as e:
            log(f"   sendMessage 第{a+1}/{RETRIES}次失败: {type(e).__name__}: {e}")
            time.sleep(RETRY_DELAY)
    return False


def claim_and_send(token: str, row: tuple) -> None:
    (oid, session_key, platform, chat_id, thread_id, content,
     state, attempts, created_at, updated_at) = row
    conn = sqlite3.connect(DB, timeout=15)
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        cur = conn.execute(
            """UPDATE delivery_obligations
               SET state='attempting', attempts=attempts+1, updated_at=?
               WHERE obligation_id=? AND platform='telegram'
                 AND state='failed' AND last_error IN ('send_path_degraded')""",
            (time.time(), oid),
        )
        conn.commit()
        if cur.rowcount != 1:
            log(f"  认领失败(可能已被网关/并发实例接管): {oid}")
            return
        log(f"认领成功 {oid} chat={chat_id} len={len(content)} attempts={attempts+1}")
    except Exception as e:
        log(f"认领异常 {oid}: {e}")
        conn.close()
        return

    full = MARKER + content if state != "pending" else content
    chunks = [full[i:i + CHUNK] for i in range(0, len(full), CHUNK)]
    ok_all = all(send_chunk(token, chat_id, c, thread_id) for c in chunks)

    try:
        if ok_all:
            conn.execute(
                "UPDATE delivery_obligations SET state='delivered', updated_at=?"
                " WHERE obligation_id=?", (time.time(), oid))
            log(f"补发成功 → delivered: {oid} ({len(chunks)}块)")
        else:
            conn.execute(
                "UPDATE delivery_obligations SET state='failed',"
                " last_error='send_path_degraded', updated_at=? WHERE obligation_id=?",
                (time.time(), oid))
            log(f"补发失败(已退回failed, 下轮再试): {oid}")
        conn.commit()
    except Exception as e:
        log(f"标记状态异常 {oid}: {e}")
    finally:
        conn.close()


def main() -> None:
    token = get_token()
    conn = sqlite3.connect(DB, timeout=15)
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        now = time.time()
        rows = conn.execute(
            """SELECT obligation_id, session_key, platform, chat_id, thread_id,
                      content, state, attempts, created_at, updated_at
               FROM delivery_obligations
               WHERE platform='telegram' AND state='failed'
                 AND last_error IN ('send_path_degraded')
                 AND attempts < ? AND created_at > ? AND updated_at < ?""",
            (MAX_ATTEMPTS, now - STALE_S, now - SETTLE_S),
        ).fetchall()
        log(f"扫描完成: 待接管 {len(rows)} 条")
    except Exception as e:
        log(f"扫描异常: {e}")
        conn.close()
        return
    conn.close()
    for row in rows:
        claim_and_send(token, row)


if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        conn = sqlite3.connect(DB, timeout=15)
        now = time.time()
        rows = conn.execute(
            """SELECT obligation_id, platform, chat_id, state, attempts,
                      datetime(created_at,'unixepoch'), datetime(updated_at,'unixepoch'),
                      length(content), substr(content,1,50)
               FROM delivery_obligations
               WHERE platform='telegram' AND state='failed'
                 AND last_error IN ('send_path_degraded')
                 AND attempts < ? AND created_at > ? AND updated_at < ?""",
            (MAX_ATTEMPTS, now - STALE_S, now - SETTLE_S),
        ).fetchall()
        print("dry-run: 可被接管 (失败>60s, attempts<3, 24h内):")
        for r in rows:
            print(" ", r)
        conn.close()
        raise SystemExit(0)
    main()
