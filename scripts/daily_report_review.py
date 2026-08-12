#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_report_review.py — 日报投递前自动质检（L0 硬规则 + L1 双模型审查）

用法:
  python daily_report_review.py --draft <日报草稿文件> [--candidates <候选JSON>] [--mode five|cb] [--model gpt|qwen|both]

流程:
  L0 硬规则脚本（本地正则，零成本）→ L1 模型审查（默认 gpt=GPT-5.6 via Codex CLI；
  --model both 启用双模型 qwen3.7-max + GPT-5.6）→ 合并 findings

输出 JSON:
  {"l0": [{"rule","severity","location","issue"}...],
   "qwen": {"ok":bool, "findings":[...] 或 "error":...},
   "gpt":  {"ok":bool, "findings":[...] 或 "error":...},
   "findings": [合并去重后的 findings], "verdict": "FIX"|"PASS"}

退出码: 0=审查完成; 2=草稿缺失/不可读; 3=草稿为空
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

CONFIG = Path(r"C:\Users\Administrator\AppData\Local\hermes\config.yaml")
PROXY = "http://127.0.0.1:7897"

# ---------- L0 硬规则 ----------
BANNED_WORDS = ["值得关注", "持续观察", "建议跟进", "综上所述", "详见原文", "原文未说明"]
TICKING_WORDS = ["加仓", "减仓", "抄底", "梭哈", "清仓", "止盈", "止损"]
MODULES_FIVE = ["今日速览", "美股与纳指", "黄金", "中国科技", "AI半导体", "宏观与政策", "对投资的提示"]
MODULES_CB = ["今日速览", "政策风向", "平台规则", "市场与成本", "实战参考", "小白词典", "今天该做的一件事"]


def l0_check(text: str, mode: str) -> list:
    findings = []
    # 1. 禁止词
    for w in BANNED_WORDS:
        for m in re.finditer(re.escape(w), text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"rule": f"禁止词[{w}]", "severity": "hard",
                             "location": f"第{line}行", "issue": f"出现禁止词「{w}」"})
    # 2. 喊单词（标记，由模型判）
    for w in TICKING_WORDS:
        for m in re.finditer(re.escape(w), text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"rule": f"喊单词[{w}]", "severity": "soft",
                             "location": f"第{line}行", "issue": f"出现操作建议词「{w}」，需模型确认是否越界"})
    # 3. 背景行标记（全部列出，交 L1 判断置信度）
    for m in re.finditer(r"背景[：:](.{0,80})", text):
        line = text.count("\n", 0, m.start()) + 1
        findings.append({"rule": "背景行", "severity": "soft",
                         "location": f"第{line}行", "issue": f"背景行内容待核实: 「{m.group(1).strip()[:60]}」"})
    # 4. 新闻清单：每条应有链接和摘要
    link_ok = len(re.findall(r"\[查看原文\]\(http", text))
    if link_ok < 1:
        findings.append({"rule": "链接检查", "severity": "hard",
                         "location": "全文", "issue": "新闻清单没有任何链接，疑似缺链接"})
    # 5. 模块完整性
    mods = MODULES_CB if mode == "cb" else MODULES_FIVE
    missing = [m for m in mods if m not in text]
    if missing:
        findings.append({"rule": "模块完整性", "severity": "soft",
                         "location": "全文", "issue": f"缺少模块: {', '.join(missing)}"})
    # 去重（同规则同位置）
    seen = set()
    out = []
    for f in findings:
        k = (f["rule"], f["location"], f["issue"])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


# ---------- L1a qwen ----------
REVIEW_RUBRIC = """你是财经日报终审编辑。审查【日报全文】，找错不重写。
检查项（按优先级）：
1. 事实性（最高优先）：
   a. 公司/人物/机构归属错误（如"XX是YY旗下/YY团队"必须准确，不确定即标 hard）
   b. 数字/百分比/日期与候选数据是否一致（候选数据见【候选】段；候选缺失时评估合理性）
   c. "背景："行内容置信度——是否为公认常识？不确定 → hard，建议删除或标注"未核实"
   d. 明显编造：新闻中未出现的细节被写成事实 → hard
2. 合规性：喊单（加仓/减仓/买入/卖出/抄底等操作建议）→ hard；禁止词（值得关注/持续观察/建议跟进/综上所述/详见原文）→ hard；格式违规（新闻缺链接/缺摘要/模块缺失）→ hard
3. 相关性/去重：混入无关内容、同一事件重复推送 → soft
4. 投资视角：分析是否基于新闻事实、有无逻辑硬伤 → soft
每条 finding 输出 JSON 对象：
{"severity":"hard|soft","category":"事实性|合规性|相关性|投资视角","location":"模块名或引用原文片段","issue":"问题描述","fix":"建议处置：删除该条/删除背景行/改写/放行"}
只输出 JSON: {"findings":[...]}，无问题则 {"findings":[]}。"""


def read_qwen_cfg():
    txt = CONFIG.read_text(encoding="utf-8", errors="replace")
    blk = txt.split("qwen-bailian:", 1)[1]
    key = re.search(r"api_key:\s*(\S+)", blk).group(1).strip()
    url = re.search(r"base_url:\s*(\S+)", blk).group(1).strip().rstrip("/")
    return key, url


def call_qwen(draft: str, candidates: str):
    key, base = read_qwen_cfg()
    body = {
        "model": "qwen3.7-max",
        "messages": [
            {"role": "system", "content": REVIEW_RUBRIC},
            {"role": "user", "content": f"【日报全文】\n{draft}\n\n【候选】\n{candidates[:6000] if candidates else '（未提供）'}"}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = json.loads(resp.read())
    return raw["choices"][0]["message"]["content"]


# ---------- L1b GPT-5.6 (Codex CLI) ----------
def extract_json(text: str):
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    # 最后一个最长的 {…} 块
    candidates = []
    for mm in re.finditer(r"\{", text):
        depth = 0
        for i in range(mm.start(), min(len(text), mm.start() + 20000)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[mm.start():i + 1])
                    break
    parsed = []
    for c in candidates:
        try:
            parsed.append(json.loads(c))
        except Exception:
            continue
    if parsed:
        # 优先含 findings 键的外层块（嵌套时内层对象无 findings），其次取最长
        with_findings = [p for p in parsed if isinstance(p, dict) and "findings" in p]
        pool = with_findings or parsed
        return max(pool, key=lambda p: len(json.dumps(p, ensure_ascii=False)))
    raise ValueError("no JSON found in codex output")


def call_gpt(draft: str, candidates: str):
    prompt = f"""{REVIEW_RUBRIC}

【日报全文】
{draft}

【候选】
{candidates[:6000] if candidates else '（未提供）'}"""
    env = dict(os.environ)
    env["HTTP_PROXY"] = PROXY
    env["HTTPS_PROXY"] = PROXY
    # Windows: codex 是 bash 脚本 + codex.cmd 包装，经 cmd.exe /c 调用；prompt 走 stdin 避免命令行长度限制
    prompt_file = Path(os.environ.get("TEMP", "/tmp")) / "daily_report_review_prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    r = subprocess.run(
        ["cmd.exe", "/c", r"C:\Users\Administrator\.local\bin\codex.cmd",
         "exec", "--skip-git-repo-check", "--sandbox", "read-only"],
        stdin=open(prompt_file, encoding="utf-8"),
        capture_output=True, text=True, timeout=600, env=env,
        cwd=r"D:\Workspace\Projects\TrendRadar")
    prompt_file.unlink(missing_ok=True)
    out = (r.stdout or "") + (r.stderr or "")
    try:
        return extract_json(out)
    except Exception as e:
        raise RuntimeError(f"codex output parse failed: {e}\n--- output ---\n{out[-1500:]}")


# ---------- 合并 ----------
def merge(qwen_f, gpt_f):
    merged = []
    for f in (qwen_f or []) + (gpt_f or []):
        if not isinstance(f, dict):
            continue
        issue = str(f.get("issue", ""))[:40]
        key = issue
        if not any(existing.get("_k") == key for existing in merged):
            f["_k"] = key
            merged.append(f)
    for f in merged:
        f.pop("_k", None)
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--candidates", default="")
    ap.add_argument("--mode", default="five", choices=["five", "cb"])
    ap.add_argument("--model", default="gpt", choices=["gpt", "qwen", "both"],
                    help="L1 审查模型：gpt（默认，GPT-5.6 via Codex CLI）/ qwen / both")
    args = ap.parse_args()

    try:
        draft = Path(args.draft).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(json.dumps({"error": f"draft unreadable: {e}"}, ensure_ascii=False))
        sys.exit(2)
    if not draft.strip():
        print(json.dumps({"error": "draft empty"}, ensure_ascii=False))
        sys.exit(3)

    candidates = ""
    if args.candidates and Path(args.candidates).exists():
        try:
            cd = json.loads(Path(args.candidates).read_text(encoding="utf-8", errors="replace"))
            cands = cd.get("candidates", cd if isinstance(cd, list) else [])
            candidates = json.dumps(
                [{"title": c.get("title"), "summary": (c.get("summary") or "")[:200]}
                 for c in cands][:40], ensure_ascii=False)
        except Exception:
            candidates = ""

    l0 = l0_check(draft, args.mode)

    qwen_res = {"ok": False, "findings": [], "skipped": True}
    if args.model in ("qwen", "both"):
        qwen_res["skipped"] = False
        try:
            qwen_res = {"ok": True, "findings": json.loads(call_qwen(draft, candidates)).get("findings", [])}
        except Exception as e:
            qwen_res["error"] = str(e)[:300]

    gpt_res = {"ok": False, "findings": [], "skipped": True}
    if args.model in ("gpt", "both"):
        gpt_res["skipped"] = False
        try:
            gpt_res = {"ok": True, "findings": call_gpt(draft, candidates).get("findings", [])}
        except Exception as e:
            gpt_res["error"] = str(e)[:300]

    findings = merge(qwen_res.get("findings"), gpt_res.get("findings"))
    for f in l0:
        if not any(f["issue"] == x.get("issue") for x in findings):
            findings.append(f)
    hard = [f for f in findings if f.get("severity") == "hard"]
    verdict = "FIX" if hard else "PASS"

    print(json.dumps({
        "l0": l0,
        "qwen": {**{k: v for k, v in qwen_res.items() if k != "findings"},
                 "findings_count": len(qwen_res.get("findings", []))},
        "gpt": {**{k: v for k, v in gpt_res.items() if k != "findings"},
                "findings_count": len(gpt_res.get("findings", []))},
        "findings": findings, "verdict": verdict,
        "hard_count": len(hard)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
