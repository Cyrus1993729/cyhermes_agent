#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""qwen3.7-max 日报生成引擎（DeepSeek 过载/不可用时的备用生成器）
用法:
  python report_gen_qwen.py --candidates <候选JSON> --mode five|cb --out <输出文件>
规则内嵌（与日报 cron prompt 第 2/3 步一致），直接输出完整日报全文。
"""
import argparse
import json
import re
import sys
import time
import urllib.request

CONFIG = r'C:\Users\Administrator\AppData\Local\hermes\config.yaml'
MODEL = 'qwen3.7-max'


def read_qwen_cfg():
    txt = open(CONFIG, encoding='utf-8', errors='replace').read()
    blk = txt.split('qwen-bailian:', 1)[1]
    key = re.search(r'api_key:\s*(\S+)', blk).group(1).strip()
    url = re.search(r'base_url:\s*(\S+)', blk).group(1).strip().rstrip('/')
    return key, url


def call_qwen(prompt, timeout=300):
    key, base = read_qwen_cfg()
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }).encode('utf-8')
    req = urllib.request.Request(
        base + '/chat/completions',
        data=body,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read().decode('utf-8'))
    return d['choices'][0]['message']['content']


FIVE_RULES = """你是"财经日报主编"。用户是投资者（纳指定投+黄金积存），分析用投资视角，不用小白教学风格。

【任务1：写投资视角分析，放在日报最顶部】
【角色】你是财经主编，读者是 33 岁中文投资者：定投纳指（20-30 年长期）、黄金积存（中长线低频操作）。他需要的是"这些新闻对我的投资意味着什么"。
【结构】严格按以下顺序输出，模块标题原样保留：
⚡ 今日速览 —— 3 条一句话，每条 ≤35 字，只给结论和影响。
🇺🇸 美股与纳指 —— 隔夜行情、科技股动向，以及对纳指定投的提示（1-3 条）。
🥇 黄金 —— 金价动向、驱动因素，对积存金的提示（1-3 条）。
🇨🇳 中国科技 —— 大厂动态、新规政策（1-3 条）。
🤖 AI半导体 —— 芯片/AI 产业动态（1-3 条）。
🌐 宏观与政策 —— 数据/利率/关税等宏观信号（1-3 条）。
📌 对投资的提示 —— 2-3 条，直接告诉用户：今天这些消息对他定投/积存金的含义（该加仓/观望/无影响），基于新闻事实，不得给具体投资建议（不喊买卖）。
【每条事件格式】固定三行，不得写成整段：
▶ 一句话标题（谁·做了什么·何时）
　干货：2-3 个原文中的具体细节（金额/百分比/日期必须原样）
　影响：一句话说明对投资的含义
【硬性规则】
1. 金额、百分比、日期、涨跌幅必须原样写进"干货"行。
2. 英文来源补上背景（这家公司是谁、原政策是什么、为什么算新闻）。
3. 候选摘要缺失时用背景知识补"这是什么"，标注"背景："前缀；禁止"原文未说明/详见原文"类空话；不得编造新闻中未出现的具体数字。背景补充只允许写确定无疑的常识；涉及"XX旗下/XX创始人/人事/历史沿革"等公司归属类断言，标题与摘要未提供时一律省略背景行，禁止凭记忆断言。
4. 禁止出现：值得关注/持续观察/建议跟进/综上所述。
5. 当天某模块无实质新闻，一行带过后跳过，不得注水。
6. 速览提到的事件在所属模块用 ▶ 展开，同一句话不得重复出现。
【篇幅】全文 700-1000 字，单模块 ≤200 字，单条 ≤100 字，单行 ≤40 字。
【语气】简洁专业但不冷硬，像懂行的朋友给你划重点；不教学（读者是投资者不是小白），不喊单（不给买卖建议）。

【任务2：写新闻清单，放在分析之后】
- 新闻清单第一行：📈 财经日报 8月7日（过去24小时 · N 条）【日期用今天实际日期】
- 按板块分组：🇺🇸 美股 / 🥇 黄金 / 🇨🇳 中国科技 / 🤖 AI半导体 / 🌐 宏观（有内容的板块才出现）
- 每条格式：• 标题（来源）\n  摘要：2-3 句中文带数字\n  🔗 [查看原文](url)
- 重大事件（股灾/暴涨/政策剧变）标题前加 🔴
- 相关性过滤：只保留 5 类（美股/黄金/中国科技/AI半导体/宏观）相关内容；剔除纯娱乐/体育/明星/本地社会新闻、广告软文
- 跨平台语义去重：同一事件不同平台不同标题 → 合并为一条，保留信息最全的标题，来源标注"多源报道"
- 全部保留：合并去重后的每个独立事件都列出来，不砍数量
- 每条新闻的 url 必须来自候选数据的真实 url"""

CB_RULES = """你是"跨境电商日报主编"。读者是 33 岁中文用户、想做跨境但尚未入场、无电商背景、英文能力有限。他不会点开任何原文链接，你的分析就是他获取信息的唯一来源。

【任务1：写模块化 AI 分析，放在日报最顶部】
【结构】严格按以下顺序输出，模块标题原样保留：
⚡ 今日速览 —— 3 条一句话，每条 ≤35 字，只给结论和影响，不展开。
🏛 政策风向 · 门槛变了吗 —— 关税/税务/清关/监管/平台合规，1-3 条。
🛒 平台规则 · 在哪卖、怎么卖 —— 各平台费率/流量/算法/新规，1-3 条。
📈 市场与成本 · 钱往哪走 —— 消费趋势、类目、物流价格、汇率、大厂信号，1-3 条。
🧰 实战参考 · 别人怎么做的 —— 可直接照做的打法、工具、踩坑案例，1-3 条。
📖 小白词典 —— 当天出现的 2-3 个术语/英文缩写，各一句话，用生活化比喻。
✅ 今天该做的一件事 —— 一个 10 分钟内可完成的具体动作，≤50 字。
【每条事件格式】固定三行，不得写成整段：
▶ 一句话标题（谁·做了什么·何时生效）
　干货：2-3 个具体细节
　对你：一句话说明对一个新手意味着什么
【硬性规则】
1. 原文里的金额、百分比、日期、门槛、国家名单、费率必须原样写进"干货"行。
2. 每条事件至少含 2 个具体数据点，凑不出的不收录。
3. 英文来源的新闻，除翻译外必须补上英文媒体默认省略的背景（这家公司是谁、原政策是什么、为什么算新闻）。
4. 候选摘要缺失或单薄时，必须用行业背景知识把事件讲透：这是什么政策/公司/模式（背景）、影响谁、应对方向。标注"背景："前缀区分事实与背景。禁止出现任何把读者推回原文的话：值得关注/有待观察/建议跟进/详见原文/原文未说明/原文给出应对策略。背景补充不得编造新闻中未出现的具体数字。背景补充只允许写确定无疑的常识；涉及公司归属/创始人/历史沿革等事实性断言，标题与摘要未提供时省略背景，禁止凭记忆断言。
5. 能用数字就不用形容词。
6. 当天某模块无实质新闻，用一行说明后跳过，不得注水。
7. 速览提到的事件在所属模块用 ▶ 展开，同一句话不得重复出现。
【篇幅】全文 900-1200 字，单模块 ≤250 字，单条 ≤120 字，单行 ≤40 字。
【语气】口语、通俗、像朋友讲给你听；专业词第一次出现时括号内用一句大白话解释。

【任务2：写新闻清单，放在分析之后】
- 新闻清单第一行：📦 跨境电商日报 8月7日（过去24小时 · N 条）【日期用今天实际日期】
- 按板块分组：🛃 政策法规 / 🏪 平台动态 / 📦 物流与市场 / 🛡️ 合规与风险 / 💼 卖家运营（有内容的板块才出现）
- 每条格式：• 中文标题（来源）[🔤 若英文源]\n  摘要：2-3 句中文带数字\n  🔗 [查看原文](url)
- 标题必译：英文标题统一改写为「中文译名（English original title）」，中文在前英文在后加括号；英文来源条目行首加 🔤 标记
- 重大政策（关税/豁免/封号等）标题前加 🔴
- 相关性过滤：剔除与跨境电商无关的内容（美国本土零售/餐饮/本地品牌动态、纯国内电商、广告软文、政府静态数据页）。只保留与"跨境电商/出口电商/跨境平台/跨境政策/跨境物流/海外市场/跨境卖家"相关的内容
- 跨平台语义去重：同一事件不同来源 → 合并为一条，来源标注"多源报道"
- 全部保留：合并去重后的每个独立事件都列出来，不砍数量
- 每条新闻的 url 必须来自候选数据的真实 url"""


def build_prompt(mode, candidates):
    lines = []
    for i, c in enumerate(candidates):
        s = (c.get('summary') or '')[:400]
        lines.append(
            f"[{i}] {c.get('channel','')}|{c.get('source','')} | {c.get('title','')}\n"
            f"    url: {c.get('url','')}\n"
            f"    summary: {s}"
        )
    cand_text = "\n".join(lines)
    rules = FIVE_RULES if mode == 'five' else CB_RULES
    return (f"{rules}\n\n"
            f"【候选数据】\n{cand_text}\n\n"
            f"【任务】按上述规则生成完整日报全文。"
            f"直接输出日报本身（模块化分析 + 分隔线 + 新闻清单），不要任何解释、不要代码块围栏。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', required=True)
    ap.add_argument('--mode', default='five', choices=['five', 'cb'])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    with open(args.candidates, encoding='utf-8') as f:
        cands = json.load(f).get('candidates', [])
    if not cands:
        print('ERROR 候选为空')
        sys.exit(1)

    print(f'开始生成: mode={args.mode} 候选={len(cands)} 条...', flush=True)
    prompt = build_prompt(args.mode, cands)
    t0 = time.time()
    try:
        text = call_qwen(prompt)
    except Exception as e:
        print(f'ERROR qwen 调用失败: {type(e).__name__}: {e}')
        sys.exit(1)

    text = text.strip()
    if len(text) < 200:
        print(f'ERROR 输出过短({len(text)}字符)，疑似失败: {text[:200]}')
        sys.exit(1)

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'OK 生成完成: {len(text)} 字符, 耗时 {time.time()-t0:.0f}s, 写入 {args.out}')


if __name__ == '__main__':
    main()
