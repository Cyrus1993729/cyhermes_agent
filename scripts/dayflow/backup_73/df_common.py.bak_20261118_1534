# -*- coding: utf-8 -*-
"""Dayflow 日程助手 —— 公共库（供 cron no_agent 脚本共用）

设计要点：
- 数据只从云端主库读（home.mjs client），不在本地存副本做权威
- 微信优先，失败自动转 Telegram，绝不静默丢失
- 单条消息 ≤900 字（iLink 1800 字才拆块，拆块既丢内容又烧额度）
- 状态文件只存"提醒去重 / 快照基线"，不存业务数据
"""
import json
import os
import subprocess
import tempfile
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")
STATE_DIR = HERMES_HOME / "state" / "dayflow"
NODE = r"C:\Users\Administrator\AppData\Local\DayflowHome\tools\node24\node.exe"
HOME_MJS = r"C:\Users\Administrator\AppData\Local\DayflowHome\releases\sites29-afdf902-home1\deployment\home.mjs"
HERMES_BIN = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe"

WX_TARGET = "weixin:o9cq805UpPVgaMB-v0amSgCvP1GY@im.wechat"
TG_TARGET = "telegram:8938729624"

MAX_MSG_CHARS = 900
SNAPSHOT_TTL_MIN = 15
LEAD_MINUTES = 15
LEAD_WINDOW_MIN = 5
STALE_DAYS = 3

STATE_DIR.mkdir(parents=True, exist_ok=True)

WEEKDAY_CN = "一二三四五六日"


# ---------------------------------------------------------------- 客户端调用

def client(op, extra=None, payload=None, request_id=None, timeout=120):
    """调用 home.mjs client <op>，返回解析后的 JSON。"""
    args = [NODE, HOME_MJS, "client", op] + list(extra or [])
    tmp = None
    if payload is not None:
        tmp = STATE_DIR / (".req_%s.json" % uuid.uuid4().hex)
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args += ["--json-file", str(tmp), "--request-id", request_id or uuid.uuid4().hex]
    try:
        p = subprocess.run(args, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    finally:
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    out = (p.stdout or "").strip()
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out[:500], "_err": (p.stderr or "").strip()[:500],
                "_code": p.returncode}


def get_items():
    d = client("items")
    if isinstance(d, list):
        return d
    raise RuntimeError("读取 items 失败: %s" % json.dumps(d, ensure_ascii=False)[:300])


def get_state():
    d = client("state")
    if isinstance(d, dict) and "items" in d:
        return d
    raise RuntimeError("读取 state 失败: %s" % json.dumps(d, ensure_ascii=False)[:300])


# ---------------------------------------------------------------- 消息发送

def _send_one(target, path):
    try:
        p = subprocess.run([HERMES_BIN, "send", "--to", target, "--file", str(path),
                            "--json"],
                           capture_output=True, encoding="utf-8", errors="replace",
                           timeout=180)
        body = (p.stdout or "").strip()
        try:
            d = json.loads(body)
        except Exception:
            d = {"raw": body[:200]}
        return bool(d.get("success")), d
    except Exception as e:
        return False, {"exception": str(e)[:200]}


def _log_delivery(record):
    try:
        p = STATE_DIR / "delivery.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def send(text, note_on_fallback=True):
    """微信优先发送；失败自动转 Telegram。返回 (ok, channel)。"""
    text = (text or "").strip()
    if not text:
        return False, "empty"
    if os.environ.get("DAYFLOW_DRY") == "1":
        print("[DRY] ---- %d chars ----" % len(text))
        print(text)
        print("[DRY] ---- end ----")
        return True, "dry"
    if len(text) > MAX_MSG_CHARS:
        text = text[: MAX_MSG_CHARS - 16] + "\n…（已截断）"

    tmp = STATE_DIR / (".msg_%s.txt" % uuid.uuid4().hex)
    try:
        tmp.write_text(text, encoding="utf-8")
        ok_wx, info_wx = _send_one(WX_TARGET, tmp)
        rec = {"at": datetime.now().isoformat(timespec="seconds"),
               "chars": len(text), "wx_ok": ok_wx,
               "wx_info": {k: info_wx.get(k) for k in
                           ("success", "message_id", "error", "raw", "exception")
                           if k in info_wx}}
        if ok_wx:
            _log_delivery(rec)
            return True, "weixin"

        # 微信失败 → Telegram 兜底
        fallback = text
        if note_on_fallback:
            fallback += "\n\n（微信通道没发出去，这条走 Telegram）"
        tmp.write_text(fallback, encoding="utf-8")
        ok_tg, info_tg = _send_one(TG_TARGET, tmp)
        rec["tg_ok"] = ok_tg
        rec["tg_info"] = {k: info_tg.get(k) for k in
                          ("success", "message_id", "error", "raw", "exception")
                          if k in info_tg}
        _log_delivery(rec)
        return ok_tg, ("telegram" if ok_tg else "failed")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- 快照

def _d(d=None):
    return d or date.today()


def snapshot_path(d=None):
    return STATE_DIR / ("snapshot_%s.json" % _d(d).isoformat())


def load_snapshot(d=None):
    p = snapshot_path(d)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_snapshot(items, d=None, source="watch"):
    d = _d(d)
    slim = []
    for i in items:
        slim.append({
            "id": i.get("id"),
            "title": i.get("title"),
            "date": i.get("date"),
            "endDate": i.get("endDate"),
            "start": i.get("start") or "",
            "end": i.get("end") or "",
            "status": i.get("status"),
            "category": i.get("category"),
            "source": i.get("source"),
            "sourceLocation": i.get("sourceLocation") or "",
            "plannedMinutes": i.get("plannedMinutes") or 0,
        })
    data = {"date": d.isoformat(),
            "savedAt": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "items": slim}
    p = snapshot_path(d)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)
    return data


def snapshot_age_minutes(d=None):
    p = snapshot_path(d)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["savedAt"])
        return (datetime.now() - ts).total_seconds() / 60.0
    except Exception:
        return None


# ---------------------------------------------------------------- 事项筛选

def is_live(item):
    return item.get("status") not in ("cancelled",)


def is_done(item):
    return item.get("status") == "completed"


def item_end(item):
    raw = item.get("endDate") or item.get("date")
    try:
        return date.fromisoformat(raw)
    except Exception:
        return None


def on_day(item, day):
    """事项是否落在 day（含跨日区间）"""
    try:
        s = date.fromisoformat(item.get("date") or "")
    except Exception:
        return False
    e = item_end(item) or s
    return s <= day <= e


def fmt_hhmm(s):
    s = (s or "").strip()
    return s if s else "--:--"


# ---------------------------------------------------------------- 今日日程组装

SRC_TAG = {"dingtalk": "钉钉", "mail": "邮件", "manual": "手动", "hermes": "助理"}


def _conflicts(fixed):
    """固定时段事项的时间重叠对"""
    out = []
    ordered = sorted(fixed, key=lambda x: x.get("start") or "99:99")
    for idx in range(len(ordered)):
        a = ordered[idx]
        for b in ordered[idx + 1:]:
            if not (a.get("start") and a.get("end") and b.get("start") and b.get("end")):
                continue
            if b["start"] < a["end"]:
                out.append((a, b))
    return out


def build_today_message(items, day=None, reason="morning"):
    """组装今日日程文本（微信友好纯文本，≤900 字）"""
    day = day or date.today()
    todays = [i for i in items if is_live(i) and on_day(i, day)]
    fixed = [i for i in todays if i.get("start") and i.get("end")]
    anon = [i for i in todays if not i.get("start")]
    done = [i for i in todays if is_done(i)]
    open_items = [i for i in todays if not is_done(i)]

    fixed.sort(key=lambda x: x.get("start") or "99:99")

    head = "今日日程 %d月%d日 周%s" % (day.month, day.day, WEEKDAY_CN[day.weekday()])
    if reason == "update":
        head = "今日日程已更新 %d月%d日 周%s" % (day.month, day.day, WEEKDAY_CN[day.weekday()])

    lines = [head]
    budget = MAX_MSG_CHARS - 120

    def add(block):
        nonlocal budget
        if budget - len(block) < 0:
            return False
        lines.append(block)
        budget -= len(block)
        return True

    if not todays:
        lines.append("")
        lines.append("今天没有任何安排。")
        if reason == "morning":
            lines.append("")
            lines.append("今天有要安排的事吗？直接告诉我就行——几点、做什么、"
                         "要不要提前提醒，我给你排进系统。")
    else:
        if fixed:
            add("")
            add("固定时段 %d 项" % len(fixed))
            for i in fixed[:12]:
                tag = SRC_TAG.get(i.get("source"), "")
                mark = " ✓" if is_done(i) else ""
                add("• %s-%s %s%s%s" % (i["start"], i["end"], i["title"][:40],
                                        "  [%s]" % tag if tag else "", mark))
            if len(fixed) > 12:
                add("• …还有 %d 项未显示" % (len(fixed) - 12))
        if anon:
            add("")
            add("无固定时间 %d 项" % len(anon))
            for i in anon[:6]:
                add("• %s" % i["title"][:40])
            if len(anon) > 6:
                add("• …还有 %d 项" % (len(anon) - 6))

        conf = _conflicts([i for i in fixed if not is_done(i)])
        if conf:
            add("")
            add("时间冲突 %d 处——你决定是真并行还是去掉一个" % len(conf))
            for a, b in conf[:3]:
                add("• %s  %s(%s-%s) 撞 %s(%s-%s)" % (
                    day.strftime("%m-%d"), a["title"][:12], a["start"], a["end"],
                    b["title"][:12], b["start"], b["end"]))

    # 历史遗留：过期且未完成，最多 3 条
    # 历史遗留：只追最近 3 天，更早的不再打扰（数据不删，只是不提醒）
    stale = [i for i in items
             if is_live(i) and not is_done(i)
             and day - timedelta(days=STALE_DAYS) <= (item_end(i) or day) < day]
    stale.sort(key=lambda x: x.get("date") or "")
    if stale:
        add("")
        add("前 %d 天还有 %d 项没确认（要我处理就说）" % (STALE_DAYS, len(stale)))

    if done:
        add("")
        add("今天已完成 %d 项" % len(done))

    body = "\n".join(lines)
    if len(body) > MAX_MSG_CHARS:
        body = body[: MAX_MSG_CHARS - 16] + "\n…（已截断）"
    return body, open_items, fixed, conf if todays else []


# ---------------------------------------------------------------- 提醒去重

def reminder_path(d=None):
    return STATE_DIR / ("reminded_%s.json" % _d(d).isoformat())


def load_reminded(d=None):
    p = reminder_path(d)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_reminded(data, d=None):
    p = reminder_path(d)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def cleanup_old_state(keep_days=14):
    """清理超过 keep_days 的每日状态文件，防止无限增长"""
    cutoff = date.today() - timedelta(days=keep_days)
    for p in STATE_DIR.glob("*.json"):
        name = p.name
        for prefix in ("snapshot_", "reminded_", "evening_"):
            if name.startswith(prefix):
                try:
                    ds = name[len(prefix):-5]
                    if date.fromisoformat(ds) < cutoff:
                        p.unlink()
                except Exception:
                    pass
