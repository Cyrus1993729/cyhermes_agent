# Claude Code Opus 打印模式调试方法

> 2026-06-27: 在排查 Hermes Qwen custom provider 401 问题时发现。

## 症状

`claude -p "task" --model opus --max-turns 20` 静默耗尽所有 turns，产生零输出：
```
Error: Reached max turns (20)
```

## 根因

Opus 在有大上下文文件的项目中（如 69K `AGENTS.md`、`CLAUDE.md`）会消费大量 turns
读取项目上下文，加上代码文件读取，可能在输出答案前耗尽 turn 配额。

## 修复尝试记录

| 尝试 | 做法 | 结果 |
|:---|:---|:---|
| 1 | 提示词中有 YAML 代码块 | bash 将缩进 YAML 当 shell 命令执行 → 立即失败 |
| 2 | pipe 文件内容 + `$(cat)` | stdin 和参数竞争 → max turns |
| 3 | `--allowedTools Read` 限制工具范围 | 仍然 max turns |
| 4 | `--bare` 跳过项目上下文 | 丢失 OAuth 登录态 → `Not logged in`（bare 需要 `ANTHROPIC_API_KEY`） |
| 5 | 简化提示词 + `--allowedTools Read` | ✅ 成功 |

## 有效的方法

```bash
# 1. 先烟测确认 Opus 可用
timeout 60 claude -p "回复OK" --model opus --max-turns 1 --output-format text

# 2. 简化提示词（不要 YAML、不要长代码块）
# 3. 加 --allowedTools Read
claude -p "只读排查文件 X 和 Y，找出根因。中文回复。" \
  --model opus --max-turns 20 --allowedTools Read --output-format text
```

## 避免的方法

- `--bare`：会跳过 OAuth，除非有 `ANTHROPIC_API_KEY`
- 提示词中放 YAML/代码块：bash 会尝试解析执行
- 使用 `$(cat)` + pipe 同时传参：stdin 竞争
