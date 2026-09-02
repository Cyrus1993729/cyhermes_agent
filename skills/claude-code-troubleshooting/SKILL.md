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
| `claude auth login` 能生成授权 URL、浏览器打开授权页后跳 `claude.ai/restricted` 显示 **"Your account is on hold"** | **账户被风控冻结（不是凭证问题）**——OAuth 管线健康但账户被 Claude 判"异常活动"（常见诱因：大陆 IP+代理访问、高频 CLI 调用），数据安全，审查约 10 天 | 页面点 "Request a review" 申诉（如实说明个人正常使用+大陆代理访问）；**期间 Opus/Claude Code 全不可用，走降级链 GPT-5.6 等；不要反复重试 login** |

## 账户冻结 vs 凭证过期 判别（2026-08-31 实踩）

1. `claude auth status --text` → `Login: Expired`（两种问题都这样显示，仅凭它无法区分）
2. 跑 `claude auth login`（`terminal background=true pty=true`；**Windows 无 tmux**）→ 能正常打印授权 URL = OAuth 管线健康；终端输出按宽度折行，拼 URL 时把 `client_id=...-59`+`44d...`、`org%3Acreat`+`e_api_key`、`code_chall`+`enge=`、`state=...Qz_1h`+`FnZgY` 这类断行接回
3. 浏览器打开授权 URL 却落到 `claude.ai/restricted` + "Your account is on hold" → **账户级风控冻结**，非凭证故障
4. 处理：申诉（Request a review）+ 等 ~10 天（邮件通知）；恢复前 OAuth 无法刷新是冻结的必然结果，无需排障
5. 冻结期间受影响面：`claude -p`（Opus 深度分析）、黄金周报双审、一切 sign-off——按用户降级链（GPT-5.6/千问 3.7 Max）替代，交付中注明降级原因

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
