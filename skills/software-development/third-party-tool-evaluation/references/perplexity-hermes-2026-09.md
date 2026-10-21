# 案例：Hermes + Perplexity 搜索后端评估（2026-09-11）

场景：小红书帖「Hermes接入Perplexity搜索」→ 用户问「对我们有没有意义 / API 要不要钱收多少」。

## 评估链路（可复用骨架）
1. **官方核实**：搜官方 X + 官方文档，区分真实更新与营销号/搬运号。本案例 Nous Research 官方 X 9/9 官宣 + Perplexity Developers 转发 + pplx.ai/hermes 落地页齐全 → 真事。
2. **本地兼容性**：`hermes --version` = v0.21.0 (8.31)；`hermes config get web` = tavily。官方要求 v0.21.1 (v2026.9.7)+ 才含 Perplexity provider（PR 102055）→ 本机暂不支持，需先升级。
3. **官方定价**：web_search 定位 → web_extract 官方定价页逐项核对：
   - Search API：$5.00 / 1,000 次，flat，无 token 费 ≈ $0.005/次（¥0.036）
   - 计费单位：每次成功 POST /search = 1 单；单请求内最多 5 条 query 也只算 1 单
   - **无免费额度**（Tavily 免费 1000 次/月）
   - 别混淆 Sonar 对话式 API（token $1–3/M in + 请求费 $5–14/千次 双计费）——Hermes 集成走 Search API，不涉及
   - web_extract 的「相关段落」同计费，但不保证完整页（官方明说可能省略细节）→ 研报/PDF 全文提取不适用
4. **月成本估算**：100–300 次/月 → $0.5–1.5（¥3.6–11）「不贵但非必需」。
5. **决策对齐用户策略**：现役 Tavily 免费且够用 → 维持不切换；Perplexity 留作备选（额度耗尽/质量瓶颈时）。用户既定策略：fallback/按量付费 = 最后手段，勿轻易触发。
6. **输出**：结论内联交付 + 存档 output/2026-09-11_Hermes接入Perplexity搜索_分析.md。

## 可复用结论句
- 「质量更好 ≠ 值得切换」：免费现役方案够用时，付费选项只进备选清单。
- 价格数字必须带来源与抓取日期，且正文注明「用前重新核实」（价格会变）。
