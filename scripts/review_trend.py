#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_trend.py — 审查趋势查看器

读取 review_log.jsonl，输出纵向评估报告。

用法:
  python review_trend.py             # 完整趋势报告
  python review_trend.py --last 10   # 只看最近 N 条
  python review_trend.py --summary   # 仅摘要
"""
import json, argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

REVIEW_LOG = Path(r"C:\Users\Administrator\AppData\Local\hermes\reviews\review_log.jsonl")


def load():
    if not REVIEW_LOG.exists():
        return []
    entries = []
    with open(REVIEW_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=0)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()

    all_entries = load()
    entries = all_entries[-a.last:] if a.last else all_entries

    if not entries:
        print("暂无审查记录。跑一次 qwen_review.py 后这里就有数据了。")
        return

    total = len(entries)
    verdicts = Counter(e["verdict"] for e in entries)
    escalates = sum(1 for e in entries if e["escalate"])
    fail_total = sum(e["fail_count"] for e in entries)
    cond_total = sum(e["cond_count"] for e in entries)

    print(f"# 审查趋势报告  ({datetime.now():%Y-%m-%d %H:%M})")
    print(f"累计审查: {total} 次  (日志共 {len(all_entries)} 条)")
    print(f"PASS {verdicts.get('PASS',0)} | CONDITIONAL {verdicts.get('CONDITIONAL',0)} | FAIL {verdicts.get('FAIL',0)}")
    print(f"升级建议: {escalates} 次")
    print(f"累计 FAIL 条目: {fail_total} | CONDITIONAL 条目: {cond_total}")
    print()

    if a.summary:
        return

    # 最近 10 条明细
    recent = entries[-10:]
    print("## 最近审查明细")
    print(f"{'时间':<22} {'任务':<30} {'裁决':<14} {'F/C/总数'}")
    for e in recent:
        ts = e["ts"][:19].replace("T", " ")
        task = e["task"][:30]
        v = e["verdict"]
        fc = f"{e['fail_count']}/{e['cond_count']}/{e['total_items']}"
        print(f"{ts:<22} {task:<30} {v:<14} {fc}")

    # 趋势判断
    if total >= 3:
        recent_pass = sum(1 for e in entries[-3:] if e["verdict"] == "PASS")
        early_pass = sum(1 for e in entries[:3] if e["verdict"] == "PASS")
        recent_fail = sum(e["fail_count"] for e in entries[-3:])
        early_fail = sum(e["fail_count"] for e in entries[:3])

        print()
        if recent_pass > early_pass:
            print("📈 趋势: 近期 PASS 率上升，审查质量在改善")
        elif recent_pass < early_pass:
            print("📉 趋势: 近期 PASS 率下降，可能需要关注")
        else:
            print("➡️ 趋势: 稳定")

        if recent_fail < early_fail:
            print("📈 FAIL 条目数在减少")
        elif recent_fail > early_fail:
            print("📉 FAIL 条目数在增加")

    if total > 0 and escalates / total > 0.5:
        print(f"\n⚠️ 升级率 {escalates/total:.0%}，超过一半的审查建议升级 Opus")


if __name__ == "__main__":
    main()
