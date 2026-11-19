#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_df73.py —— 73 号提醒补丁的离线验收（不发消息、不打云端、不碰真实状态目录）

跑法（必须带 DAYFLOW_DRY=1，双保险）：
    DAYFLOW_DRY=1 python tests73/test_df73.py

覆盖：
  A 纯虚构响应 + DAYFLOW_DRY=1 的干跑（真 df_common.send 的 dry 分支）
  B 判定分支：窗口 [13,18]（由 date/start + 北京时间算）、改期无时间窗、
    cancelled/待改期不兜底、非钉钉（含 source 缺失）不接管、钉钉缺 message 不发
  C 去重：新键 + 旧键「本地事项ID|开始时间|日期」兼容、跨轮不重发
  D ack：成功后落盘再 ack、幂等键稳定、ack 失败进 pending 队列、下轮只补 ack 不重发
  E 读取链路：直连带认证 GET 的路由与重试（403→200 自愈、5xx 重试、Retry-After、
    传输异常、坏 JSON），全部用注入的假 transport，绝不真连网
  F 正常响应：空列表、只有非钉钉候选都不算「未就绪」，零发送
  G df_watch73 与 df_watch 的分工：钉钉不再由快照发、非钉钉照旧
  H 线上文件零改动（哈希比对备份）
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAYFLOW = HERE.parent
sys.path.insert(0, str(DAYFLOW))

import df_common as C          # noqa: E402
import df_reminders73 as R     # noqa: E402
import df_watch as W           # noqa: E402
import df_watch73 as W73       # noqa: E402

FIXTURE = HERE / "due73_fictional.json"
FAKE_NOW = "2026-11-18T09:30:00"
FAKE_DAY = date(2026, 11, 18)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("%s %s%s" % ("PASS" if cond else "FAIL", name,
                       ("  <- " + detail) if (detail and not cond) else ""))


# ---------------------------------------------------------------- 沙箱

def sandbox():
    d = Path(tempfile.mkdtemp(prefix="df73_test_"))
    C.STATE_DIR = d
    return d


class Rec:
    """假通道：记录发出的消息，模拟成功/失败。"""
    def __init__(self, ok=True):
        self.texts, self.ok = [], ok

    def __call__(self, text, note_on_fallback=True):
        self.texts.append(text)
        return (True, "weixin") if self.ok else (False, "failed")


class FakeTransport:
    """假只读 HTTP：按预设序列返回 {status, body, err, retryAfter}，记录被请求的路由。"""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, route):
        self.calls.append(route)
        idx = min(len(self.calls), len(self.responses)) - 1
        r = self.responses[idx]
        return dict(r) if isinstance(r, dict) else r


def ok_list(cands):
    return {"status": 200, "body": json.dumps(cands, ensure_ascii=False), "err": ""}


def run_fixture(now_iso=FAKE_NOW, fixture=FIXTURE, seed=True, transport=None):
    now = datetime.fromisoformat(now_iso)
    day = now.date()
    if seed:
        # 夹具里 fx-legacy-dup 代表「旧脚本按旧键已送达过」
        rem = C.load_reminded(day)
        if "fx-item-008|09:45|2026-11-18" not in rem:
            rem["fx-item-008|09:45|2026-11-18"] = "2026-11-18T09:00:00"
            C.save_reminded(rem, day)
    # 注入 transport 时不走夹具，保证测的是读取链路
    use_fixture = None if transport is not None else (str(fixture) if fixture else None)
    return R.run(day=day, now=now, fixture=use_fixture, transport=transport)


def main():
    os.environ["DAYFLOW_DRY"] = "1"

    # ---------- A 干跑：真实 send 的 dry 分支 + 虚构响应
    print("\n== A 干跑（DAYFLOW_DRY=1，虚构响应）==")
    sandbox()
    res = run_fixture()
    check("A1 查询就绪（空/非钉钉也算就绪）", res["ready"] is True, str(res.get("error")))
    check("A2 干跑不发不落盘不 ack",
          all(a["result"] == "dry-skip" for a in res["ack"]))
    sent_keys = sorted(s["key"] for s in res["sent"] if s["ok"])
    check("A3 只发 2 条（窗口内普通 1 + 改期 1）",
          sent_keys == ["fx-change-far", "fx-normal-in-window"], str(sent_keys))
    check("A4 4 条无 source 的站点候选只被跳过、不算异常",
          len([s for s in res["skipped"] if s["why"] == "source-empty"]) == 4,
          str([s for s in res["skipped"] if s["why"].startswith("source")]))
    dry_rem = json.loads((C.STATE_DIR / "reminded_2026-11-18.json")
                         .read_text(encoding="utf-8"))
    check("A5 干跑不写任何 73 去重键",
          not [k for k in dry_rem if k.startswith("r73:")], str(list(dry_rem)))

    # ---------- B 判定分支
    print("\n== B 判定分支 ==")
    skipped = {s["key"]: s["why"] for s in res["skipped"]}
    check("B1 窗口外(25 分钟)跳过", skipped.get("fx-normal-too-early", "").startswith("window"))
    check("B2 窗口外(12 分钟)跳过", skipped.get("fx-normal-too-late", "").startswith("window"))
    check("B3 cancelled 不兜底", skipped.get("fx-cancelled") == "lifecycle-cancelled")
    check("B4 待改期不兜底（大小写归一）",
          skipped.get("fx-pending-reschedule") == "lifecycle-pendingreschedule")
    check("B5 非钉钉不接管（source 缺失同样不接管）",
          skipped.get("fx-hermes-source") == "source-hermes"
          and skipped.get("fx-plain-01|09:30|2026-11-18") == "source-empty",
          str({k: v for k, v in skipped.items() if v.startswith("source")}))
    check("B6 改期通知无时间窗（start 14:00 仍发）",
          "fx-change-far" in [s["key"] for s in res["sent"]])
    check("B7 钉钉缺 message 不发", skipped.get("fx-no-message") == "no-message")
    kinds = {s["key"]: s["kind"] for s in res["sent"]}
    check("B8 无 kind 视为普通会前（kind 缺失不报错）",
          kinds.get("fx-normal-in-window") == "pre-meeting"
          and kinds.get("fx-change-far") == "calendar-change", str(kinds))

    # 窗口边界：由 date/start 与 now 计算，不依赖 leadMinutes
    for start, want, tag in (("09:43", True, "13 分钟"),
                             ("09:48", True, "18 分钟"),
                             ("09:42", False, "12 分钟"),
                             ("09:49", False, "19 分钟")):
        c = R.normalize({"key": "edge-" + start, "source": "dingtalk",
                         "itemId": "fx-edge", "start": start,
                         "date": "2026-11-18", "message": "虚构边界"})
        got, why = R.classify(c, datetime(2026, 11, 18, 9, 30), FAKE_DAY, {})
        check("B9 边界 %s(%s) -> %s" % (start, tag, "发" if want else "不发"),
              got is want, why)

    # 北京时间口径：UTC 时间戳同样按 +08:00 折算
    lead_utc = R.minutes_until("09:45", "2026-11-18",
                               datetime(2026, 11, 18, 1, 30, tzinfo=timezone.utc))
    check("B10 北京时间口径（UTC 01:30 = 北京 09:30 -> 15 分钟）",
          lead_utc == 15.0, str(lead_utc))
    c_no_src = R.normalize({"key": "k", "date": "2026-11-18", "start": "09:45"})
    got, why = R.classify(c_no_src, datetime(2026, 11, 18, 9, 30), FAKE_DAY, {})
    check("B11 无 source 的候选在 source 处就停住（不再报缺 message/key）",
          why == "source-empty", why)

    # ---------- C 去重（注入假通道，模拟真实发送成功）
    print("\n== C 去重与旧键兼容 ==")
    os.environ["DAYFLOW_DRY"] = "0"   # 后面的状态机测试走真实分支，但通道是假的
    sandbox()
    C.send = Rec()                                     # 注入假通道
    R.do_ack = lambda key, retries=2: (True, {"ack": "ok",
                                             "requestId": R.ack_request_id(key)})
    r1 = run_fixture()
    check("C1 首轮发 2 条", len([s for s in r1["sent"] if s["ok"]]) == 2)
    rem = json.loads((C.STATE_DIR / "reminded_2026-11-18.json").read_text(encoding="utf-8"))
    check("C2 落盘带 73 键", "r73:fx-normal-in-window" in rem)
    check("C3 落盘带旧键（回滚兼容）",
          "fx-item-001|09:45|2026-11-18" in rem)
    check("C4 改期只落 73 键（无旧键）", "r73:fx-change-far" in rem)

    r2 = run_fixture()
    check("C5 第二轮零重发", [s for s in r2["sent"] if s["ok"]] == [])
    why2 = {s["key"]: s["why"] for s in r2["skipped"]}
    check("C6 第二轮按 dup 跳过",
          why2.get("fx-normal-in-window") == "dup-key"
          and why2.get("fx-change-far") == "dup-key")

    # 旧键已送达（老脚本发过，新键未见过）
    sandbox()
    C.send = Rec()
    C.save_reminded({"fx-item-008|09:45|2026-11-18": "2026-11-18T09:00:00"}, FAKE_DAY)
    r3 = run_fixture()
    why3 = {s["key"]: s["why"] for s in r3["skipped"]}
    check("C7 旧键已送达 -> dup-legacy 不重发", why3.get("fx-legacy-dup") == "dup-legacy")

    # ---------- D ack
    print("\n== D ack 语义 ==")
    sandbox()
    calls = []
    C.send = Rec()
    R.do_ack = lambda key, retries=2: (calls.append(key) or
                                       (True, {"ack": "ok",
                                               "requestId": R.ack_request_id(key)}))
    run_fixture()
    check("D1 渠道成功后才 ack，次数=2",
          sorted(calls) == sorted(["fx-normal-in-window", "fx-change-far"]), str(calls))
    rid_a = R.ack_request_id("fx-normal-in-window")
    rid_b = R.ack_request_id("fx-normal-in-window")
    check("D2 幂等键稳定（同 key 同 UUID）", rid_a == rid_b and len(rid_a) == 36, rid_a)

    # ack 失败 → 进 pending，不重发
    sandbox()
    C.send = Rec()
    R.do_ack = lambda key, retries=2: (False, {"ack": "failed",
                                              "requestId": R.ack_request_id(key)})
    r4 = run_fixture()
    pend = json.loads((C.STATE_DIR / "pending_ack_2026-11-18.json")
                      .read_text(encoding="utf-8"))
    check("D3 ack 失败进 pending 队列",
          sorted(p["key"] for p in pend) == ["fx-change-far", "fx-normal-in-window"])
    check("D4 ack 失败仍算已送达（本地去重已落）",
          r4["ack"] and all(a["result"] == "queued" for a in r4["ack"]))

    # 下一轮：ack 恢复 → 只补 ack，不发消息
    C.send = Rec()
    okack = []
    R.do_ack = lambda key, retries=2: (okack.append(key) or
                                       (True, {"ack": "ok",
                                               "requestId": R.ack_request_id(key)}))
    r5 = run_fixture()
    check("D5 下轮补 ack 成功", sorted(okack) == ["fx-change-far", "fx-normal-in-window"],
          str(okack))
    check("D6 补 ack 不发消息", [s for s in r5["sent"] if s["ok"]] == [])
    check("D7 pending 清空",
          not (C.STATE_DIR / "pending_ack_2026-11-18.json").exists())

    # 渠道失败 → 不落盘、不 ack
    sandbox()
    C.send = Rec(ok=False)
    ackd = []
    R.do_ack = lambda key, retries=2: (ackd.append(key) or
                                       (True, {"ack": "ok", "requestId": "x"}))
    run_fixture()
    check("D8 渠道失败不 ack", ackd == [])
    fail_rem = json.loads((C.STATE_DIR / "reminded_2026-11-18.json")
                          .read_text(encoding="utf-8"))
    check("D9 渠道失败不落去重（无 73 键、无新旧键）",
          not [k for k in fail_rem if k.startswith("r73:")]
          and "fx-item-001|09:45|2026-11-18" not in fail_rem, str(list(fail_rem)))

    # ---------- E 读取链路（注入假 transport，不联网）
    print("\n== E 直连读取：路由 / 重试 / 失败关闭 ==")
    check("E1 路由为 reminders/due?calendarChanges=1&lead=18",
          R.due_route() == "reminders/due?calendarChanges=1&lead=18", R.due_route())

    real_sleep = R.time.sleep
    slept = []

    class FakeTime:
        @staticmethod
        def sleep(sec):
            slept.append(sec)

    R.time = FakeTime
    try:
        # 403（Cloudflare 1010：缺 UA）后自愈
        sandbox()
        C.send = Rec()
        t = FakeTransport({"status": 403, "body": "error code: 1010", "err": "http-403"},
                          ok_list([{"key": "k403", "source": "hermes"}]))
        out = run_fixture(transport=t)
        check("E2 403 后重试成功（2 次请求）",
              out["query"] == "ok" and len(t.calls) == 2, str(t.calls))
        check("E3 重试仍打同一路由", set(t.calls) == {R.due_route()})

        # 5xx 重试用尽 -> 失败关闭，零发送
        sandbox()
        C.send = Rec()
        t = FakeTransport({"status": 503, "body": "", "err": "http-503"},
                          {"status": 502, "body": "", "err": "http-502"})
        out = run_fixture(transport=t)
        check("E4 5xx 两次仍失败 -> query=error / ready=False",
              out["query"] == "error" and out["ready"] is False and out["sent"] == [])
        check("E5 失败原因可核对（不含凭据）",
              out["error"] == "http-502", out["error"])

        # 429 + Retry-After
        sandbox()
        C.send = Rec()
        slept.clear()
        t = FakeTransport({"status": 429, "body": "", "err": "http-429", "retryAfter": 3},
                          ok_list([]))
        out = run_fixture(transport=t)
        check("E6 429 按 Retry-After=3 等待后重试", out["query"] == "ok" and slept == [3.0],
              str(slept))
        check("E7 空列表也算就绪、零发送", out["ready"] is True and out["sent"] == [])

        # Retry-After 过大时截断
        slept.clear()
        t = FakeTransport({"status": 429, "body": "", "err": "http-429", "retryAfter": 120},
                          ok_list([]))
        run_fixture(transport=t)
        check("E8 Retry-After 过长截断到 5s", slept == [R.RETRY_WAIT_MAX], str(slept))

        # 传输异常（status=0）两次
        sandbox()
        C.send = Rec()
        t = FakeTransport({"status": 0, "body": "", "err": "URLError:timed out"},
                          {"status": 0, "body": "", "err": "URLError:timed out"})
        out = run_fixture(transport=t)
        check("E9 传输异常两次 -> 失败关闭",
              out["query"] == "error" and out["sent"] == [], out["error"])

        # 坏 JSON 不重试
        sandbox()
        C.send = Rec()
        t = FakeTransport({"status": 200, "body": "<html>not json</html>", "err": ""})
        out = run_fixture(transport=t)
        check("E10 坏 JSON -> error 且不重试",
              out["query"] == "error" and len(t.calls) == 1 and out["error"] == "bad-json",
              "%s / calls=%d" % (out["error"], len(t.calls)))

        # 形态不认识（dict 无数组字段）
        sandbox()
        C.send = Rec()
        t = FakeTransport({"status": 200, "body": '{"unexpected":1}', "err": ""})
        out = run_fixture(transport=t)
        check("E11 形态不认识 -> ready=False / unexpected-shape",
              out["ready"] is False and out["error"] == "unexpected-shape" and out["sent"] == [])
    finally:
        R.time.sleep = real_sleep
        R.time = __import__("time")

    # ---------- F 只有非钉钉候选 = 正常响应
    print("\n== F 只有非钉钉候选 / 空列表 ==")
    sandbox()
    C.send = Rec()
    only_plain = [{"date": "2026-11-18", "end": "11:00", "itemId": "p1",
                   "key": "p1|09:45|2026-11-18", "start": "09:45", "title": "站点候选"}]
    t = FakeTransport(ok_list(only_plain))
    out = run_fixture(transport=t)
    check("F1 4→1 条非钉钉候选：ready=True、零发送、无 error",
          out["ready"] is True and out["sent"] == [] and out["error"] == "")
    check("F2 跳过原因记为 source-empty",
          [s["why"] for s in out["skipped"]] == ["source-empty"], str(out["skipped"]))

    sandbox()
    C.send = Rec()
    out = run_fixture(transport=FakeTransport(ok_list([])))
    check("F3 空列表：ready=True、零发送", out["ready"] is True and out["sent"] == [])

    # ---------- G df_watch73 与 df_watch 的分工
    print("\n== G 快照路径只发非钉钉（离线，虚构事项）==")
    sandbox()
    now = datetime.now()
    if now.hour >= 23:
        print("SKIP G（临近午夜，跨日会干扰）")
    else:
        s1 = (now + timedelta(minutes=15)).strftime("%H:%M")
        e1 = (now + timedelta(minutes=75)).strftime("%H:%M")
        fake_items = [
            {"id": "fx-dt", "title": "虚构钉钉会议", "date": now.date().isoformat(),
             "start": s1, "end": e1, "status": "pending", "source": "dingtalk",
             "plannedMinutes": 60},
            {"id": "fx-hm", "title": "虚构助理事项", "date": now.date().isoformat(),
             "start": s1, "end": e1, "status": "pending", "source": "hermes",
             "plannedMinutes": 60},
        ]
        C.get_items = lambda: fake_items
        rec = Rec()
        C.send = rec
        C.load_snapshot = lambda d=None: {"date": now.date().isoformat(),
                                          "savedAt": now.isoformat(timespec="seconds"),
                                          "source": "test",
                                          "items": [W._slim(i) for i in fake_items]}
        C.snapshot_age_minutes = lambda d=None: 1.0
        W73.main()
        check("G1 只发 1 条（钉钉不发、助理发）",
              len(rec.texts) == 1, "texts=%d" % len(rec.texts))
        check("G2 发出的是非钉钉事项",
              rec.texts and "虚构助理事项" in rec.texts[0])
        subj = rec.texts[0].split("\n")[1] if rec.texts else ""
        check("G3 提醒主体不是钉钉事项", subj == "虚构助理事项", subj)

    # ---------- H 线上文件零改动
    print("\n== H 线上文件哈希 ==")
    bak = DAYFLOW / "backup_73" / "df_watch.py.bak_20261118_1534"
    bakc = DAYFLOW / "backup_73" / "df_common.py.bak_20261118_1534"

    def h(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    check("H1 df_watch.py 未改动", h(DAYFLOW / "df_watch.py") == h(bak))
    check("H2 df_common.py 未改动", h(DAYFLOW / "df_common.py") == h(bakc))
    check("H3 新文件独立存在",
          (DAYFLOW / "df_reminders73.py").exists() and (DAYFLOW / "df_watch73.py").exists())

    print("\n---- 结果：PASS %d / FAIL %d ----" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败项：" + ", ".join(FAIL))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
