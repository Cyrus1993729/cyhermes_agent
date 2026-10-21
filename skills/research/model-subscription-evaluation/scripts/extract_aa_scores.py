#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 Artificial Analysis 页面挖出**逐模型分项分数**（图表数据，正文取不到）。

为什么需要这个脚本
------------------
AA 的对比页/评测页上，Intelligence Index、AutomationBench-AA、Terminal-Bench、
AA-AnalystAgent 等分项**在正文里是空的**——`web_extract` 只能拿到图表标题和
图例，拿不到数字（图表是客户端渲染的）。

真实数值埋在页面内嵌 JSON 里，字段形如：

    "name":"DeepSeek V4.1 Flash 1017",
    "intelligenceIndex":45.0965048681912,
    "automationBenchPartialScore":0.6664095364949257,
    "automationBenchBreakdown":{"strictScore":0.3668,"completion":0.8794,
                                "violationsPerTask":0.359,"violations":3800,...}

两个 JSON 源都要扫（Next.js App Router 两种写法并存）：
  1. `<script type="application/json">...</script>`
  2. `self.__next_f.push([1,"..."])` —— 内容是 escaped 的 JSON 片段

用法
----
    # 默认抓 AutomationBench-AA 页，列出模型订阅里关心的那些
    python extract_aa_scores.py

    # 指定页面
    python extract_aa_scores.py --url https://artificialanalysis.ai/evaluations/terminalbench-4-0

    # 列出全部解析到的模型（不过滤）
    python extract_aa_scores.py --all

    # 自定义过滤
    python extract_aa_scores.py --models deepseek glm kimi

实测（2026-10-20）：AutomationBench 页解析出 69 个模型记录。
注意 AA 会为同一模型建多条（如 `DeepSeek V4.1 Flash` 与
`DeepSeek V4.1 Flash 1017` 是两个独立条目，分数不同）——**别把版本混为一谈**。
"""
import argparse
import json
import re
import ssl
import sys
import urllib.request

DEFAULT_URL = "https://artificialanalysis.ai/evaluations/automationbench-aa"
DEFAULT_PROXY = "http://127.0.0.1:10808"

# 订阅选型时默认关心的模型（子串匹配，大小写不敏感）
DEFAULT_TARGETS = [
    "deepseek", "glm-5.3", "mimo-v2.6", "longcat", "hy3", "hy4",
    "qwen3.8", "qwen3.7", "kimi", "gpt-6", "gpt 6", "gpt-5.6", "gpt 5.6",
    "claude haiku", "claude sonnet", "claude opus", "grok", "gemini", "step 5",
    "muse spark", "minimax",
]

# 分项字段 → 展示名。值 ≤1.5 视为 0-1 比例，乘 100。
FIELDS = {
    "intelligenceIndex": ("AA 总分", 1),
    "automationBenchPartialScore": ("AutoBench", 100),
    "analystAgent": ("AnalystAgent", 100),
    "terminalBench40": ("TerminalBench4", 100),
    "scicode": ("SciCode", 100),
    "critpt": ("CritPt", 100),
    "briefcase": ("Briefcase", 100),
    "omniscience": ("Omniscience", 100),
    "lcr": ("LCR", 100),
}


def fetch(url, proxy):
    ctx = ssl.create_default_context()
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    if proxy:
        handlers.insert(0, urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    op = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; hermes-agent/0.21.0)"})
    with op.open(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def json_blobs(raw):
    """抽出页面里所有内嵌 JSON 片段（两种 Next.js 写法）。"""
    out = []
    for m in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', raw, re.S):
        out.append(m.group(1))
    for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', raw, re.S):
        try:
            out.append(m.group(1).encode().decode("unicode_escape", "replace"))
        except Exception:
            out.append(m.group(1))
    return out


def parse_records(blobs):
    """找 `"name":"<模型>"` 及其后 6000 字符内的分项字段。"""
    recs = {}
    for blob in blobs:
        for m in re.finditer(r'"name":"([^"]{2,60})"', blob):
            name = m.group(1)
            seg = blob[m.start(): m.start() + 6000]
            rec = {}
            for key, (_label, _scale) in FIELDS.items():
                mm = re.search(rf'"{key}":([0-9.]+)', seg)
                if mm:
                    rec[key] = float(mm.group(1))
            br = re.search(r'"automationBenchBreakdown":\{([^}]*)\}', seg)
            if br:
                rec["_breakdown"] = {
                    k: float(v) for k, v in re.findall(r'"(\w+)":([0-9.]+)', br.group(1))}
            # 必须有至少一个真实分数才算数（过滤掉只有 name 的壳）
            if any(k in rec for k in FIELDS):
                recs.setdefault(name, {}).update(rec)
    return recs


def fmt(v, scale):
    if v is None:
        return "-"
    return f"{v * scale:.1f}" if scale == 100 else f"{v:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--proxy", default=DEFAULT_PROXY, help="设为 '' 关闭代理")
    ap.add_argument("--models", nargs="*", default=None, help="子串过滤；省略则用内置候选表")
    ap.add_argument("--all", action="store_true", help="不过滤，列出全部")
    ap.add_argument("--breakdown", action="store_true", help="打印 AutoBench 明细")
    args = ap.parse_args()

    raw = fetch(args.url, args.proxy or None)
    blobs = json_blobs(raw)
    recs = parse_records(blobs)
    if not recs:
        print(f"❌ 没解析到任何记录（HTML {len(raw):,} 字节 / {len(blobs)} 个 JSON 块）")
        print("   检查：页面是否换了渲染方式，或字段名是否改名。")
        return 1

    targets = None if args.all else (args.models or DEFAULT_TARGETS)
    rows = []
    for name, rec in recs.items():
        if targets and not any(t.lower() in name.lower() for t in targets):
            continue
        rows.append((name, rec))
    if not rows:
        print(f"⚠️ 解析到 {len(recs)} 个模型，但没有匹配过滤词的。加 --all 看看全部名字。")
        return 0

    rows.sort(key=lambda x: -(x[1].get("automationBenchPartialScore") or
                              x[1].get("intelligenceIndex") or 0))

    head = f"{'模型':<32}" + "".join(f"{label:>14}" for label, _ in FIELDS.values())
    print(f"\n数据源: {args.url}")
    print(f"解析到 {len(recs)} 个模型，显示 {len(rows)} 个\n")
    print(head)
    print("-" * len(head))
    for name, rec in rows:
        line = f"{name[:31]:<32}"
        for key, (_label, scale) in FIELDS.items():
            line += f"{fmt(rec.get(key), scale):>14}"
        print(line)
        if args.breakdown and rec.get("_breakdown"):
            bd = rec["_breakdown"]
            bits = [f"{k}={bd[k] * 100:.1f}%" for k in
                    ("strictScore", "completion", "violationsPerTask") if k in bd]
            if bits:
                print(f"{'':<32}" + "  ".join(bits))

    print("\n⚠️ AA 会为同一模型建多条独立记录（如 `DeepSeek V4.1 Flash` 与")
    print("   `DeepSeek V4.1 Flash 1017` 分数不同）——**别把版本混为一谈**。")
    print("⚠️ AA 的速度/延迟是首方 API 数字，走中转网关会差很多 →")
    print("   速度只信 scripts/model_probe.py 的本地实测。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
