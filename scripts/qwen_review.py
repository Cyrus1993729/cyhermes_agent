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
审查六维度，每条结论单独裁决，禁止打包：

1. 任务完成度：契约里每个交付项/验收标准是否达成。
2. 论证质量：把关键论断按【事实 / 推理 / 判断】三分类，检查——
   - 事实：有无权威来源？有无编造数据/引用？
   - 推理：是否从第一性原理推导？有无预设立场？
   - 判断：边界条件是否成立？
3. 数据逻辑（必须逐项核验，不得跳过）：
   a) 符号方向：偏差/变化的±号是否与比较关系一致（A<B→差为负；A>B→差为正）。但凡出现百分比数值，倒推原始值验算符号。
   b) 跨小节勾稽：同一组数据在报告不同小节出现时，数值和单位是否一致。
   c) 口径一致性：同一概念在全文中是否使用统一术语。
   d) 基本算术：涉及四则运算的数据点，用近似心算验证数量级是否合理。
4. 风险合规：越界、遗漏边界条件、凭证/安全红线。
5. 深度体检（存在性检查——只查"有没有"，不判"对不对"。输出疑点标记而非深度通过/不通过）：
   a) 证据链：关键结论是否有具体证据支撑？还是空泛断言？
   c) 反方视角：是否至少提及了替代解释或反方观点？
   d) 盲区标注：是否主动标出了不确定性、数据局限、未覆盖范围？
   e) 承重假设：整个结论压在哪一条假设上？这条假设被说清楚了吗？
   f) 问题替代：交付物有没有把真正的问题偷换成一个更好答的邻近问题？
   ⚠️ 注意："逻辑跳跃"（推理链条有无断层）不属于 L1 范围——L1 只标记"疑似逻辑跳跃"疑点。
6. 执行策略契合度（作为前置条件，不是独立维度）：
   先读契约「执行策略」字段——
   - 选单模型：检查交付物是否有拼接痕迹、前后矛盾、论证断裂
   - 选 Kanban：检查子任务衔接处有无信息丢失、handoff 损耗、口径不一致

对每条给：结论(PASS/CONDITIONAL/FAIL) + 依据 + 修复建议。
dim5 的子项若存在不足，判 CONDITIONAL 并给出疑点描述（而非 FAIL）。
最后给总裁决：全 PASS→PASS；有 CONDITIONAL 无 FAIL→CONDITIONAL；任一 FAIL→FAIL。
CONDITIONAL≥3 条或任一 FAIL → 建议升级 Opus（人工手动）。

严格输出 JSON:
{"verdict":"...","escalate":bool,
 "items":[{"claim":"","type":"完成度|事实|推理|判断|数据逻辑|合规|深度体检|执行策略","result":"PASS|CONDITIONAL|FAIL","reason":"","fix":""}],
 "suspicions":[{"flag":"","sub_type":"证据链|反方视角|盲区标注|承重假设|问题替代|逻辑跳跃|接缝|一致性","detail":""}],
 "summary":""}

suspicions 数组独立于 items——dim5 子项即使判了 CONDITIONAL/PASS，仍可同时输出疑点标记让 L2 确认。suspicions 和 items 互不影响。没有疑点时可为空数组。"""


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
        with urllib.request.urlopen(req, timeout=300) as resp:
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
    suspicions = obj.get("suspicions", [])
    if suspicions:
        print("\n--- 疑点标记（建议 L2 确认）---")
        for s in suspicions:
            print(f"  ⚠ [{s.get('sub_type','?')}] {s.get('flag','')}")
            if s.get('detail'):
                print(f"     详情: {s['detail']}")
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
