# 经验教训库 — Lessons Learned

> 从每次复盘和审查中提炼的可复用规则。sprint-contract 自动加载。
> 格式：每条 = 来源(日期+任务) + 规则 + 证据(复现次数)

---

## 内容分析类

### L1 必须标注来源性质
- **来源**: 2026-07-02 小红书3-Agent帖子分析审查
- **规则**: 所有内容分析产出必须标注每条结论的来源性质——是【事实】/【推断】/【猜测】
- **复现**: 1次（L1审查 FAIL — 全文未标注）
- **状态**: active

---

## 投资分析类



---

## 系统操作类



---

## 通用方法论

### L2 skill 优先路由——收到链接先查 skill
- **来源**: 2026-07-02 小红书备份教程分析复盘
- **规则**: 收到带链接(含 xhslink.com/xiaohongshu.com/bilibili.com/youtube.com)且含分析/理解意图的消息时，第一步必须检索是否有匹配的专用 skill，有则直接走 skill 流水线，禁止先用通用工具试探
- **复现**: 1次（Agent 先用了 browser_navigate + curl 多轮试探，用户提醒才走 skill）
- **触发词**: xhslink.com, xiaohongshu.com, bilibili.com, youtube.com, 小红书, B站
- **状态**: active


---

*规则状态: active = 生效中 | retired = 已被替代（手动标记）*
*最后更新: 2026-07-02*
