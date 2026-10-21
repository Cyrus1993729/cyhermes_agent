#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""行为指纹对比：OpenCode Go 网关 vs DeepSeek 官方，判断是否同一后端（1017）。

原理：官方已确认是 V4.1-Flash-1017（system_fingerprint=e72d3c7f…）。
网关不透传 fingerprint，所以改用 temperature=0 的输出一致性做旁证：
  - 同一后端 → 输出应高度一致
  - 不同后端（自建旧权重）→ 输出差异明显
"""
import os
import ssl
import json
import time
import urllib.request

PROXY = "http://127.0.0.1:10808"
HOME = os.path.expanduser("~")
ENV = os.path.join(HOME, "AppData", "Local", "hermes", ".env")

PROMPTS = [
    ("版本自述", "你现在运行的是 DeepSeek 的哪个版本？如果知道具体版本号（例如 V4.1-Flash-1017）就直说，不知道就说不知道。只回答一行。"),
    ("编程", "用 Python 写一个函数，判断一个整数是否为素数。只给代码，不要解释。"),
    ("推理", "一个笼子里有鸡和兔共 35 只，脚共 94 只。鸡和兔各几只？只给数字和一行推理。"),
    ("中文概括", "用一句话（不超过 30 字）说明什么是复利。"),
    ("工具调用意识", "要查今天的天气，你会调用什么工具？只回答工具名，没有就说没有。"),
]


def load_env():
    d = {}
    with open(ENV, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


CTX = ssl.create_default_context()


def call(url, key, model, prompt, session, max_tokens=300):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "hermes-agent/0.21.0",
        "x-opencode-session": session,
    }
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX))
    t0 = time.time()
    try:
        r = op.open(urllib.request.Request(url, data=body, headers=headers), timeout=120)
        d = json.loads(r.read().decode())
        dt = time.time() - t0
        ch = (d.get("choices") or [{}])[0]
        txt = (ch.get("message") or {}).get("content") or ""
        u = d.get("usage") or {}
        return {"ok": True, "text": txt.strip(), "sec": round(dt, 2),
                "out_tok": u.get("completion_tokens"),
                "fp": d.get("system_fingerprint")}
    except Exception as e:
        return {"ok": False, "text": f"<ERR {type(e).__name__}: {str(e)[:120]}>",
                "sec": round(time.time() - t0, 2), "out_tok": None, "fp": None}


def norm(s):
    """粗归一：去空白/标点差异，用于相似度粗判。"""
    import re
    return re.sub(r"\s+", "", s or "")


def main():
    env = load_env()
    oc, ds = env.get("OPENCODE_GO_API_KEY", ""), env.get("DEEPSEEK_API_KEY", "")
    GW = "https://opencode.ai/zen/go/v1/chat/completions"
    OF = "https://api.deepseek.com/v1/chat/completions"

    rows = []
    for i, (label, p) in enumerate(PROMPTS, 1):
        g = call(GW, oc, "deepseek-v4.1-flash", p, f"hermes-bp-gw-{i}")
        o = call(OF, ds, "deepseek-flash", p, f"hermes-bp-of-{i}")
        same = norm(g["text"]) == norm(o["text"])
        rows.append((label, g, o, same))
        print(f"\n【{label}】输出{'完全一致 ✅' if same else '不同 ⚠️'}")
        print(f"  网关 fp={g['fp']} {g['sec']}s {g['out_tok']}tok")
        print(f"  官方 fp={(o['fp'] or '')[:8]} {o['sec']}s {o['out_tok']}tok")
        print(f"  网关: {g['text'][:150]!r}")
        print(f"  官方: {o['text'][:150]!r}")

    same_n = sum(1 for r in rows if r[3])
    print("\n" + "=" * 64)
    print(f"输出完全一致：{same_n}/{len(rows)}")
    gtok = sum((r[1]['out_tok'] or 0) for r in rows)
    otok = sum((r[2]['out_tok'] or 0) for r in rows)
    gsec = sum(r[1]['sec'] for r in rows)
    osec = sum(r[2]['sec'] for r in rows)
    print(f"总输出 token：网关 {gtok} / 官方 {otok}（差 {gtok-otok:+d}）")
    print(f"总耗时      ：网关 {gsec:.1f}s / 官方 {osec:.1f}s")
    print("=" * 64)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
