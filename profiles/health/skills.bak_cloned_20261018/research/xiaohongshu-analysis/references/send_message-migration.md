# send_message 工具迁移指南（v0.17.0）

## 问题

Hermes Agent v0.17.0 从 Agent 工具箱中移除了 `send_message` 工具。
网关（gateway）的消息发送能力不受影响——Agent 无法主动调用 `send_message`，
但普通回复会被网关自动送达微信。

## 受影响的文件

| 文件 | 影响 |
|:---|:---|
| `SKILL.md` | 「微信分段发送」步骤使用 `send_message` → 需改为普通回复输出 |
| `references/hermes-upgrade-0.14-to-0.17.md` | 参考文档中引用 `send_message` → 不影晌运行 |
| `references/ilink-rate-limiting.md` | 参考文档中引用 `send_message` → 不影晌运行 |

## 修复方法

将 `send_message` 调用替换为普通 Markdown 回复：

```diff
- 用 send_message 逐段发送报告
+ 将报告拆分为多段，逐段作为普通回复输出
+ 网关会自动将每段回复送达微信
```

不需要修改底层分析逻辑，只改交付步骤。

## 相关 Skill 影响

| Skill | 影响 | 是否使用 |
|:---|:---|:---|
| `yuanbao` | send_message 完全失效 | 用户极少使用 |
| Cron 输出 | 用 send_message 投递结果的 cron 会静默失败 | 需逐一检查 |
