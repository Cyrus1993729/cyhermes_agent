# -*- coding: utf-8 -*-
"""把饮食流水线架构问题简报发给 gpt-6-astra，产出写到 out 文件。"""
import os, re, subprocess, sys

BRIEF = r"C:\Users\Administrator\AppData\Local\hermes\scripts\astra_brief_diet_pipeline.md"
OUT = r"C:\Users\Administrator\AppData\Local\hermes\scripts\astra_out_diet_pipeline.txt"
CODEX = r"C:\Users\Administrator\.local\bin\codex.cmd"

prompt = open(BRIEF, encoding="utf-8").read()

env = dict(os.environ)
env["HTTP_PROXY"] = "http://127.0.0.1:10808"
env["HTTPS_PROXY"] = "http://127.0.0.1:10808"

r = subprocess.run(
    ["cmd.exe", "/c", CODEX, "exec", "--skip-git-repo-check",
     "--sandbox", "read-only", "-c", 'model="gpt-6-astra"'],
    input=prompt, capture_output=True, text=True, encoding="utf-8",
    errors="replace", timeout=1800, env=env,
    cwd=r"C:\Users\Administrator\AppData\Local\hermes\scripts",
)

raw = (r.stdout or "") + "\n" + (r.stderr or "")
# 清洗 ANSI / 控制字符
raw = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", raw)
raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)

if "usage limit" in raw or "hit your usage" in raw:
    print("QUOTA_BLOCKED")
    print(raw[-500:])
    sys.exit(2)

# 正文：取【最后一个】 codex 标记之后，到 tokens used 之前
body = raw
m = list(re.finditer(r"(?:^|\n)codex\n", raw))
if m:
    body = raw[m[-1].end():]
else:
    # 没有标记（异常输出）：砍掉 header 块
    i = raw.find("\n--------\n")
    if i != -1:
        j = raw.find("\n--------\n", i + 1)
        body = raw[j + len("\n--------\n"):] if j != -1 else raw
body = re.sub(r"\ntokens used\n[\d,]+.*$", "", body, flags=re.S)
body = re.sub(r"^\s*user\n.*?\ncodex\n", "", body, flags=re.S)

open(OUT, "w", encoding="utf-8").write(body)
print("exit:", r.returncode)
print("正文长度:", len(body))
print("--- 前 400 字 ---")
print(body[:400])
