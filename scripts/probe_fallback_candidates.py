import json, os, ssl, urllib.request, urllib.error, time, re, sys

ENV = r"C:\Users\Administrator\AppData\Local\hermes\.env"
key = None
for line in open(ENV, encoding="utf-8", errors="replace"):
    if line.startswith("OPENCODE_GO_API_KEY="):
        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not key:
    print("NO KEY"); sys.exit(1)

BASE = "https://opencode.ai/zen/go/v1"
UA = "hermes-agent/0.21.0"
ctx = ssl.create_default_context()

def probe(model, protocol="openai"):
    t0 = time.time()
    try:
        if protocol == "openai":
            url = BASE + "/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                       "User-Agent": UA, "x-opencode-session": "hermes-probe-1029"}
            body = {"model": model, "max_tokens": 32,
                    "messages": [{"role": "user", "content": "只回复两个字：可用"}]}
        else:
            url = BASE + "/messages"
            headers = {"Content-Type": "application/json", "x-api-key": key,
                       "anthropic-version": "2023-06-01", "User-Agent": UA,
                       "x-opencode-session": "hermes-probe-1029"}
            body = {"model": model, "max_tokens": 32,
                    "messages": [{"role": "user", "content": "只回复两个字：可用"}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
            d = json.loads(r.read().decode())
        dt = time.time() - t0
        if protocol == "openai":
            txt = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            txt = "".join(b.get("text", "") for b in d.get("content", []))
        return f"OK   {dt:5.1f}s  {model:20} [{protocol}]  -> {str(txt)[:40]!r}"
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        return f"FAIL {dt:5.1f}s  {model:20} [{protocol}]  HTTP {e.code}: {e.read().decode(errors='replace')[:160]}"
    except Exception as e:
        dt = time.time() - t0
        return f"ERR  {dt:5.1f}s  {model:20} [{protocol}]  {type(e).__name__}: {str(e)[:120]}"

CANDS = [
    ("deepseek-v4.1-flash", "openai"),
    ("gpt-6-luna", "openai"),
    ("kimi-k3", "openai"),
    ("glm-5.3-flash", "openai"),
    ("qwen3.8-max", "anthropic"),
]
for m, pr in CANDS:
    print(probe(m, pr), flush=True)
