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

### L3 compaction 摘要注入用户消息
- **来源**: 2026-07-03 compaction 消息注入 bug 修复
- **规则**: 压缩摘要角色交替死锁时，不能把摘要合并到用户当前消息。应 prepend 到 head 末尾的 assistant 消息。注意两种死锁场景都需覆盖（head=assistant+tail=user 和 head=user+tail=assistant）
- **复现**: 1次（用户查进度，Agent 却启动下午的小红书分析任务）
- **状态**: active



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

### L5 L1审查对齐——交付物分类必须与契约严格一致
- **来源**: 2026-07-04 Skill 微信→Telegram 迁移
- **规则**: 交付物中 D1/D2/D3 的分类数量必须与契约完全对应。甲类(8)+丙类(1)不能混成"9个skill"；额外展示的证据（如未改动的cron job）必须显式标注"未改动"
- **复现**: 1次（L1 第2轮 FAIL — 数量不符 + 越界）
- **状态**: active

### L6 新增数值参数必须附推导依据
- **来源**: 2026-07-04 Skill 微信→Telegram 迁移
- **规则**: 在任何交付物中新增数值阈值/参数（如分段字数上限），必须附第一性原理推导（API上限→扣除格式化开销→净空间）和可靠来源（官方API文档）
- **复现**: 1次（L1 第1轮 CONDITIONAL — 3500字阈值缺少推导）
- **状态**: active

### L7 契约验收标准应写精确动作
- **来源**: 2026-07-04 文件治理规范
- **规则**: 写契约验收标准时，用精确动作而非抽象描述。如"step 6 执行 `rm -f workflow_*.md`"优于"创建前清孤儿";"hermes cron list 输出显示 deliver=origin"优于"已改为origin"。L1 审查只能验证可执行的事实，不能推断意图。
- **复现**: 1次（L1 FAIL — 清理孤儿动作不在指定 step）
- **状态**: active
