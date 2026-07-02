# 复盘：小红书链接分析未自动调用skill

## 事件还原

1. 用户发来 xhslink.com 链接："请你理解这个帖子，并分析对我们的帮助"
2. Agent 没有调用 xiaohongshu-analysis skill
3. Agent 尝试了：browser_navigate（2次失败）、curl 提取页面、execute_code 多轮抓取
4. 用户提醒："调用我们的小红书理解skill做啊？你怎么忘了？"
5. 之后才加载 skill 走正确流程

## 根因分析

**表面原因**：Agent 默认走通用 web 抓取路径，没有优先检查是否有匹配的 skill。

**深层原因**：xiaohongshu-analysis skill 的触发条件明确写在 SKILL.md 中——"用户消息中包含 xhslink.com 链接 或 xiaohongshu.com 链接，且表达了分析/理解的意图"——两个条件都满足。但 Agent 没有在收到消息的第一步就检索已有 skill，而是直接开始用通用工具试探。

**本质**：skill 匹配机制是 Hermes 自动做的（系统加载），但 Agent 的"第一反应"是通用工具而非专用 skill。这跟论文 Q1（路由）说的"检索+重排"问题一致——skill 在库里但 Agent 没意识到应该先用它。

## 影响

浪费了 4 轮交互和约 3 分钟时间。如果 Agent 第一步就走 skill 流程：
- browser_navigate 两次调用（超时）→ 省掉
- curl 多次试探 → 省掉
- 用户提醒 → 省掉

## 改进措施

在当前 memory 中已有规则的基础上，补充一条：

**规则：收到带链接的内容分析请求时，优先检查是否有匹配 skill，有则直接走 skill 流程。** 具体触发词：xhslink.com / xiaohongshu.com / bilibili.com / youtube.com / 小红书 / B站 等。

这条规则需要写入 lessons.md 作为 L2 规则（skill 路由类）。

## 承诺

今后收到 xhslink.com 或类似链接+分析意图时，第一步直接加载 xiaohongshu-analysis skill 走流水线。
