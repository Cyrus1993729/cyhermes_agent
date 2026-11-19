#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""df_reminders73 —— Dayflow 73 号「云端提醒候选」补丁模块（暂存版，尚未切线上）

上游契约（Sites43 实际形态，2026-11-18 直连只读核验）：
    GET  /api/v1/reminders/due?calendarChanges=1&lead=18    每轮独立查询
    POST /api/v1/reminders/ack   {"key": "..."}  + 稳定 Idempotency-Key

读取走「带认证的直连 HTTP」，不再依赖本机 home 客户端：
  - 旧客户端（sites29 build）不认识 --query，实测 `client due` 会先空等 30s 超时再
    返回 `[]`，既慢又永远为空，因此读取路径改为直接打云端的 /api/v1/。
  - 认证 = hermes-cloud-connection.json 里的 {url, key}，请求头 Authorization: Bearer。
  - 必须带常规 User-Agent：缺 UA 时 Cloudflare 直接回 403「error code: 1010」。
  - 代理沿用 calendar-automation.json 的 httpProxy（127.0.0.1:10808），环境变量可覆盖。

本模块的边界（照需求书逐条落地，越界即为 bug）：
 1. 只接管 source=dingtalk 的候选。source 缺失或非 dingtalk 一律不碰 —— 那些继续走
    快照路径（df_watch73 里保留原逻辑）。
 2. 旧快照不再产生钉钉会前提醒；sourceLifecycle 为 cancelled / 待改期等失效态的候选
    不得兜底（本模块一律跳过，不猜新时间）。
 3. 字段按实际格式容错：
      - kind 缺省 = 普通会前；kind=calendar-change = 改期通知（无时间窗，按 key 去重）
      - sourceLifecycle、leadMinutes 都可以不存在（lead 由 date/start 按北京时间算）
      - message / path / key 只在钉钉候选上是必须字段
      - 空列表、以及只有非钉钉候选，都是正常响应（不算「未就绪」）
 4. 消息体 = 响应里的 message + 同站 path，交给既有 df_common.send（微信优先、
    私人 Telegram 兜底，不改收件人）。
 5. 只有渠道发送成功才写本地去重，随后 POST ack；ack 失败重试、绝不重发消息
    （失败的 ack 进 pending_ack_<date>.json，下一轮只补 ack）。

回滚：本文件为新增文件，不修改 df_watch.py / df_common.py。回滚 = cron 继续指向
df_watch.py（或把指向 df_watch73.py 的改回去），本文件留着不用即可。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_common as C

# ---------------------------------------------------------------- 契约常量

TARGET_SOURCE = "dingtalk"
KIND_PRE = "pre-meeting"
KIND_CHANGE = "calendar-change"

DUE_LEAD = 18            # 查询参数 lead=18（服务端提前量）
DUE_CALENDAR_CHANGES = 1  # 查询参数 calendarChanges=1

# 普通候选时间窗：沿用原 [LEAD-2, LEAD+3] = [13,18] 分钟
WINDOW_MIN = C.LEAD_MINUTES - 2
WINDOW_MAX = C.LEAD_MINUTES + 3

# 失效态不兜底（兼容不同拼写的 lifecycle 值，统一小写比较）
LIFECYCLE_BLOCK = {"cancelled", "canceled", "pendingreschedule",
                   "pending_reschedule", "rescheduled", "deleted", "removed"}

# 同站站点基址（与 home.mjs 里的 publicURL 一致；只是公开站点地址，不含任何凭据）
SITE_BASE = "https://dayflow-personal-planner.yucui3516.chatgpt.site"

MAX_SENDS_PER_ROUND = 3   # 单轮最多发 3 条，保护微信 iLink 额度
PENDING_ACK = "pending_ack_%s.json"
DEDUPE_PREFIX = "r73:"     # 73 候选在 reminded_<date>.json 里的键前缀

# 空白期一律按北京时间算「还有几分钟」，不依赖主机时区
BEIJING = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- 直连 HTTP 参数

DAYFLOW_HOME = Path(os.environ.get("DAYFLOW_HOME_DIR")
                    or r"C:\Users\Administrator\AppData\Local\DayflowHome")
# 缺失 UA 会被 Cloudflare 拦成 403 / error code 1010，这个头是必需品，不是可选项
USER_AGENT = "DayflowHome/1.0 (dayflow-reminders73)"
HTTP_TIMEOUT = 30
HTTP_ATTEMPTS = 2          # 与 home 客户端一致：只读请求最多 2 次
RETRY_STATUS = (403, 408, 425, 429, 500, 502, 503, 504)  # 403 多为边缘层瞬时拒绝（如 1010）
RETRY_WAIT_MAX = 5.0


def is_dry():
    return os.environ.get("DAYFLOW_DRY") == "1"


def _get(d, *names, default=None):
    for n in names:
        if isinstance(d, dict) and n in d and d[n] is not None:
            return d[n]
    return default


# ---------------------------------------------------------------- 连接配置（不含凭据输出）

def conn_file():
    """定位云端连接配置；release 升级换目录也不用改代码。可被 DAYFLOW_CONN_FILE 覆盖。"""
    env = os.environ.get("DAYFLOW_CONN_FILE")
    if env:
        return Path(env)
    try:
        cands = sorted(DAYFLOW_HOME.glob("releases/*/runtime/.local/hermes-cloud-connection.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    return cands[0] if cands else None


def _proxy_url():
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    cf = conn_file()
    if cf:
        try:
            cfg = json.loads((cf.parent / "calendar-automation.json")
                             .read_text(encoding="utf-8-sig"))
            return (cfg.get("httpProxy") or "").strip() or None
        except Exception:
            return None
    return None


def _opener():
    proxy = _proxy_url()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http_get(route):
    """只读 GET /api/v1/<route>。返回 {status, body, err, retryAfter}；绝不回显凭据。"""
    cf = conn_file()
    if not cf or not cf.exists():
        return {"status": 0, "body": "", "err": "no-connection-file"}
    try:
        conf = json.loads(cf.read_text(encoding="utf-8-sig"))
        base, key = (conf.get("url") or "").rstrip("/"), conf.get("key") or ""
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "body": "", "err": "bad-connection-file:%s" % str(e)[:80]}
    if not base or not key:
        return {"status": 0, "body": "", "err": "bad-connection-file:empty"}

    req = urllib.request.Request(
        "%s/api/v1/%s" % (base, route),
        headers={"Authorization": "Bearer " + key,
                 "User-Agent": USER_AGENT,
                 "Accept": "application/json"})
    try:
        with _opener().open(req, timeout=HTTP_TIMEOUT) as r:
            return {"status": r.status,
                    "body": r.read().decode("utf-8", "replace"), "err": ""}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        ra = None
        try:
            ra = float(e.headers.get("Retry-After"))
        except Exception:
            ra = None
        return {"status": e.code, "body": body, "err": "http-%d" % e.code,
                "retryAfter": ra}
    except Exception as e:  # noqa: BLE001 - 网络异常一律按失败重试
        return {"status": 0, "body": "",
                "err": "%s:%s" % (type(e).__name__, str(e)[:120])}


# ---------------------------------------------------------------- 查询

def due_route():
    return "reminders/due?" + urllib.parse.urlencode(
        {"calendarChanges": DUE_CALENDAR_CHANGES, "lead": DUE_LEAD})


def query_due(fixture_path=None, transport=None):
    """返回 (status, payload)。status: ok / error。

    fixture_path 用于纯虚构响应的离线验证（不发任何网络请求）。
    transport 可注入假的 GET（测试用），签名同 _http_get(route) -> dict。
    真实路径：直连 GET /api/v1/reminders/due?calendarChanges=1&lead=18，失败按只读语义
    重试一次（传输异常 / 408 / 429 / 5xx），不做任何兜底。
    """
    if fixture_path:
        try:
            return "ok", json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        except Exception as e:
            return "error", {"_fixture_error": str(e)[:200]}

    get = transport or _http_get
    route = due_route()
    last = {}
    for attempt in range(1, HTTP_ATTEMPTS + 1):
        r = get(route) or {}
        status = r.get("status") or 0
        if 200 <= status < 300:
            try:
                return "ok", json.loads(r.get("body") or "")
            except Exception as e:  # noqa: BLE001
                last = {"_error": "bad-json", "_why": str(e)[:120]}
                break
        last = {"_error": r.get("err") or ("http-%s" % status), "_status": status}
        if status not in (0,) + RETRY_STATUS or attempt >= HTTP_ATTEMPTS:
            break
        wait = r.get("retryAfter")
        wait = float(wait) if isinstance(wait, (int, float)) else float(attempt)
        time.sleep(min(max(wait, 0.0), RETRY_WAIT_MAX))
    return "error", last


def extract_candidates(payload):
    """兼容数组与 {candidates|due|items:[...]} 包装形态。"""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("candidates", "due", "reminders", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def payload_ready(payload):
    """响应是否为可用形态：数组，或带数组字段的包装。

    空数组与「只有非钉钉候选」都是正常响应（Sites43 实际行为），不算未就绪。
    """
    if isinstance(payload, list):
        return True
    if isinstance(payload, dict):
        return any(isinstance(payload.get(k), list)
                   for k in ("candidates", "due", "reminders", "items"))
    return False


# ---------------------------------------------------------------- 归一化 / 判定

def normalize(c):
    """把不同拼写的候选统一成内部结构（字段缺失就给空值，不猜）。"""
    if not isinstance(c, dict):
        return None
    key = _get(c, "key", "reminderKey", "id")
    lead = _get(c, "leadMinutes", "lead", "minutesUntilStart", "minutes")
    try:
        lead = int(lead) if lead is not None else None
    except (TypeError, ValueError):
        lead = None
    return {
        "key": str(key) if key else "",
        "kind": str(_get(c, "kind", "type", default=KIND_PRE) or KIND_PRE).strip().lower(),
        "source": str(_get(c, "source", "itemSource", default="") or "").strip().lower(),
        "lifecycle": str(_get(c, "sourceLifecycle", "lifecycle", "state",
                              default="") or "").strip().lower(),
        "itemId": _get(c, "itemId", "item_id", "localItemId", "item", "localId"),
        "start": str(_get(c, "start", "startTime", default="") or "").strip(),
        "date": str(_get(c, "date", "day", default="") or "").strip(),
        "lead": lead,
        "message": str(_get(c, "message", "text", "body", default="") or "").strip(),
        "path": str(_get(c, "path", "url", "link", default="") or "").strip(),
    }


def legacy_key(c):
    """旧脚本已经在用的去重键：本地事项ID|开始时间|日期。"""
    if c.get("itemId") and c.get("start") and c.get("date"):
        return "%s|%s|%s" % (c["itemId"], c["start"], c["date"])
    return None


def _beijing(now):
    return now.replace(tzinfo=BEIJING) if now.tzinfo is None else now.astimezone(BEIJING)


def minutes_until(start, day_str, now):
    """date/start 与北京时间 now 之间还差几分钟；无法解析返回 None。"""
    if not start:
        return None
    try:
        hms = start.split(":")
        h, m = int(hms[0]), int(hms[1])
        d = date.fromisoformat(day_str) if day_str else _beijing(now).date()
        sdt = datetime.combine(d, dtime(hour=h, minute=m), tzinfo=BEIJING)
        return (sdt - _beijing(now)).total_seconds() / 60.0
    except Exception:
        return None


def _lead_minutes(c, now, day):
    if c.get("lead") is not None:
        return c["lead"]
    return minutes_until(c.get("start"), c.get("date"), now)


def classify(c, now, day, reminded):
    """返回 (是否发送, 原因)。原因会进日志，便于上线后核对。"""
    if c is None:
        return False, "not-an-object"
    # 先看来源：非钉钉（含 source 缺失）连 key/message 都不要求，直接不接管
    if c["source"] != TARGET_SOURCE:
        return False, "source-%s" % (c["source"] or "empty")
    if not c["key"]:
        return False, "no-key"
    if c["lifecycle"] in LIFECYCLE_BLOCK:
        return False, "lifecycle-%s" % c["lifecycle"]
    if not c["message"]:
        return False, "no-message"

    dk = DEDUPE_PREFIX + c["key"]
    if reminded.get(dk):
        return False, "dup-key"
    lk = legacy_key(c)
    if lk and reminded.get(lk):
        return False, "dup-legacy"

    if c["kind"] == KIND_CHANGE:
        # 会前改期通知：无时间窗，独立按 key 去重
        return True, "calendar-change"

    lead = _lead_minutes(c, now, day)
    if lead is None:
        return False, "no-lead"
    if not (WINDOW_MIN <= lead <= WINDOW_MAX):
        return False, "window(%.1f)" % lead
    return True, "pre-meeting"


# ---------------------------------------------------------------- 消息组装

def compose_text(c):
    """响应 message + 同站 path。path 已含域名则原样，否则拼公开站点基址。"""
    msg = c.get("message") or ""
    path = c.get("path") or ""
    if path:
        link = path if path.startswith("http") else \
            SITE_BASE.rstrip("/") + "/" + path.lstrip("/")
        if link not in msg:
            msg = msg + "\n" + link
    return msg.strip()


# ---------------------------------------------------------------- 去重持久化

def _mark_sent(reminded, c, now, day):
    ts = now.isoformat(timespec="seconds")
    reminded[DEDUPE_PREFIX + c["key"]] = ts
    lk = legacy_key(c)
    if lk and c["kind"] != KIND_CHANGE:
        # 兼容：老的 df_watch.py 只认这个键，回滚后不会重复提醒
        reminded[lk] = ts
    C.save_reminded(reminded, day)


# ---------------------------------------------------------------- ack

def ack_request_id(key):
    """稳定幂等键：同一 key 永远同一个 Idempotency-Key。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "dayflow-reminders-ack:" + key))


def do_ack(key, retries=2):
    """POST /api/v1/reminders/ack {key}，失败按原幂等键重试。返回 (ok, info)。"""
    rid = ack_request_id(key)
    last = {}
    for _ in range(max(1, retries)):
        try:
            r = C.client("ack", payload={"key": key}, request_id=rid)
        except Exception as e:  # noqa: BLE001 - 传输异常一律按失败重试
            last = {"exception": str(e)[:200]}
            continue
        if isinstance(r, dict) and not r.get("_err") and not r.get("error"):
            return True, {"ack": "ok", "requestId": rid}
        last = {"ack": "failed", "requestId": rid,
                "resp": str(r)[:160]}
    return False, last


# ---------------------------------------------------------------- 待补 ack 队列

def _pending_path(day):
    return C.STATE_DIR / (PENDING_ACK % day.isoformat())


def load_pending(day):
    p = _pending_path(day)
    if not p.exists():
        return []
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, list) else []
    except Exception:
        return []


def save_pending(items, day):
    p = _pending_path(day)
    if not items:
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass
        return
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def retry_pending_acks(day, dry=False):
    """只补 ack，绝不重发消息。"""
    items = load_pending(day)
    if not items:
        return []
    out, remain = [], []
    for it in items:
        key = it.get("key")
        if not key:
            continue
        if dry:
            out.append({"key": key, "result": "dry-skip"})
            remain.append(it)
            continue
        ok, info = do_ack(key)
        out.append({"key": key, "result": "acked" if ok else "still-failed"})
        if not ok:
            remain.append(it)
    if not dry:
        save_pending(remain, day)
    return out


# ---------------------------------------------------------------- 主流程（供 df_watch73 调用）

def run(day=None, now=None, fixture=None, transport=None):
    """跑一轮钉钉候选提醒。返回脱敏摘要 dict（可直接当日志/回执）。"""
    now = now or datetime.now()
    day = day or _beijing(now).date()
    dry = is_dry()
    fixture = fixture or os.environ.get("DAYFLOW_DUE73_FIXTURE") or None

    out = {"day": day.isoformat(), "dry": dry, "query": "", "route": due_route(),
           "ready": False, "error": "", "sent": [], "skipped": [], "ack": [],
           "pendingRetry": []}

    # 0) 先补上轮没 ack 成功的（只 ack，不发消息）
    out["pendingRetry"] = retry_pending_acks(day, dry=dry)

    # 1) 每轮独立查询（直连带认证 HTTP）
    status, payload = query_due(fixture, transport=transport)
    out["query"] = status
    if status != "ok":
        out["ready"] = False
        out["error"] = str(payload.get("_error") or payload)[:120]
        print("r73 due unavailable (%s) — 不做兜底" % out["error"])
        return out

    out["ready"] = payload_ready(payload)
    if not out["ready"]:
        # 形态不认识（既不是数组也没有数组字段）：失败关闭，不读旧快照、不发钉钉会前
        out["error"] = "unexpected-shape"
        print("r73 due not-ready (unexpected shape) — 钉钉会前提醒本轮跳过，无快照兜底")
        return out

    cands = extract_candidates(payload)
    reminded = C.load_reminded(day)
    sends = 0

    for raw in cands:
        c = normalize(raw)
        verdict, why = classify(c, now, day, reminded)
        if not verdict:
            out["skipped"].append({"key": (c or {}).get("key", ""), "why": why})
            continue
        if sends >= MAX_SENDS_PER_ROUND:
            out["skipped"].append({"key": c["key"], "why": "round-cap"})
            continue

        text = compose_text(c)
        ok, ch = C.send(text)
        sends += 1
        out["sent"].append({"key": c["key"], "kind": c["kind"], "channel": ch, "ok": ok})
        if not ok:
            continue

        if dry:
            # 干跑不发、不落盘、不 ack；只报告将要做的动作
            out["ack"].append({"key": c["key"], "result": "dry-skip",
                               "requestId": ack_request_id(c["key"])})
            continue

        # 渠道成功后：先落本地去重，再 ack
        _mark_sent(reminded, c, now, day)
        ok_ack, info = do_ack(c["key"])
        out["ack"].append({"key": c["key"],
                           "result": "acked" if ok_ack else "queued",
                           "requestId": info.get("requestId")})
        if not ok_ack:
            pend = load_pending(day)
            pend.append({"key": c["key"], "at": now.isoformat(timespec="seconds")})
            save_pending(pend, day)

    return out


# ---------------------------------------------------------------- CLI（离线/干跑入口）

def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="df_reminders73 离线/干跑入口")
    ap.add_argument("--fixture", help="纯虚构响应 JSON 路径（不发网络请求）")
    ap.add_argument("--now", help="模拟当前时间 ISO，如 2026-11-18T09:30:00")
    ap.add_argument("--day", help="日期 YYYY-MM-DD（默认取 --now 的北京日期）")
    a = ap.parse_args(argv[1:])

    now = datetime.fromisoformat(a.now) if a.now else datetime.now()
    day = date.fromisoformat(a.day) if a.day else _beijing(now).date()
    res = run(day=day, now=now, fixture=a.fixture)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
