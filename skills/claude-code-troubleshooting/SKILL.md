---
name: claude-code-troubleshooting
description: Claude Code CLI 认证排障：OAuth 凭证损坏恢复、Windows 陷阱。
version: 1.0.0
category: software-development
tags: [Claude, OAuth, troubleshooting, Windows, authentication]
---

# Claude Code CLI 排障

## 触发条件

- `claude -p` 返回认证错误
- `claude auth login` 死循环/无响应
- OAuth 登录后仍报 "Not logged in"

## 症状→诊断

| 症状 | 诊断 | 修复 |
|---|---|---|
| `Failed to authenticate: OAuth session expired` | `.credentials.json` 里 accessToken/refreshToken 为空 | 凭证恢复流程 |
| `Not logged in · Please run /login` | 凭证文件不存在 | `claude auth login` |
| PowerShell 里 `claude` 命令找不到 | npm 全局路径不在 PS 的 PATH | 用 CMD 或 git-bash |
| localhost 拒绝连接 | auth login 的本地服务器超时退出 | 后台模式重跑 |

## 凭证恢复流程

当 `~/.claude/.credentials.json` 内容为：
```json
{"claudeAiOauth":{"accessToken":"","refreshToken":"","expiresAt":0}}
```

损坏凭证阻断 `claude auth login` 自身刷新→死锁。

步骤：
1. **备份删除**：`cp ~/.claude/.credentials.json ~/.claude/.credentials.json.bak && rm ~/.claude/.credentials.json`
2. **后台运行**（foreground 超时会导致 localhost 服务器在回调前死掉）：`export HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=... && claude auth login`（用 terminal background=true pty=true）
3. 用户打开 URL 授权→回调写入新凭证
4. 验证：`timeout 30 claude -p "say OK" --max-turns 1 < /dev/null`

## 命令对照

`claude login`（旧）→ `claude auth login`（新）。旧命令可能只输出 "Not logged in" 不启动 OAuth。

## Windows 注意

- 不用 PowerShell——npm 全局 claude 不在 PS PATH。用 CMD 或 git-bash。
- Windows Store Claude Desktop 会覆盖 CLI 安装，需重装 `npm install -g @anthropic-ai/claude-code`
