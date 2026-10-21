#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""找外部实测证据：Reddit 原帖（走 json API）+ docs/go 的 ZDR 星号脚注。"""
import re
import ssl
import sys
import json
import html
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PROXY = "http://127.0.0.1:10808"
CTX = ssl.create_default_context()
OP = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
    urllib.request.HTTPSHandler(context=CTX))


def get(u, ua="Mozilla/5.0 (compatible; hermes-agent/0.21.0)"):
    r = OP.open(urllib.request.Request(u, headers={"User-Agent": ua}), timeout=45)
    return r.read().decode("utf-8", "replace")


print("=" * 72)
print("① Reddit 原帖：Does Opencode use Deepseek flash 4.1 1017?")
print("=" * 72)
for u in ["https://www.reddit.com/r/opencode/comments/1x8z8jz/.json",
          "https://old.reddit.com/r/opencode/comments/1x8z8jz/.json"]:
    try:
        d = json.loads(get(u))
        post = d[0]["data"]["children"][0]["data"]
        print(f"\n  标题: {post.get('title')}")
        print(f"  正文: {(post.get('selftext') or '')[:600]}")
        print(f"  时间: {post.get('created_utc')}  评论数: {post.get('num_comments')}")
        comments = d[1]["data"]["children"]
        print(f"\n  --- 评论（共 {len(comments)}）---")
        shown = 0
        for c in comments:
            cd = c.get("data") or {}
            body = (cd.get("body") or "").strip()
            if not body or body in ("[deleted]", "[removed]"):
                continue
            print(f"\n  [{cd.get('author')}] {body[:700]}")
            shown += 1
            if shown >= 8:
                break
        if shown == 0:
            print("  （无有效评论）")
        break
    except Exception as e:
        print(f"  {u} ❌ {type(e).__name__}: {str(e)[:100]}")

print("\n\n" + "=" * 72)
print("② docs/go 里 DeepSeek 那行 ZDR 的完整脚注")
print("=" * 72)
try:
    t = get("https://opencode.ai/docs/go")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t)
    i = t.find("DeepSeek V4.1 Flash Not used")
    if i < 0:
        i = t.find("Not used 0 days*")
    if i >= 0:
        print("\n  …" + t[i:i + 700] + "…")
    else:
        j = t.find("ZDR")
        print("\n  [ZDR 段] …" + t[max(0, j - 300):j + 900] + "…")
except Exception as e:
    print("  ❌", e)
