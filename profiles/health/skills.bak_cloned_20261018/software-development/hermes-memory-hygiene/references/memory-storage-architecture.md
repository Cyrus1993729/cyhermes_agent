# Memory 存储架构与审查系统数据边界

## Memory 文件确切实体

两个文件存储在工作目录下的 `memories/` 子目录：

```
hermes/memories/MEMORY.md   — 个人笔记（工具、环境、经验）
hermes/memories/USER.md     — 用户画像（偏好、身份、规范）
```

- 格式：纯文本 markdown，条目用单独的 `§` 行分隔
- 条目可多行，`§` 必须是独立一行（前后无其他字符）
- 编码：UTF-8
- 加载：会话启动时读入 frozen snapshot，注入 system prompt
- 修改：会话内通过 `memory` 工具操作，立即落盘但不更新 prompt（保护缓存）

## 与审查系统的数据边界

以下数据**不进入 memory**，各自有独立存储：

| 数据类型 | 存储位置 | 原因 |
|:---|:---|:---|
| 审查结果 | `reviews/review_log.jsonl` | 高频写入，JSONL 格式，供 trend 分析 |
| 经验教训 | `lessons.md` | 可复用规则库，sprint-contract 自动加载 |
| 安全底线 | `safety_invariants.md` | 跨任务不变量，契约自动引用 |
| 任务契约 | `contracts/contract_*.md` | 每次任务独立文件 |
| 复盘记录 | `references/任务复盘/` | 历史追溯，低频访问 |

**原则**：memory 只存"跨会话稳定事实"，审查系统的工作数据走独立文件体系。
