#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mem_gc.py — 记忆时效性扫描器（只读 / 只报告，不改任何文件）

扫描 MEMORY.md / USER.md，标记：
  [STALE]  带日期且含易变状态词、超过阈值天数的条目
  [VOLATILE] 含"待定/待充值/耗尽/临时/TODO"等未定状态、需复核
  [SUPERSEDED] 内容已迁移到 skill / 已被替代
  [DUP]    跨文件或同文件内的近重复条目（difflib 相似度）

用法:
  python mem_gc.py                     # 纯启发式，打印报告到 stdout
  python mem_gc.py --days 45           # 自定义 STALE 天数阈值（默认 30）
  python mem_gc.py --out report.md     # 报告写入文件
  python mem_gc.py --llm               # 额外调 qwen-bailian 做语义去重/时效判断
"""
import re, difflib, argparse
from pathlib import Path
from datetime import datetime

HERMES = Path(r"C:\Users\Administrator\AppData\Local\hermes")
MEM_FILES = [HERMES / "memories" / "MEMORY.md",
             HERMES / "memories" / "USER.md"]
CONFIG = HERMES / "config.yaml"

VOLATILE = ["待定", "待充值", "待重置", "耗尽", "已耗尽", "临时",
            "TODO", "待补", "未定", "待验证", "待确认"]
SUPERSEDED = ["已迁移", "已替代", "迁移为", "替代旧"]
DUP_THRESHOLD = 0.62          # SequenceMatcher 比率阈值
DATE_RE = re.compile(r"(?:(\d{4})-)?(\d{1,2})[-/](\d{1,2})")


def load_entries(path: Path):
    """按只含 § 的行切分，返回 [(行号, 文本)]。"""
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    entries, buf, start = [], [], 1
    for i, line in enumerate(raw, 1):
        if line.strip() == "§":
            if buf:
                entries.append((start, "\n".join(buf).strip()))
            buf, start = [], i + 1
        else:
            buf.append(line)
    if buf:
        entries.append((start, "\n".join(buf).strip()))
    return [(ln, t) for ln, t in entries if t]


def entry_age_days(text: str, today: datetime):
    """取条目中最早的一个日期，返回距今天数；无日期返回 None。"""
    best = None
    for m in DATE_RE.finditer(text):
        y, mo, d = m.groups()
        try:
            dt = datetime(int(y) if y else today.year, int(mo), int(d))
        except ValueError:
            continue
        if dt > today:            # 无年份且落在未来 → 归到去年
            dt = dt.replace(year=dt.year - 1)
        age = (today - dt).days
        best = age if best is None else max(best, age)
    return best


def norm(s: str):
    return re.sub(r"[\s，。、→()\[\]:：\-]", "", s)


def scan(days: int):
    today = datetime.now()
    flags = {"STALE": [], "VOLATILE": [], "SUPERSEDED": [], "DUP": []}
    all_entries = []  # (file, lineno, text)

    for path in MEM_FILES:
        for ln, text in load_entries(path):
            all_entries.append((path.name, ln, text))
            age = entry_age_days(text, today)
            has_vol = any(k in text for k in VOLATILE)
            if age is not None and age > days and has_vol:
                flags["STALE"].append((path.name, ln, age, text))
            elif has_vol:
                flags["VOLATILE"].append((path.name, ln, age, text))
            if any(re.search(p, text) for p in SUPERSEDED):
                flags["SUPERSEDED"].append((path.name, ln, age, text))

    # 跨条目近重复
    for i in range(len(all_entries)):
        for j in range(i + 1, len(all_entries)):
            fa, la, ta = all_entries[i]
            fb, lb, tb = all_entries[j]
            ratio = difflib.SequenceMatcher(None, norm(ta), norm(tb)).ratio()
            if ratio >= DUP_THRESHOLD:
                flags["DUP"].append((ratio, fa, la, ta, fb, lb, tb))
    flags["DUP"].sort(reverse=True)
    return flags


def render(flags, days):
    L = [f"# 记忆时效性扫描报告  ({datetime.now():%Y-%m-%d %H:%M})",
         f"STALE 阈值 = {days} 天。**本报告只提示，不改动任何文件。**\n"]

    def block(title, key, fmt):
        L.append(f"## {title}（{len(flags[key])}）")
        if not flags[key]:
            L.append("_无_\n"); return
        for item in flags[key]:
            L.append(fmt(item))
        L.append("")

    block("STALE — 过期易变，建议复核或删除", "STALE",
          lambda x: f"- `{x[0]}:{x[1]}` (约 {x[2]} 天前)\n  > {x[3][:120]}")
    block("VOLATILE — 未定状态，需确认现状", "VOLATILE",
          lambda x: f"- `{x[0]}:{x[1]}`\n  > {x[3][:120]}")
    block("SUPERSEDED — 疑似已迁移/被替代，可精简", "SUPERSEDED",
          lambda x: f"- `{x[0]}:{x[1]}`\n  > {x[3][:120]}")
    L.append(f"## DUP — 近重复条目对（{len(flags['DUP'])}）")
    if not flags["DUP"]:
        L.append("_无_")
    for r, fa, la, ta, fb, lb, tb in flags["DUP"]:
        L.append(f"- 相似度 {r:.2f}: `{fa}:{la}`  ↔  `{fb}:{lb}`\n"
                 f"  - A> {ta[:90]}\n  - B> {tb[:90]}")
    L.append("\n---\n处置建议：确认后用 memory 工具删除/合并，或手动编辑对应文件。")
    return "\n".join(L)


def read_qwen_cfg():
    txt = CONFIG.read_text(encoding="utf-8", errors="replace")
    blk = txt.split("qwen-bailian:", 1)[1]
    key = re.search(r"api_key:\s*(\S+)", blk).group(1)
    url = re.search(r"base_url:\s*(\S+)", blk).group(1)
    return key.strip(), url.strip().rstrip("/")


def llm_pass(flags):
    import json, urllib.request
    key, base = read_qwen_cfg()
    items = flags["DUP"][:20]
    if not items:
        return "（无 DUP 候选，跳过 LLM 复核）"
    payload = "\n".join(
        f"{i+1}. A[{fa}:{la}]={ta[:80]} || B[{fb}:{lb}]={tb[:80]}"
        for i, (r, fa, la, ta, fb, lb, tb) in enumerate(items))
    body = {
        "model": "qwen3.7-max",
        "messages": [
            {"role": "system", "content":
             "你是记忆库维护助手。对每对条目判断：MERGE（应合并）/KEEP（各有独立信息）/"
             "DELETE_A/DELETE_B。只输出编号+裁决+一句理由，中文。"},
            {"role": "user", "content": payload}],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out")
    ap.add_argument("--llm", action="store_true")
    a = ap.parse_args()

    flags = scan(a.days)
    report = render(flags, a.days)
    if a.llm:
        report += "\n\n## 千问 L 语义复核（DUP）\n" + llm_pass(flags)

    if a.out:
        Path(a.out).write_text(report, encoding="utf-8")
        print(f"已写入 {a.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
