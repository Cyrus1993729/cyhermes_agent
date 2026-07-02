# Opus 4.8 源码排查模式（2026-06-27 验证）

经过 5 次尝试终于让 Opus 4.8 成功完成源码只读排查任务。以下是教训和正确模式。

## 背景

任务：排查 Hermes MoA 的 Qwen custom provider 401 错误。
需要 Opus 阅读 `agent/moa_loop.py`、`agent/auxiliary_client.py`、
`hermes_cli/models.py`、`plugins/model-providers/custom/__init__.py` 等源码。

## 五次尝试的失败教训

### 尝试 1：YAML 被 bash 误解析 ❌
```
claude -p "... MoA config: yaml: providers: qwen-bailian: ..."
→ bash: yaml: command not found
```
**根因**：提示词中的 YAML 代码块缩进被 bash 当作命令执行。
**修复**：将配置信息写成独立文件，不要内嵌 YAML 在 `-p "..."` 参数里。

### 尝试 2：pipe 传参 + max turns 耗尽 ❌
```
cat debug.txt | claude -p "$(cat)" --max-turns 20
→ Error: Reached max turns (20)
```
**根因**：`--max-turns 20` 不够读 4-5 个源码文件（每个文件一次 Read 调用就是 4-5 turns，
加上 AGENTS.md 等上下文文件自动加载消耗额外 turns）。

### 尝试 3：`--allowedTools Read` 仍不够 ❌
```
claude -p "..." --model opus --max-turns 10 --allowedTools Read
→ Error: Reached max turns (10)
```
**根因**：虽然限制了工具，但 `--max-turns 10` 仍然不够。项目中的 AGENTS.md（69K chars）
被自动加载到上下文，消耗了 turns。

### 尝试 4：`--bare` 丢失登录态 ❌
```
claude --bare -p "..." --model opus
→ Not logged in · Please run /login
```
**根因**：`--bare` 跳过了 OAuth 登录，但我们也因此丢失了 Claude Pro 订阅的认证。
`--bare` 需要 `ANTHROPIC_API_KEY` 环境变量才能工作。

### 尝试 5：成功 ✅
```
claude -p "..." --model opus --max-turns 20 --allowedTools Read --output-format text
```
**成功要素**：
- 不加 `--bare`（保留 OAuth 登录态）
- `--max-turns 20`（足够读 4-5 个文件 + 思考）
- `--allowedTools Read`（防止 Opus 做无用操作）
- 提示词中不含 YAML 代码块（避免 bash 解析）
- 明确指定阅读顺序：`请依次阅读以下文件：1. ... 2. ...`

## 正确的 Opus 源码排查流程

### Step 1: 先做烟雾测试
```bash
timeout 60 claude -p "回复OK" --model opus --max-turns 1 --output-format text
# 必须在 60s 内返回 "OK"
```

### Step 2: 简化提示词格式
不要在 `-p "..."` 中包含 YAML/JSON 配置块。如需传递配置信息：
- 写到一个独立文本文件
- 提示词中只说"config.yaml 中 providers.qwen-bailian 已配置 base_url、api_key..."
- 不粘贴完整 YAML

### Step 3: 选择正确的参数组合
```bash
claude -p "只读排查...请依次阅读以下文件：1. A.py 2. B.py 3. C.py ..." \
  --model opus \
  --max-turns 20 \
  --allowedTools Read \
  --output-format text
```

| 参数 | 为什么 |
|:---|:---|
| `--max-turns 20` | 读 N 个文件需要 N turns + 思考 + 1 个回答 turn |
| `--allowedTools Read` | 防止模型分心做无关操作 |
| `--output-format text` | 避免 stream-json 的额外开销 |
| 不要 `--bare` | 除非有 ANTHROPIC_API_KEY |
| 不要 YAML | 会被 bash 解析 |

### Step 4: 结果解读
Opus 返回的是结构化图文诊断，通常包含：
- 根因文件:行号 → 判断逻辑 → 为什么出错
- 修复方案（只读模式不会执行）
- 附带影响面分析

## 禁止的做法

- ❌ 在命令行提示词中嵌入 YAML/JSON
- ❌ `--max-turns` < 10 的源码排查
- ❌ `--bare` 除非确认有 ANTHROPIC_API_KEY
- ❌ 在 Opus 无输出时默默换模型（违反 claude-code-workflow Rule 1）
- ❌ 在 Opus 无输出时不断重跑而不改变参数（最多尝试 3 次同参数，然后必须调整）
