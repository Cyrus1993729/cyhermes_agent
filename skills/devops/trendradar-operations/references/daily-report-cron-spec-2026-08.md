# 双日报 cron 规范（2026-08-07 定稿）— 修改日报格式时以此为准

两个 cron 的 prompt 是"日报格式规范"的唯一真相源（cronjob update 传完整 prompt）。
本文件是精炼版规范；改格式时 cronjob update 后**必须同步更新本文件**。

## 跨境日报（f4506e87cc69，`0 16 * * *`，deliver=origin，toolsets=[terminal,file]）

流程 6 步：
1. **取候选**：`cd /d/Workspace/Projects/TrendRadar && unset PYTHONPATH VIRTUAL_ENV && uv run python fetch_summaries.py`（补摘要 1-2min）→ `uv run python prepare_candidates.py --crossborder-only`（stdout JSON：stats+candidates[]，每项 title/channel/source/url/rank/first_time/summary；after_pushed 已排除已推送 URL）
2. **1.5 读已推送**：`pushed_titles.json`，与已推送标题相同/高度相似的同一事件跳过不推
3. **编辑清单**：a 相关性过滤（剔除美国本土零售/餐饮、纯国内电商、广告软文"XX特训营优秀学员"、政府静态数据页）b 跨平台语义去重（多源→合并，"多源报道"）c **标题必译**「中文译名（English original title）」+🔤 d **摘要 2-3 句带数字**，summary 空时补一句背景 e 全推不砍量
4. **模块化 AI 分析**（Opus 设计，放最顶）：
   - 结构：⚡今日速览（3 条≤35 字）→ 🏛政策风向·门槛变了吗 → 🛒平台规则·在哪卖怎么卖 → 📈市场与成本·钱往哪走 → 🧰实战参考·别人怎么做的 → 📖小白词典（2-3 术语+生活化比喻）→ ✅今天该做的一件事（≤50 字）
   - 每条事件固定三行：`▶ 一句话标题 / 干货：2-3 个具体细节 / 对你：一句话`
   - 硬规则：金额/百分比/日期/门槛原样写进干货行；每条≥2 数据点凑不出不收录；英文源补背景（公司是谁/原政策/为何算新闻）；**摘要缺失用背景知识补（"背景："前缀），禁止"原文未说明/详见原文/值得关注/有待观察/建议跟进"**；不编造新闻中没有的具体数字；空模块一行带过不注水；速览与模块内容不重复
   - 篇幅 900-1200 字，单模块≤250，单条≤120，单行≤40
5. **清单分组**：🛃政策法规 / 🏪平台动态 / 📦物流与市场 / 🛡️合规与风险 / 💼卖家运营；重大政策加🔴；>4096 字符拆条标（1/N）
6. **5 硬性：更新 pushed_titles.json**（title+norm+url+pushed_at，norm=小写去空格标点去修饰词，按 norm 去重）
7. **5.5 硬性：存档知识库**：write_file `archives/crossborder/YYYY-MM-DD.md`（完整日报）+ `YYYY-MM-DD.json`（{date,pushed_at,mode,news_count,analysis,news:[{section,title,source,url,summary}]}）+ 更新 `index.json` archives 数组（同日不重复）
8. 最终回复=完整日报（自动推送 TG）；候选空→"📦 今日跨境无新动态"

## 5 类日报（970113abe8a7，`30 9 * * *`）

与跨境同构，差异点：
- 取候选：`prepare_candidates.py --hot-only --pushed-file pushed_five.json > output/candidates_five.json` → `fetch_summaries.py --input output/candidates_five.json`；读 pushed_five.json
- 分析为**投资视角**（读者=纳指定投+黄金积存投资者）：⚡今日速览 → 🇺🇸美股与纳指 → 🥇黄金 → 🇨🇳中国科技 → 🤖AI半导体 → 🌐宏观与政策 → 📌对投资的提示（2-3 条：定投/积存含义，**不喊单不给买卖建议**）
- 篇幅 700-1000 字，单模块≤200，单条≤100
- 清单板块：🇺🇸美股 / 🥇黄金 / 🇨🇳中国科技 / 🤖AI半导体 / 🌐宏观
- 存档：目前**未要求**（用户只说跨境日报存档）；如要加，镜像 `archives/five/` 结构
- 空候选→"📈 今日财经无新动态"

## 修改日报格式的流程
1. 用户提需求 → 需要格式级设计时先发 Opus 出设计稿（prompt 含用户原话+现有结构+画像）
2. 用户确认 → `cronjob update` 传完整新 prompt
3. 手动模拟跑一次完整流程给用户看效果（备份→清空 pushed→跑→恢复 pushed，避免 16:00 重复推）
4. 更新本 reference + verify_crossborder_pipeline.py（如涉及脚本行为）
