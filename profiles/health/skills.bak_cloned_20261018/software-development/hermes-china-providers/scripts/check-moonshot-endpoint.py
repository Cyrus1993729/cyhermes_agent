#!/usr/bin/env python3
"""Test which Moonshot/Kimi endpoint a given API key works with.

Reads KIMI_API_KEY and KIMI_CN_API_KEY from ~/.hermes/.env and tests
both against the China (api.moonshot.cn) and international (api.moonshot.ai)
endpoints. Also checks for the common env-var mismatch: key is in
KIMI_API_KEY but user configured provider=moonshot-cn (which reads
KIMI_CN_API_KEY).

Usage:
    python scripts/check-moonshot-endpoint.py
"""

import os
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

# Resolve .env path
hermes_home = os.environ.get(
    "HERMES_HOME",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes"),
)
env_path = os.path.join(hermes_home, ".env")
if not os.path.exists(env_path):
    # Fallback for non-Windows
    env_path = os.path.join(os.path.expanduser("~"), ".hermes", ".env")

load_dotenv(env_path)

# Check both env vars
kimi_key = os.getenv("KIMI_API_KEY")
cn_key = os.getenv("KIMI_CN_API_KEY")

if not kimi_key and not cn_key:
    print("❌ Neither KIMI_API_KEY nor KIMI_CN_API_KEY found in .env")
    print("   Set one of them via: hermes config set env KIMI_API_KEY <your-key>")
    exit(1)

# Determine which key to test (prefer KIMI_API_KEY since it's the primary)
test_key = kimi_key or cn_key
print(f"Using key from {'KIMI_API_KEY' if kimi_key else 'KIMI_CN_API_KEY'}")
print(f"Key prefix: {test_key[:8]}...  length: {len(test_key)}")
print(f"KIMI_API_KEY set: {bool(kimi_key)}")
print(f"KIMI_CN_API_KEY set: {bool(cn_key)}")

ENDPOINTS = [
    ("https://api.moonshot.cn/v1/models",   "中国站 (moonshot-cn)"),
    ("https://api.moonshot.ai/v1/models",   "国际站 (moonshot)"),
]

results = []
for endpoint, label in ENDPOINTS:
    try:
        req = urllib.request.Request(
            endpoint,
            headers={"Authorization": f"Bearer {test_key}"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        models = [m["id"] for m in data.get("data", [])]
        print(f"✅ {label}: OK ({len(models)} models)")
        results.append((label, True, None))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ {label}: HTTP {e.code} - {body[:200]}")
        results.append((label, False, body))
    except Exception as e:
        print(f"❌ {label}: {e}")
        results.append((label, False, str(e)))

# Recommend fix
cn_ok = any(label.startswith("中国站") and ok for label, ok, _ in results)
intl_ok = any(label.startswith("国际站") and ok for label, ok, _ in results)

print()
if cn_ok and not intl_ok:
    if not cn_key:
        print("👉 Fix (2 steps):")
        print("   1. Add KIMI_CN_API_KEY to .env (same value as KIMI_API_KEY)")
        print("   2. hermes config set auxiliary.vision.provider moonshot-cn")
        print("   (Key works on China platform; moonshot-cn requires KIMI_CN_API_KEY)")
    else:
        print("👉 Fix: hermes config set auxiliary.vision.provider moonshot-cn")
        print("   (Key works on China platform only)")
elif intl_ok and not cn_ok:
    print("👉 Fix: hermes config set auxiliary.vision.provider moonshot")
    print("   (Key works on international platform only)")
elif cn_ok and intl_ok:
    print("✅ Key works on both endpoints — no endpoint mismatch")
else:
    print("❌ Key rejected by both endpoints — check key validity")
