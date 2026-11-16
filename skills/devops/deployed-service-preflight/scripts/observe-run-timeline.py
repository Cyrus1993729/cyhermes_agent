#!/usr/bin/env python3
"""Read-only timeline for a work-automation observation JSONL (Dayflow 家主机等).

Usage:
    python observe-run-timeline.py <observation.jsonl> [N]

Prints, for the last N records (default 6):
    startedAt | finishedAt | error | calendar.complete/runId | mail.complete/runId/bodyFailures/analysisStopped
plus: total lines, unparseable lines, tail consecutive-error streak, error counts.

Never prints record bodies beyond the fields above; safe for A2A receipts.
"""

import io
import json
import sys
from collections import Counter


def short(value, limit=60):
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return "<obj>"
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    with io.open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()

    records, bad = [], 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            records.append(json.loads(raw))
        except Exception:
            bad += 1

    print("file=%s" % path)
    print("total_lines=%d parsed=%d unparseable=%d" % (len(lines), len(records), bad))
    if not records:
        print("verdict: no_parsed_records")
        return 0

    print("window=%s .. %s" % (records[0].get("startedAt"), records[-1].get("startedAt")))

    streak = 0
    first_failing = None
    for rec in reversed(records):
        if rec.get("error"):
            streak += 1
            first_failing = rec.get("startedAt")
        else:
            break
    print("tail_error_streak=%d%s" % (streak, " first=%s" % first_failing if streak else ""))

    counts = Counter(short(r.get("error"), 40) for r in records)
    print("error_counts=%s" % json.dumps(dict(counts), ensure_ascii=False))

    for rec in records[-limit:]:
        cal = rec.get("calendar") or {}
        mail = rec.get("mail") or {}
        print(
            "%s -> %s | err=%s | cal=%s/%s | mail=%s/%s/%s/%s"
            % (
                rec.get("startedAt"),
                rec.get("finishedAt"),
                short(rec.get("error")),
                cal.get("complete"),
                cal.get("runId"),
                mail.get("complete"),
                mail.get("runId"),
                mail.get("bodyFailures"),
                short(mail.get("analysisStopped")),
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
