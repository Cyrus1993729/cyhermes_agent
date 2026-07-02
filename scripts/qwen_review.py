#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen_review.py — L1 固定审查层（千问 3.7 Max）
直连 qwen-bailian /chat/completions，不经 delegate_task、不受 delegation.provider 影响。

用法:
  python qwen_review.py --contract contract.md --deliverable report.md
  echo "<交付物文本>" | python qwen_review.py --contract contract.md --deliverable -
输出: PASS / CONDITIONAL / FAIL + 逐条裁决（JSON + 人读摘要），只报告不改文件。
"""
import re, sys, json, argparse, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

CONFIG = Path(r"C:\Users\Administrator\AppData\Local\hermes\config.yaml")
REVIEWS_DIR = Path(r"C:\Users\Administrator\AppData\Local\hermes\reviews")
REVIEW_LOG = REVIEWS_DIR / "review_log.jsonl"

RUBRIC = """你是 L1 固定审查层。对照【任务契约】逐条审查【交付物】，只审交付物不审过程。
审查三维度，每条结论单独裁决，禁止打包：
1. 任务完成度：契约里每个交付项/验收标准是否达成。
2. 论证质量：把关键论断按【事实 / 推理 / 判断】三分类，检查——
   - 事实：有无权威来源？口径是否统一（拒绝不同标准混比）？有无编造数据/引用？
   - 推理：是否从第一性原理推导？有无预设立场？
   - 判断：边界条件是否成立？
3. 风险合规：越界、遗漏边界条件、凭证/安全红线。
对每条给：结论(PASS/CONDITIONAL/FAIL) + 依据 + 修复建议。
最后给总裁决：全 PASS→PASS；有 CONDITIONAL 无 FAIL→CONDITIONAL；任一 FAIL→FAIL。
CONDITIONAL≥3 条或任一 FAIL → 建议升级 Opus（人工手动）。
严格输出 JSON: {"verdict":"...","escalate":bool,"items":[{"claim":"","type":"事实|推理|判断|完成度|合规","result":"","reason":"","fix":""}],"summary":""}"""


def read_qwen_cfg():
    txt = CONFIG.read_text(encoding="utf-8", errors="replace")
    blk = txt.split("qwen-bailian:", 1)[1]
    key = re.search(r"api_key:\s*(\S+)", blk).group(1).strip()
    url = re.search(r"base_url:\s*(\S+)", blk).group(1).strip().rstrip("/")
    return key, url


def call_qwen(contract: str, deliverable: str):
    key, base = read_qwen_cfg()
    body = {
        "model": "qwen3.7-max",
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content":
             f"【任务契约】\n{contract}\n\n【交付物】\n{deliverable}"}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read())
        return raw["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[L1 ERROR] HTTP {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(2)
    except urllib.error.URLError as e:
        print(f"[L1 ERROR] 千问 API 不可达: {e.reason}", file=sys.stderr)
        sys.exit(2)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[L1 ERROR] 千问返回格式异常: {e}", file=sys.stderr)
        sys.exit(2)


def load(arg):
    if arg == "-":
        return sys.stdin.read()
    return Path(arg).read_text(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--deliverable", required=True)
    a = ap.parse_args()
    out = call_qwen(load(a.contract), load(a.deliverable))
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        print(out); return

    # --- 确定性重算 verdict / escalate（不信任 LLM 自评）---
    items = obj.get("items", [])
    fail_count = sum(1 for it in items if it.get("result") == "FAIL")
    cond_count = sum(1 for it in items if it.get("result") == "CONDITIONAL")
    if fail_count > 0:
        verdict = "FAIL"
    elif cond_count > 0:
        verdict = "CONDITIONAL"
    else:
        verdict = "PASS"
    escalate = fail_count > 0 or cond_count >= 3
    # ---------------------------------------------------------

    print(f"===== L1 裁决: {verdict} "
          f"| 升级Opus: {escalate} =====")
    for it in obj.get("items", []):
        print(f"[{it['result']}] ({it['type']}) {it['claim']}")
        print(f"    依据: {it['reason']}")
        if it.get("fix"):
            print(f"    修复: {it['fix']}")
    print("\n摘要:", obj.get("summary", ""))

    # --- 存档（纵向评估数据）---
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "ts": datetime.now().isoformat(),
        "task": Path(a.contract).stem,
        "verdict": verdict,
        "escalate": escalate,
        "fail_count": fail_count,
        "cond_count": cond_count,
        "total_items": len(items)
    }
    with open(REVIEW_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
