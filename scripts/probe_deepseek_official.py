import json, os, ssl, urllib.request, urllib.error, time

path = r"C:\Users\Administrator\Desktop\各类api key\deepseek api key.txt"
key = open(path, encoding="utf-8", errors="replace").read().strip().strip('"').strip("'")
print("key 前缀:", key[:6], "长度:", len(key))
ctx = ssl.create_default_context()

def call(url, headers, data=None, method="GET"):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers=headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            return f"OK {r.status} ({time.time()-t0:.1f}s) " + r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} ({time.time()-t0:.1f}s) " + e.read().decode(errors="replace")[:300]
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:200]}"

H = {"Authorization": f"Bearer {key}", "User-Agent": "curl/8.0.0", "Content-Type": "application/json"}

print("\n[1] /models")
print(call("https://api.deepseek.com/v1/models", H))

print("\n[2] /user/balance")
print(call("https://api.deepseek.com/user/balance", H))

print("\n[3] chat deepseek-flash")
print(call("https://api.deepseek.com/v1/chat/completions", H,
           {"model": "deepseek-flash", "max_tokens": 16,
            "messages": [{"role": "user", "content": "只回复：可用"}]}, "POST"))
