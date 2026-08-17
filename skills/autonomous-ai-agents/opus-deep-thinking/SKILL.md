---
name: opus-deep-thinking
description: 多主题深度思考时调用 Opus 的编排流程。触发：用户说"你和 Opus 挨个思考"。
version: 1.0.0
metadata:
  hermes:
    tags: [opus, claude-code, deep-thinking, orchestration, multi-topic]
    related_skills: [claude-code, claude-code-workflow]
---

# Opus 多主题深度思考编排

当用户要求"你和 Opus 都深度思考一下 X"（如分析完 N 个帖子/主题后要赋能建议），用本流程。核心：**逐主题独立 prompt 并行跑**（用户明确偏好），不要打包成大杂烩。

## 触发场景

- 用户说"我希望你们挨个思考，而不是一股脑塞给 opus"（2026-08-08 用户原话，明确修正过一次）
- 多主题分析任务收尾时要求"深度思考如何赋能日常"
- 需要 Opus 对 N 个独立主题分别给出判断

## 一、调用语法（实测正确姿势，崩法已记录）

### ✅ 正确（2026-08-08 实测通过）

```bash
export HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897
claude -p --model opus --disallowedTools Read Write Bash < prompt.md > out.md 2> err.log
```

- `--disallowedTools` **裸写空格分隔，不带引号**
- prompt 用 **stdin 重定向 `< file`**
- 用 `terminal(background=true, notify_on_complete=true)` 跑，完成后读输出

### ❌ 崩溃姿势（实测 EXIT:1，输出 0 字节）

```bash
claude -p --model opus --disallowedTools "Read Write Bash" "$(cat prompt.md)"
```

症状：`Permission deny rule "<prompt内容片段>" matches no known tool` 刷屏 → `Error: Input must be provided either through stdin or as a prompt argument`。prompt 内容被误解析成 permission rules。

### 长 prompt 文件管理

每个主题一个独立 prompt 文件（如 `opus_p1.md`、`opus_p2.md`…），含：**用户画像 + 该主题完整内容 + 聚焦任务 + 输出要求**。不要把所有主题塞进一个文件。

## 二、逐主题独立并行（用户红线偏好）

1. 为每个主题写独立 prompt 文件（write_file × N，一次 turn 并行）
2. 并行启动 N 个 `claude -p` 后台进程（各自 `notify_on_complete=true`）
3. 每个完成通知到达后读输出，**逐主题交付**（不要等全部完成才一次倒出）

> 为什么并行：每个主题得到完整专注的思考深度；总耗时≈单个主题耗时，不因主题数线性增长。
> 为什么逐主题交付：用户要"挨个思考"，一条条看到每个主题的双视角对比。

## 三、OAuth 过期恢复（"OAuth session expired and could not be refreshed"）

1. 症状：`claude -p` 输出文件只有一句 `Failed to authenticate: OAuth session expired and could not be refreshed`
2. 恢复：`claude auth login`，必须 `terminal(background=true, pty=true)`——它会打开浏览器授权页
3. 浏览器应自动弹出 claude.com/cai/oauth/authorize 链接；若没弹，把完整链接发给用户手动打开
4. **需要用户在本机浏览器完成授权**（登录 Claude 账号→点授权），agent 无法代劳。进程日志出现 `Login successful.` 即完成
5. 完成后重跑原 `claude -p` 命令即可，无需其他修复

## 四、双视角交付格式（用户认可的结构）

每个主题一条交付消息：

1. **Opus 的核心判断**（精炼，保留关键论据和金句，标注"未核实"项）
2. **我的判断**（Hermes 视角，明确"一致/分歧"——有分歧要摆出来，附双方理由，被说服就明说）
3. **结论 + 优先级**（🔴立即/🟡一周内/🟢观察 + 具体第一步）
4. 全部主题交付完，给一张**跨主题行动清单**（合并共识，标红最高优先级项）
5. 完整版（含 Opus 全文）合并进存档 md，用 `MEDIA:` 发送

## 五、坑与注意事项

- **Opus 单次任务 2-5 分钟起**，6 个并行约 3-5 分钟全部完成。不要中途 kill（除非用户打断要求改方向）
- 用户中途打断改方向（如"挨个思考"）→ **立即 kill 当前大杂烩任务**，按新指令重来，不要辩解
- prompt 里给足背景：子进程没有会话上下文，用户画像+主题内容必须自包含
- 内容里有"未核实"信息（工具名、GitHub 地址、演示数据）要在 prompt 里明确标注，让 Opus 知道边界
- 涉及投资/决策建议时，Opus 输出要保留原文免责声明（如 FriesTrader 的"不构成投资建议"），交付时带上
- 🔴 **`claude -p` 输出文件可能被 read_file 误判 binary（2026-08-14 实踩）**：bash 重定向生成的 out.md 是 UTF-8 文本但含 CRLF 时，read_file 报 `Binary file - cannot display as text`（`file out.md` 仍显示 "Unicode text, UTF-8"）——不是真二进制。用 `python -c "open('out.md', encoding='utf-8').read()"`（terminal）读取即可；不要因此删掉输出重跑（Opus 单次 2-5 分钟成本）
- 单篇分析（非多主题）同样适用本流程：一个自包含 prompt（用户画像+文章全文+聚焦任务+输出要求）后台跑，期间先交付 Hermes 视角，Opus 完成通知到达后再补对比（2026-08-14 验证）
- **触发短语**：用户说"同样的问题，你去问一下opus"/"你问下Opus" = 把当前问题原样交给 Opus 独立评估（单主题变体，用上一条的流程）
- **事实核查分工（2026-08-15 Hermes Studio 评估实踩，交付前必做）**：Opus 无联网权限，无法核实仓库真实性/star/具体配置默认值，它自己会声明"无法验证"。Hermes 的职责是**回源验证后再交付**：① Opus 声称无法核实的（仓库是否存在、star 是否真实）→ 用 GitHub API 核实；② Opus 提出的具体技术担忧（如"Web 端口默认没绑 127.0.0.1"）→ 直接查源码/config 确认或证伪，把"担忧"升级为"事实"（本次查 config.ts 证实 BIND_HOST 默认 0.0.0.0 + 默认账号 admin/123456，同时发现认证模块其实存在——两边都要报，别只报坏消息）。分工：Opus 负责机制批判，Hermes 负责事实核查，两边做完交付物才可信

## 参考实例

2026-08-08：6 个小红书帖子分析完成后，用户要求"你和 Opus 挨个思考赋能"。6 个独立 prompt 并行跑，每帖交付 Hermes+Opus 双视角，产出跨帖行动清单（Hermes 配置调优 6 项、黄金决策闸门 T+7、复盘模板交接包等）。完整流程见 session 记录。
