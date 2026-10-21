# Claude Code OAuth 认证故障排查

> 来源：2026-08-03 黄金周报 Opus 审查失败。根因：credentials.json 中 token 为空，且 `claude login` 自身也因尝试刷新坏 token 而死锁。

## 症状

```bash
claude -p "hello" --max-turns 1 < /dev/null
# → Failed to authenticate: OAuth session expired and could not be refreshed

claude --version
# → 2.1.215 (Claude Code)  ← 版本正常，只是认证挂了
```

## 诊断

检查 `~/.claude/.credentials.json`：

```bash
cat ~/.claude/.credentials.json
```

如果看到：
```json
{"claudeAiOauth":{"accessToken":"","refreshToken":"","expiresAt":0,...}}
```

说明 **access token + refresh token 双双丢失**，无法自动续期。

## 修复步骤

### 1. 删除坏凭证（关键！不删会死锁）

```bash
cp ~/.claude/.credentials.json ~/.claude/.credentials.json.bak
rm ~/.claude/.credentials.json
```

**为什么必须删？** `claude login` 的第一步是尝试用现有 token 刷新——如果 token 是空的，刷新失败，login 本身也被阻断。只有清掉文件让它从零开始。

### 2. 重新登录

```bash
claude login
```

会弹出浏览器 → 跳转 Anthropic 授权页 → 点 Allow → 终端显示 "✓ Authenticated successfully"。

### 3. 验证

```bash
claude -p "say hi" --max-turns 1 < /dev/null
# 应该正常返回
```

## 关键区分

- **Claude 桌面客户端登录** ≠ **Claude Code CLI 登录**——两套认证互不相干
- CLI 的 `claude` 二进制可能不在系统 PATH 中（本机路径：`~/AppData/Local/hermes/node/claude`）

## 预防

- OAuth token 过期时间随 Anthropic 策略而定，无固定周期
- 建议设置每月提醒检查 `claude -p "test"` 的连通性
- 备选方案：使用 `ANTHROPIC_API_KEY` 环境变量绕过 OAuth
