# 任务复盘：黄金周报
- 日期：2026-09-07
- 数据质量：
  - SGE：上海金数据 4 天前（2026-09-03，中秋假期无收盘），系统自动以 GC=F × 汇率外推 —— 正常路径，无需干预
  - FRED：DFII10 / M2SL / T10Y2Y 全部获取成功 ✓；宏观数据 13 天前、央行数据 30 天前（权重自动衰减至 80%/60%）
  - 金价校验：XAU 现货 $4,400.70 vs COMEX 期货 $4,476.60 → 期货溢价 +1.7%（contango 正常，≤2%）
  - 汇率校验：CNH 6.71 / CNY 6.72（差值 0.15%），换算偏差 -0.7%（≤3%）
- 踩过的坑：
  1. **运行环境丢失**：hermes venv 缺 pandas，main.py 无法运行 → 用 uv 新建 .venv + 安装 requirements.txt 解决（未改任何代码，符合铁律）
  2. **qwen_review.py 缺 x-opencode-session 头**：OpenCode 网关 400 MissingSessionID → 用临时封装脚本（Temp/l1_review_wrap.py）补 session 头绕过，正式脚本未改（改动脚本需用户确认）
  3. **L1 审查 3 轮 FAIL → 1 轮 CONDITIONAL → API 抖动**：L1 首轮抓出 2 FAIL（contango 口径、CNH/CNY 术语混用）+ 2 CONDITIONAL；第 2 轮抓 fiscal_gpr 文本矛盾 + MACD 表述 + 评分映射未披露；第 3 轮 contango 措辞 + USDCNY/USDCNH 口径豁免声明；修复后 L1 PASS（25/25），随后 2 次 API 抖动（timeout/500），最终 PASS
  4. **L2 GPT-5.6 Sol 确诊 3 疑点**：①fiscal_gpr 文本自相矛盾（走弱 vs 强势）→ 交付物声明忽略文字仅取评分 0；②MACD"金叉"表述不严谨（代码只查 last>signal 未查前一期，应为"位于信号线上方/多头排列"）；③**境内 ETF 流量信号口径错误**——main.py 输出"份额减少 33.9%/散户资金流出"，L2 核验底层实为 518880/159937 日成交量（Volume）变化，非份额非资金流，已修正研判引用并降权
  5. **公允价值口径**：综合研判引用 ¥965.9 需披露计算（XAU×CNY÷31.1035×1.0），已补说明
- 最终结果：L1 PASS（25/25）+ L2 修正 3 项，周报投递，contract+deliverable 归档
- 可优化点：
  - main.py 三处文本生成 bug 待用户确认后修复：①fiscal_gpr 信号文字方向错误 ②"金叉"判定需补前一期校验 ③境内 ETF 流量把成交量表述为份额（误导性最强，建议优先修）
  - qwen_review.py 应补 x-opencode-session 头（网关新要求），避免每次用临时封装

## 教训回流判断
- 一次性：本次 L1/Q 抖动、API 超时为偶发，不入 lessons
- **可复用规则（拟写入 lessons.md）**：L1 审查前确认 qwen_review.py 带 x-opencode-session 头（OpenCode 网关 2026-09 起要求），否则直跑必 400；封装脚本 Temp/l1_review_wrap.py 可复用
- 程序瑕疵类（fiscal_gpr/MACD/ETF 口径）：写入复盘即可，代码修改需用户确认后单独执行，符合"本任务禁止修改 gold_analyzer 代码"铁律