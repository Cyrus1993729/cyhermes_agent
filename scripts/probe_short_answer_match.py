#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""短答案判定：网关 vs 官方是否同一后端（1017）。

设计要点：全部是**单值短答案**（一个数/一个词），输出空间极小，
同后端 + temperature=0 应该几乎逐字相同；不同后端会明显分叉。
"""
import os
import re
import ssl
import sys
import json
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
ENV = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", ".env")

PROMPTS = [
    "17 的平方是多少？只回答数字。",
    "中国的首都是哪里？只回答城市名。",
    "水的化学式是什么？只回答化学式。",
    "一年有多少个星期？（按 7 天整数算）只回答数字。",
    "二进制 1011 转成十进制是多少？只回答数字。",
    "「光合作用」发生在细胞的哪个细胞器？只回答名称。",
    "3 的 10 次方是多少？只回答数字。",
    "英语单词 book 的复数是什么？只回答单词。",
    "圆周率保留四位小数是多少？只回答数字。",
    "元素符号 Fe 代表哪种金属？只回答中文名称。",
]

CTX = ssl.create_default_context()


def load_env():
    d = {}
    with open(ENV, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def call(url, key, model, prompt, sess):
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 40, "temperature": 0,
                       "stream": False}).encode()
    h = {"Content-Type": "application/json", "Authorization": f"Bearer {key}",
         "User-Agent": "hermes-agent/0.21.0", "x-opencode-session": sess}
    op = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX))
    try:
        r = op.open(urllib.request.Request(url, data=body, headers=h), timeout=90)
        d = json.loads(r.read().decode())
        ch = (d.get("choices") or [{}])[0]
        return ((ch.get("message") or {}).get("content") or "").strip()
    except Exception as e:
        return f"<ERR {type(e).__name__}>"


def norm(s):
    return re.sub(r"[\s。，,、：:；;！!？?\"'`]+", "", s or "").lower()


env = load_env()
GW = "https://opencode.ai/zen/go/v1/chat/completions"
OF = "https://api.deepseek.com/v1/chat/completions"
oc, ds = env["OPENCODE_GO_API_KEY"], env["DEEPSEEK_API_KEY"]

same = 0
print(f"{'题目':<22}{'网关':<18}{'官方':<18}一致")
print("-" * 72)
for i, p in enumerate(PROMPTS, 1):
    g = call(GW, oc, "deepseek-v4.1-flash", p, f"hermes-sd-gw-{i}")
    o = call(OF, ds, "deepseek-flash", p, f"hermes-sd-of-{i}")
    eq = norm(g) == norm(o)
    same += eq
    label = p[:20].replace("\n", " ")
    print(f"{label:<22}{g[:16]:<18}{o[:16]:<18}{'✅' if eq else '❌'}")
    time.sleep(0.4)

print("-" * 72)
print(f"逐字一致：{same}/{len(PROMPTS)}  =  {same/len(PROMPTS):.0%}")
