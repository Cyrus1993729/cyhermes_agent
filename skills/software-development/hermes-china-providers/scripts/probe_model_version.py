#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""比对官方 API 与 OpenCode 网关的 system_fingerprint，判断后端是否同版本。

用法：
    python probe_model_version.py

改 TARGETS 可复用到任意「官方 vs 网关」模型对。

原理：system_fingerprint 由后端配置生成，换版本就变。这是判断模型后端是否
已切换到新版本的唯一硬证据。网关（opencode.ai）不透传该字段，所以本脚本对
网关侧会报 None —— 那是预期行为，不是 bug。
"""
import os
import ssl
import sys
import json
import urllib.request
import urllib.error

# ── 配置 ──────────────────────────────────────────────────────────
PROXY = os.environ.get("HERMES_PROXY", "http://127.0.0.1:10808")
HERMES_HOME = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")

GATEWAY_URL = "https://opencode.ai/zen/go/v1/chat/completions"
OFFICIAL_URL = "https://api.deepseek.com/v1/chat/completions"

# (标签, url, env里的key名, 模型名, 已知新指纹前缀, 已知旧指纹前缀)
TARGETS = [
    ("① OpenCode Go 网关 · deepseek-v4.1-flash",
     GATEWAY_URL, "OPENCODE_GO_API_KEY", "deepseek-v4.1-flash", "e72d3c7f", "aeb56401"),
    ("② DeepSeek 官方 · deepseek-flash（对照组）",
     OFFICIAL_URL, "DEEPSEEK_API_KEY", "deepseek-flash", "e72d3c7f", "aeb56401"),
]

CTX = ssl.create_default_context()


# ── 实现 ──────────────────────────────────────────────────────────
def load_env():
    d = {}
    path = os.path.join(HERMES_HOME, ".env")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return d


def probe(url, key, model, session_id):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        # 两个头都不能少：默认 urllib UA 被 Cloudflare 拦 → 403；
        # 缺 x-opencode-session → 400 MissingSessionID
        "User-Agent": "hermes-agent/0.21.0",
        "x-opencode-session": session_id,
    }
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX),
    )
    try:
        r = opener.open(urllib.request.Request(url, data=body, headers=headers), timeout=90)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode(errors="replace")[:300]}
    except Exception as e:
        return {"_err": f"{type(e).__name__}: {str(e)[:200]}"}


def main():
    env = load_env()
    results = {}

    for label, url, env_key, model, new_fp, old_fp in TARGETS:
        key = env.get(env_key, "")
        print("\n" + "=" * 64)
        print(label)
        print("=" * 64)
        if not key:
            print(f"  ⚠️ .env 里没有 {env_key}，跳过")
            continue

        res = probe(url, key, model, f"hermes-version-probe-{model[:12]}")
        if "_err" in res:
            print("  ❌ 连接错误:", res["_err"])
            continue
        if "_http_error" in res:
            print(f"  ❌ HTTP {res['_http_error']}: {res['_body']}")
            continue

        fp = res.get("system_fingerprint")
        print("  model        :", res.get("model"))
        print("  system_fp    :", fp)
        usage = res.get("usage") or {}
        print("  tokens       :", usage.get("prompt_tokens"), "->", usage.get("completion_tokens"))
        results[label] = fp

    print("\n" + "=" * 64)
    print("指纹汇总")
    print("=" * 64)
    new_fp = TARGETS[0][4]
    old_fp = TARGETS[0][5]
    for label, fp in results.items():
        if not fp:
            print(f"  ❓ {label}")
            print("     → 该接口不透传 system_fingerprint（OpenCode 网关的预期行为）")
            print("     → 改用行为指纹：references/model-version-verification.md 第 3 节")
        elif fp.startswith(new_fp):
            print(f"  ✅ {label} → 已是新版（{fp}）")
        elif fp.startswith(old_fp):
            print(f"  ⚠️ {label} → 仍是旧版（{fp}）")
        else:
            print(f"  ❓ {label} → {fp}（不在已知值里，需另行比对）")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
