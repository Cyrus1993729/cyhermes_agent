#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre_review_check.py — ③.5 自检闸门
在审查之前强制检查交付物质量。脚本化闸门（exit≠0 阻断），不靠 Agent 自觉。

用法:
  python pre_review_check.py --contract contract.md --deliverable report.md

退出码:
  0 = 全部通过
  1 = 闸门失败（有阻断项，不可进入审查）
  3 = 契约/交付物文件缺失或格式错误
"""
import re, sys, argparse
from pathlib import Path

BLOCK = "🔴 阻断"
WARN = "🟡 告警"
PASS = "🟢 通过"

# ── 从契约提取 D4 预期阈值 ──
def _parse_d4_threshold(contract_text):
    """从契约 D4 判定阈值表提取 key → pattern。"""
    thresholds = {}
    table = re.search(r'D4 判定阈值.*?\n\n', contract_text, re.DOTALL)
    if not table:
        return thresholds
    for line in table.group(0).split('\n'):
        m = re.match(r'\|\s*(D4\.\d)\s*\|.*?([±]?\s*\d+[\.,]?\d*\s*%)', line)
        if m:
            thresholds[m.group(1)] = m.group(2).replace(' ', '').replace(',', '.')
    return thresholds

# ── 从交付物提取七因子表（锚定到 D2 区块） ──
def _parse_factor_table(deliverable_text):
    """在 D2 区块内匹配七因子评分表，返回 [(name, weight_pct, score), ...]"""
    sec = re.search(r'## 📊 D2.*?(?=## |\Z)', deliverable_text, re.DOTALL)
    if not sec:
        return None
    dims = re.findall(
        r'\|\s*(.+?)\s*\|\s*(\d+)%\s*\|\s*\*{0,2}([+-]?\d+\.\d+)\*{0,2}',
        sec.group(0)
    )
    return dims if dims else None

# ── 提取 composite 值 ──
def _parse_composite(deliverable_text):
    # 格式: code block 内 "加权 composite = (...)" 后跟 "= -0.540"
    # 策略: 找 composite 声明行，再在后续 5 行内找独立的 "= X.XXX"
    m = re.search(r'加权\s+composite\s*=', deliverable_text)
    if m:
        after = deliverable_text[m.end():m.end()+500]
        val = re.search(r'=\s*([+-]?\d+\.\d{2,3})\s*$', after, re.MULTILINE)
        if val:
            return float(val.group(1))
    # fallback: 直接搜 "composite = N.NNN"
    m2 = re.search(r'composite\s*=\s*([+-]?\d+\.\d+)', deliverable_text)
    return float(m2.group(1)) if m2 else None

# ── 提取综合评分 ──
def _parse_score(deliverable_text):
    m = re.search(r'综合评分.*?=\s*([\d.]+)', deliverable_text)
    return float(m.group(1)) if m else None

# ── 金价振幅 ──
def _parse_amplitude(deliverable_text):
    m = re.search(r'\$([\d,]+)\s*[-–]\s*\$([\d,]+)', deliverable_text)
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    return None, None

# ── 金价 ──
def _parse_gold_price(deliverable_text):
    m = re.search(r'COMEX GC=F.*?\$([\d,]+\.[\d]{2})', deliverable_text)
    if not m:
        m = re.search(r'\$([\d,]+\.[\d]{2})', deliverable_text)
    return float(m.group(1).replace(",", "")) if m else None


def check_deliverable(contract_path, deliverable_path):
    contract = Path(contract_path).read_text(encoding="utf-8", errors="replace")
    deliverable = Path(deliverable_path).read_text(encoding="utf-8", errors="replace")
    
    results = []
    blocked = False
    
    # ── 1. composite 加权重算（锚定 D2 区块） ──
    dims = _parse_factor_table(deliverable)
    if dims:
        composite = 0.0
        for name, weight_str, score_str in dims:
            composite += float(weight_str) / 100 * float(score_str)
        composite = round(composite, 3)
        expected_score = round((composite + 2) / 4 * 100, 1)
        
        claimed_comp = _parse_composite(deliverable)
        claimed_score = _parse_score(deliverable)
        
        if claimed_comp is not None:
            if abs(composite - claimed_comp) > 0.01:
                results.append((BLOCK, f"composite 计算不一致: 脚本={composite}, 交付物={claimed_comp}"))
                blocked = True
            else:
                results.append((PASS, f"composite 验算通过: {composite}"))
        else:
            results.append((WARN, "未找到 composite 声明行"))
        
        if claimed_score is not None:
            if abs(expected_score - claimed_score) > 0.5:
                results.append((BLOCK, f"综合评分不一致: 计算={expected_score}, 交付物={claimed_score}"))
                blocked = True
            else:
                results.append((PASS, f"综合评分验算通过: {expected_score}"))
    else:
        results.append((WARN, "未在 D2 区块找到七因子评分表"))
    
    # ── 2. 定投映射 ──
    # 从契约提取映射规则
    map_text = ""
    m = re.search(r'定投映射[：:].*?(?:\n|$)', contract)
    if m:
        map_text = m.group(0)
    # 默认规则
    thresholds_def = [(40, "暂停"), (50, "30%"), (60, "50%"), (70, "75%"), (float("inf"), "正常")]
    score_val = _parse_score(deliverable)
    if score_val is not None:
        expected_action = None
        for limit, action in thresholds_def:
            if score_val < limit:
                expected_action = action
                break
        if expected_action:
            if expected_action == "暂停":
                # 锚定到定投建议区块，非全文搜索
                advice_sec = re.search(r'(?:定投建议|💰)', deliverable)
                if advice_sec:
                    advice_text = deliverable[advice_sec.start():advice_sec.start()+500]
                else:
                    advice_text = deliverable
                if '暂停' not in advice_text:
                    results.append((BLOCK, f"定投映射: 评分{score_val}<40，契约要求'暂停'，定投建议行未找到"))
                    blocked = True
                else:
                    results.append((PASS, f"定投映射: {score_val}<40 → 暂停 ✓"))
            else:
                # 非暂停档: 容忍整数和 N/100 格式
                pct_int = int(expected_action.replace("%", ""))
                # 匹配 "XX% 定投" / "定投 XX%" / "XX/100" 等变体
                found = False
                for variant in [f"{pct_int}%", f"{pct_int}/100", str(pct_int)]:
                    if variant in deliverable:
                        found = True
                        break
                if not found:
                    results.append((BLOCK, f"定投映射: 评分{score_val}应在{expected_action}档，交付物中未找到"))
                    blocked = True
                else:
                    results.append((PASS, f"定投映射: {score_val} → {expected_action} ✓"))
    contract_thresholds = _parse_d4_threshold(contract)
    # 从交付物 D4 表提取实际阈值
    d4_sec = re.search(r'## 🔬 D4.*?(?=## |\Z)', deliverable, re.DOTALL)
    if d4_sec:
        d4_text = d4_sec.group(0)
        for key, expected in contract_thresholds.items():
            # D4 表格式: | 子项 | 内容 | 结果 | 判定 |
            # 跳过前3列，在判定列（第4列）提取阈值
            # 判定列格式: "✅ ≤±0.8%" / "⚠️ ≤±10%，未超阈值" / "✅ ≤±1%"
            row_pat = re.compile(
                r'\|\s*' + re.escape(key) + r'\s*\|'
                r'(?:[^|]*\|){2}'          # 跳过 内容、结果 两列
                r'[^|]*?(?:≤\s*)?([±]\s*\d+[\.,]?\d*\s*%)'  # 判定列阈值(≤可选)
            )
            m = row_pat.search(d4_text)
            if m:
                actual = m.group(1).replace(' ', '').replace(',', '.')
                # 标准化比较: 去掉 ±/≤ 前缀只比数字
                actual_clean = actual.lstrip('±≤')
                expected_clean = expected.lstrip('±≤')
                if actual_clean != expected_clean:
                    results.append((BLOCK, f"{key} 阈值不一致: 契约={expected}, 交付物={actual}"))
                    blocked = True
                else:
                    results.append((PASS, f"{key} 阈值一致: {expected}"))
    
    # ── 4. 术语一致性（告警，不阻断） ──
    terms_found = []
    for term in ['境内外价差', '公允价值偏离', '上海金折价', '折价']:
        count = deliverable.count(term)
        if count > 0:
            terms_found.append(f"{term}({count}次)")
    if terms_found:
        results.append((PASS, f"术语使用: {', '.join(terms_found)}"))
    # 检测"上海金折价"和"公允价值偏离"同时出现
    if '上海金折价' in deliverable and '公允价值偏离' in deliverable:
        results.append((WARN, "⚠ '上海金折价'和'公允价值偏离'同时出现——两者不应混用"))
    
    # ── 5. 新闻振幅 vs 当前价 ──
    lo, hi = _parse_amplitude(deliverable)
    price = _parse_gold_price(deliverable)
    if lo and hi and price:
        if price < lo or price > hi:
            results.append((BLOCK, f"新闻振幅 ${lo:,.0f}-${hi:,.0f} 与 COMEX 价 ${price:,.2f} 矛盾（超出振幅）"))
            blocked = True
        else:
            results.append((PASS, f"价格自洽: ${price:,.2f} 在振幅 ${lo:,.0f}-${hi:,.0f} 内"))
    
    # ── 汇总 ──
    print(f"\n{'='*50}")
    print(f"  ③.5 自检闸门")
    print(f"{'='*50}")
    for status, msg in results:
        print(f"  {status}: {msg}")
    
    if blocked:
        print(f"\n🔴 闸门未过 — 请修复上述阻断项后重新运行。")
    else:
        print(f"\n🟢 闸门通过 — 可进入审查。")
    
    return blocked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--deliverable", required=True)
    a = ap.parse_args()
    
    if not Path(a.contract).exists():
        print(f"[ERROR] 契约文件不存在: {a.contract}", file=sys.stderr)
        sys.exit(3)
    if not Path(a.deliverable).exists():
        print(f"[ERROR] 交付物文件不存在: {a.deliverable}", file=sys.stderr)
        sys.exit(3)
    
    blocked = check_deliverable(a.contract, a.deliverable)
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
