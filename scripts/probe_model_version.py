#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探测 OpenCode Go 网关 / DeepSeek 官方后端实际模型版本（靠 system_fingerprint）。

判据来源：X @finalbsd 实测 —— V4.1-Flash 旧版 fingerprint = aeb56401，
1017 新版 = e72d3c7f。
"""
import os
import io
import ssl
import json
import urllib.request
import urllib.error

PROXY = "http://127.0.0.1:10808"
HOME = os.path.expanduser("~")
ENV = os.path.join(HOME, "AppData", "Local", "hermes", ".env")


def load_env():
    d = {}
    with open(ENV, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def post(url, key, model, session="version-probe", max_tokens=1):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "hermes-agent/0.21.0",
        "x-opencode-session": session,
    }
    ctx = ssl.create_default_context()
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=ctx),
    )
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        r = op.open(req, timeout=90)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode(errors="replace")[:300]}
    except Exception as e:
        return {"_err": f"{type(e).__name__}: {str(e)[:200]}"}


def show(label, res):
    print(f"\n{'='*62}\n{label}\n{'='*62}")
    if "_err" in res:
        print("  ❌ 连接错误:", res["_err"])
        return None
    if "_http_error" in res:
        print(f"  ❌ HTTP {res['_http_error']}: {res['_body']}")
        return None
    print("  model        :", res.get("model"))
    print("  system_fp    :", res.get("system_fingerprint"))
    print("  id           :", res.get("id"))
    u = res.get("usage") or {}
    print("  usage        :", {k: u.get(k) for k in ("prompt_tokens", "completion_tokens")})
    ch = (res.get("choices") or [{}])[0]
    print("  finish       :", ch.get("finish_reason"))
    return res.get("system_fingerprint")


def main():
    env = load_env()
    oc_key = env.get("OPENCODE_GO_API_KEY", "")
    ds_key = env.get("DEEPSEEK_API_KEY", "")
    print("OpenCode key:", ("有 " + oc_key[:6] + "…") if oc_key else "❌ 缺失")
    print("DeepSeek key:", ("有 " + ds_key[:6] + "…") if ds_key else "❌ 缺失")

    gw = "https://opencode.ai/zen/go/v1/chat/completions"
    of = "https://api.deepseek.com/v1/chat/completions"

    fps = {}
    fps["网关 deepseek-v4.1-flash"] = show(
        "① OpenCode Go 网关 · deepseek-v4.1-flash（我们主模型）",
        post(gw, oc_key, "deepseek-v4.1-flash", "hermes-version-probe-gw"))

    if ds_key:
        fps["官方 deepseek-flash"] = show(
            "② DeepSeek 官方 · deepseek-flash（对照组，可能余额不足）",
            post(of, ds_key, "deepseek-flash", "hermes-version-probe-off"))

    print(f"\n{'='*62}\n指纹汇总\n{'='*62}")
    for k, v in fps.items():
        print(f"  {k:<34} {v}")
    print("\n  已知：aeb56401 = 1017 之前的旧版 / e72d3c7f = V4.1-Flash-1017")
    for k, v in fps.items():
        if v == "e72d3c7f":
            print(f"  ✅ {k} → 已是 1017 版")
        elif v == "aeb56401":
            print(f"  ⚠️ {k} → 仍是 1017 之前的旧版")
        elif v:
            print(f"  ❓ {k} → {v}（不在已知两值里，需另查）")


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
