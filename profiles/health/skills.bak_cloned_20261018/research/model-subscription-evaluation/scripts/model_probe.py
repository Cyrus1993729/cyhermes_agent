#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenCode Go 候选模型「双探针」体检：① 工具调用能力 ② 流式长文本吞吐。

为什么必须跑两个探针
--------------------
小工具探针只输出 12-70 个 token，**完全暴露不出慢模型**。
2026-10-08 实踩：GLM-5.3-Flash 的小工具探针 1.5s 返回（全场最快），
但让它写 200 字花了 **117.5 秒**（中途思考 3658 字）、写 400 字 **150 秒没吐出正文**。
单看小探针，它会以「AA 42 分 > DeepSeek 39 分、额度只占 20%」的姿态被选成主力，
而实际上一轮 20-27 次调用的会话要跑一小时。

用法
----
python model_probe.py deepseek-v4.1-flash glm-5.3-flash mimo-v2.6-pro
python model_probe.py --no-long glm-5.3-flash          # 只跑工具探针
python model_probe.py --proxy http://127.0.0.1:10808 --endpoint <url> <model> ...

四个必须遵守的姿势（实测踩出来的）
----------------------------------
1. **POST 一律用 curl**（本脚本用 subprocess 调 curl）。urllib POST chat/completions
   实测连续 RemoteDisconnected；requests 亦可，但 curl 最省事。
2. **User-Agent: curl/8.0.0** —— 网关的 Cloudflare 会对默认 urllib UA 返 403（1010）。
3. **x-opencode-session** —— 缺了直接 400 MissingSessionID，请求无法路由。
4. **长文本用 stream:true** —— 非流式长生成会被代理掐断（curl exit 56/35，响应为空）。

依赖：只用标准库。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

DEFAULT_ENDPOINT = "https://opencode.ai/zen/go/v1/chat/completions"
DEFAULT_PROXY = "http://127.0.0.1:10808"
ENV_FILE = os.path.expanduser("~/AppData/Local/hermes/.env")
KEY_FILES = [
    os.path.expanduser("~/Desktop/各类api key/opencode go api key.txt"),
]

TOOL_PROMPT = "帮我查一下苏州今天天气，然后告诉我穿什么"
TOOL_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询城市天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

LONG_PROMPT = "用大约400字介绍苏州工业园区的产业结构，直接输出正文"


def load_key() -> str | None:
    key = os.environ.get("OPENCODE_GO_API_KEY")
    if key:
        return key.strip()
    for path in KEY_FILES:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            continue
    try:
        with open(ENV_FILE, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("OPENCODE_GO_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def _curl(args: list[str], body: str, timeout: int) -> bytes:
    """调 curl 发 POST，body 走 stdin（避免 MSYS 下 @file 的相对路径问题）。"""
    proc = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), "-N", *args,
         "-X", "POST", "--data-binary", "@-"],
        input=body.encode("utf-8"), capture_output=True, timeout=timeout + 25,
    )
    return proc.stdout


def _headers(key: str, tag: str) -> list[str]:
    return [
        "-H", f"Authorization: Bearer {key}",
        "-H", "User-Agent: curl/8.0.0",
        "-H", f"x-opencode-session: hermes-script-{tag}",
        "-H", "Content-Type: application/json",
    ]


def probe_tools(model: str, endpoint: str, proxy: str, key: str, timeout: int) -> str:
    """小探针：模型会不会真的发起 tool_call（而不是退化成纯文本回复）。"""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": TOOL_PROMPT}],
        "tools": TOOL_SCHEMA,
        "tool_choice": "auto",
        "max_tokens": 300,
    })
    raw = _curl(["-x", proxy, *_headers(key, "tool-probe"), endpoint], body, timeout)
    try:
        data = json.loads(raw.decode("utf-8", "ignore"))
    except Exception:
        return f"❌ 解析失败 / 空响应：{raw[:120]!r}"
    if "error" in data:
        return f"❌ {str(data['error'])[:110]}"
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    calls = msg.get("tool_calls")
    usage = data.get("usage") or {}
    if calls:
        fn = calls[0].get("function") or {}
        arg = str(fn.get("arguments"))[:40]
        return f"✅ 调工具 {fn.get('name')}({arg}) out={usage.get('completion_tokens')}tok"
    return f"⚠️ 未调工具 · 纯文本：{str(msg.get('content'))[:60]}"


def probe_long(model: str, endpoint: str, proxy: str, key: str, timeout: int) -> str:
    """长探针：流式生成约 400 字，量墙钟 / 首字 / 正文 / 思考 / finish_reason。

    finish_reason=None 且耗时贴住 timeout = 被超时截断（模型太慢，等于不可用）。
    """
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": LONG_PROMPT}],
        "max_tokens": 3000,
        "stream": True,
    })
    t0 = time.time()
    raw = _curl(["-x", proxy, *_headers(key, "long-probe"), endpoint], body, timeout)
    elapsed = time.time() - t0
    content = reasoning = 0
    finish = None
    err = None
    for line in raw.decode("utf-8", "ignore").splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except Exception:
            continue
        if "error" in chunk:
            err = str(chunk["error"])[:110]
            break
        choice = (chunk.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        content += len(delta.get("content") or "")
        reasoning += len(delta.get("reasoning_content") or "")
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
    if err:
        return f"❌ {err}"
    cps = content / max(elapsed, 0.001)
    flag = ""
    if finish is None and elapsed >= timeout - 5:
        flag = "  ⛔ 超时截断（慢到不可用）"
    elif cps < 20:
        flag = "  ⚠️ 正文字/秒 <20，agent loop 会很痛苦"
    return (f"墙钟 {elapsed:6.1f}s · 正文 {content:5d} 字 · 思考 {reasoning:5d} 字 · "
            f"{cps:5.1f} 字/s · finish={finish}{flag}")


def main() -> int:
    ap = argparse.ArgumentParser(description="OpenCode Go 候选模型双探针体检")
    ap.add_argument("models", nargs="+", help="模型 ID（套餐文档里的 model ID）")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY") or DEFAULT_PROXY)
    ap.add_argument("--tool-timeout", type=int, default=90)
    ap.add_argument("--long-timeout", type=int, default=150,
                    help="长探针单模型上限秒数；贴住这个值说明模型慢到不可用")
    ap.add_argument("--no-long", action="store_true", help="只跑工具探针")
    args = ap.parse_args()

    key = load_key()
    if not key:
        print("❌ 找不到 OPENCODE_GO_API_KEY（env / .env / Desktop key 文件均未命中）")
        return 2

    print(f"endpoint = {args.endpoint}")
    print(f"proxy    = {args.proxy}\n")
    for model in args.models:
        print(f"── {model}")
        print(f"   工具探针  {probe_tools(model, args.endpoint, args.proxy, key, args.tool_timeout)}")
        if not args.no_long:
            print(f"   长文探针  {probe_long(model, args.endpoint, args.proxy, key, args.long_timeout)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
