# 五类日报（投资视角）与 fetch_summaries 强化 — 2026-08-07

## 背景
用户定版：5 类新闻（美股/黄金/中国科技/AI半导体/宏观）**与跨境分开推送**。
- 跨境日报：16:00，小白教学风格分析（见 ai-analysis-modular-v2.md）
- **五类日报：9:30（一天一次），去重后全推，投资视角分析（非教学）**

## 用户决策要点
- 时间选 9:30（A股开盘前）：美股隔夜行情/黄金最新价对**纳指定投（工作日）+ 黄金积存**有实操价值
- 内容：去重后全推（与跨境一致，不精选）——24h 窗口实测 614 原始 → 白名单 86 → 去重 62 条
- 分析：投资视角——读者是投资者不是小白；**不教学、不喊单、不给买卖建议**（只讲"对定投/积存的含义"，不喊加仓减仓）

## 管线改动（prepare_candidates.py v3）
- `--hot-only`：固定 24h 窗口 + **只走热榜白名单通道**（rss/cb 垂直源跳过——防止跨境内容混入 5 类推送）；与 `--crossborder-only` 互斥
- `--pushed-file <路径>`：指定独立防重复清单。跨境=`pushed_titles.json`，5类=`pushed_five.json`——**必须隔离，否则两套推送互相排除**
- get_window：cb/hot 两种模式共用"过去 24h"逻辑

## 五类日报 cron（TrendRadar五类日报，30 9 * * *）
流程同跨境：prepare_candidates --hot-only --pushed-file pushed_five.json → fetch_summaries --input（补摘要）→ LLM 去重全推 + 投资视角分析 → 更新 pushed_five.json（title+norm+url）→ 回复日报

## 投资视角分析格式（cron prompt 第 3 步）
```
⚡ 今日速览 —— 3 条一句话 ≤35 字
🇺🇸 美股与纳指 —— 隔夜行情/科技股动向/对纳指定投的提示
🥇 黄金 —— 金价动向/驱动因素/对积存金的提示
🇨🇳 中国科技 —— 大厂动态/新规
🤖 AI半导体 —— 芯片/AI 产业动态
🌐 宏观与政策 —— 数据/利率/关税信号
📌 对投资的提示 —— 2-3 条"对定投/积存的含义"（该观望/无影响），基于事实，不喊买卖
```
每条三行卡：`▶ 标题` / `　干货：数字原样` / `　影响：对投资的含义`。全文 700-1000 字，单模块 ≤200，单条 ≤100，单行 ≤40。禁"值得关注/持续观察/建议跟进/综上所述"。

## fetch_summaries.py 强化（通用正文提取，两类日报共用）
- **泛化**：`--input`（默认 cb_candidates.json）/ `--output`（默认覆盖 input）；兼容 `{"items":[...]}` 与 `{"candidates":[...]}` 两种结构
- 🔴 **编码修复**：中文站 GBK/GB2312，requests 默认可能误判 → `resp.encoding` 为 None/iso-8859-1/ascii/utf-8 时，先用 `requests.utils.get_encoding_from_headers`，否则 `apparent_encoding`
- 🔴 **反爬/垃圾页检测（extract_text 必须全部覆盖）**：
  - Google 桥接页：`WIZ_global_data` / `window.WIZ`
  - JS/SPA：`$jsvmprt` / `window.` / `var glb`
  - 百度安全验证页：`百度安全验证` / `网络不给力`
  - 超短文本：`len(text) < 20` → 拒收（防导航碎片）
- **article 优先**：HTMLParser 收集 `<article>` 内 `<p>` 文本；无 article 或 article 空则回退全部 p——有效剔除导航噪音（凤凰网等）
- 🔴 **热榜源正文抓取现实**：百度热搜/微博/抖音/头条反爬强或 SPA，62 条候选仅 ~10-15 条能抓到正文摘要。**可接受**——热榜标题本身是中文且信息密度高（自带数字，如"宇树科技发行价150.8元/股"），无摘要条目标题+链接即可，不像英文源必须补翻译

## 验证
verify_crossborder_pipeline.py 已扩展至 26 项（+hot-only 模式 5 项、pushed_five 4 项、extract_text 垃圾/反爬/超短/article 优先 6 项）。🔴 历史断言样本若 <20 字符会被新"超短拒收"规则挡掉（FAIL 是断言问题非代码 bug），样本需加长到 >20 字符。
