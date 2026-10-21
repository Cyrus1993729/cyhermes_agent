# -*- coding: utf-8 -*-
"""视觉模型「输出不稳定 / JSON 解析失败」诊断探针。

用途：怀疑某个多模态模型识别结果飘忽时，先跑这个，**不要先怀疑采样随机**。
它把每次调用的 finish_reason 和 token 用量（尤其是 reasoning_tokens）打出来，
一眼就能看出是不是 max_tokens 卡得太紧导致 JSON 被截断。

典型结论长这样（2026-10 minimax-m3 实测）：
    reasoning_tokens   1244 / 5499 / 3572    ← 思考量波动极大
    completion_tokens  2604 / 6633 / 4753    ← 曾用满 6633，而当时上限只有 8000
    → 8000 的余量太薄，思考多一点 JSON 就写不完。改成 32000 后 5/5 稳定。

用法：
    python probe_vision_token_usage.py <图片路径> [--model minimax-m3] [--n 3] [--max-tokens 32000]

环境：
    - 走代理（本机默认 http://127.0.0.1:10808），可用 BH_PROXY 覆盖
    - key 从 ~/AppData/Local/hermes/.env 的 OPENCODE_GO_API_KEY 读
    - 必须带浏览器 UA + x-opencode-session 头，否则被网关拒
"""
import os
import re
import sys
import json
import time
import base64
import argparse
import urllib.request
import urllib.error

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ENV_FILE = os.path.expanduser("~/AppData/Local/hermes/.env")
BASE = "https://opencode.ai/inference/go/v1"
PROMPT_FILE = os.path.expanduser("~/health/tools/prompt_recognize.txt")


def api_key():
    m = re.search(r"^OPENCODE_GO_API_KEY\s*=\s*(.+)$",
                  open(ENV_FILE, encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("找不到 OPENCODE_GO_API_KEY")
    return m.group(1).strip().strip('"').strip("'")


def opener():
    proxy = os.environ.get("BH_PROXY", "http://127.0.0.1:10808")
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy}))


def call(model, b64, mime, prompt, max_tokens):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json",
                 "User-Agent": "hermes-agent/0.21.0",
                 "x-opencode-session": "vision-probe"},
    )
    t0 = time.time()
    try:
        with opener().open(req, timeout=600) as r:
            return json.loads(r.read().decode()), time.time() - t0, None
    except urllib.error.HTTPError as e:
        return None, time.time() - t0, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return None, time.time() - t0, f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--model", default="minimax-m3")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--prompt")
    a = ap.parse_args()

    prompt = open(a.prompt or PROMPT_FILE, encoding="utf-8").read()
    b64 = base64.b64encode(open(a.image, "rb").read()).decode()
    mime = "image/png" if a.image.lower().endswith(".png") else "image/jpeg"

    print(f"模型={a.model}  max_tokens={a.max_tokens}  跑 {a.n} 次")
    print(f"提示词 {len(prompt)} 字符 | 图片 base64 {len(b64)} 字符\n")

    ok_n, ct, rt, closed = 0, [], [], []
    for i in range(1, a.n + 1):
        j, el, err = call(a.model, b64, mime, prompt, a.max_tokens)
        if err:
            print(f"[{i}] {el:>5.0f}s  ❌ {err}")
            continue
        ch = (j.get("choices") or [{}])[0]
        content = (ch.get("message") or {}).get("content") or ""
        fr = ch.get("finish_reason")
        us = j.get("usage") or {}
        c = us.get("completion_tokens")
        r_ = (us.get("completion_tokens_details") or {}).get("reasoning_tokens")
        json_ok = content.strip().endswith("}") or "```" in content
        if json_ok:
            ok_n += 1
        if c:
            ct.append(c)
        if r_:
            rt.append(r_)
        if fr == "length":
            closed.append(i)
        print(f"[{i}] {el:>5.0f}s  finish={fr:<8} completion={c}  reasoning={r_}  "
              f"content={len(content)}字符  {'✓' if json_ok else '✗'}")

    print(f"\n完成 {ok_n}/{a.n}")
    if ct:
        print(f"completion_tokens 最大 {max(ct)}（上限 {a.max_tokens}，余量 {a.max_tokens - max(ct)}）")
    if rt:
        print(f"reasoning_tokens 最大 {max(rt)}")
    if closed:
        print(f"⚠️ 第 {closed} 次 finish_reason=length —— **确认是被 max_tokens 截断了**，往上加")
    if ct and max(ct) > a.max_tokens * 0.8:
        print("⚠️ 最大用量已超上限的 80%，余量偏薄，建议继续加 max_tokens")


if __name__ == "__main__":
    main()
