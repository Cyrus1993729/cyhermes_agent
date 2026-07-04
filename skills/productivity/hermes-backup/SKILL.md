---
name: hermes-backup
description: "Hermes Agent 数据备份与恢复——Git 私有仓库 + 白名单 .gitignore + cron 失败通知。路径验证、恢复流程。"
version: 1.0.0
category: productivity
tags: [hermes, backup, git, cron, disaster-recovery]
---

# Hermes Agent 备份与恢复

> 来源：小红书「Hermes Agent 完整备份教程」by 鹏叔大玩家（2026.7.2 分析提炼）

## 为什么必须备份

三个真实场景：
1. **重装系统** → `~/.hermes/` 随旧系统盘格式化消失，几个月累积的记忆、技能全没
2. **硬盘物理损坏** → 数据物理消失，专业恢复报价几千块，还不一定救得回来
3. **换新电脑** → 不想从零调教，但旧电脑已卖/归还

一句话：**Hermes 数据没有脱离当前这台电脑独立存在 = 在赌硬盘不坏。**

## 核心资产清单（全部在数据目录下）

| 目录/文件 | 内容 | 不可恢复性 |
|:---|:---|:---|
| `memories/MEMORY.md` + `USER.md` | 几个月累积的个人偏好和上下文 | 🔴 完全手动积累 |
| `skills/` | 30+ 个自动生成和手动编写的技能文件 | 🔴 多轮对话调教出来的 |
| `config.yaml` | 模型、工具、权限设置 | 🟡 可重新配置但耗时 |
| `auth.json` | OAuth token、凭证池 | 🟡 可重授权 |
| `profiles/` | 多 Profile 配置 | 🟡 可重建 |
| `scripts/` | 自定义脚本（qwen_review.py 等） | 🔴 自己写的代码 |
| `reviews/` | 审查日志（review_log.jsonl） | 🟡 纵向数据 |
| `lessons.md` | 经验教训 | 🔴 自进化积累 |
| `safety_invariants.md` | 安全基线 | 🟡 可重建 |
| `model_routing.md` | 模型路由表 | 🟡 可重建 |

> ⚠️ 备份总大小一般 < 50MB，不占空间。

## 路径验证（必须第一步！）

Windows 上路径易出错。执行前验证：

```bash
# 真实数据目录（Windows）——必须确认存在
ls ~/AppData/Local/hermes/config.yaml && echo "CORRECT PATH"

# ~/.hermes/ 大概率不存在——Opus 审查发现的阻断性问题
ls ~/.hermes/config.yaml 2>/dev/null || echo "WRONG PATH — do NOT use"
```

> ⚠️ 下面的命令全部用 `~/AppData/Local/hermes/`（不是 `~/.hermes/`！）

## 云端 Git 备份

### 1. 创建 .gitignore（白名单模式——Opus 审查要求）

```gitignore
# 默认全部忽略
*
# 显式放行确定安全的
!memories/
!skills/
!scripts/
!reviews/
!references/
!lessons.md
!safety_invariants.md
!model_routing.md
!config.yaml
!.gitignore
```

> **为什么是白名单不是黑名单？** 黑名单模式下，任何未预料的新文件（如误存的密钥）会被 `git add -A` 永久推进 GitHub。白名单默认安全。Opus 审查明确指出：对不看代码的用户，黑名单 = 定时炸弹。

### 2. 首次配置

```bash
cd ~/AppData/Local/hermes
git init

# 创建上面的白名单 .gitignore
git add -A
git commit -m "首次备份 $(date +%Y-%m-%d)"
git remote add origin git@github.com:<用户名>/hermes-backup.git
git push -u origin main
```

**首次 push 前注意：** 如果从 Agent（非交互终端）操作，`git push` 会卡在认证步骤——Git Credential Manager 弹窗无法在 Agent 的终端环境里出现。首次 push 需要用户**自己在桌面终端里手动执行一次**，弹出 GitHub 登录窗口授权。之后 Git Credential Manager 会记住凭证，后续 cron 自动 push 无需再认证。

### 3. 日常备份脚本（带失败通知 ⚠️ Opus 要求）

**不能用裸 cron 一行命令**——push 失败是静默的，用户不会知道。

#### ⚠️ Windows 脚本格式陷阱（2026.7.3 实战教训）

`no_agent` 模式的 cron runner 在 Windows 上**用 Python 执行脚本**，不是 bash 也不是 cmd.exe：

| 脚本格式 | 结果 | 原因 |
|:---|:---|:---|
| `.sh` (bash) | ❌ | Windows 反斜杠路径被 bash 当转义符吞掉 |
| `.bat` (batch) | ❌ | Python 解析器遇到中文/emoji 字符语法报错 |
| `.py` (Python) | ✅ | cron runner 原生支持 |

**结论：`no_agent` cron 脚本在 Windows 上必须用 `.py`。**

#### 备份脚本 `scripts/backup_git.py`

```python
#!/usr/bin/env python3
"""Hermes Agent Git 备份脚本 — no_agent cron 用 Python 执行"""
import subprocess, sys, os
from datetime import datetime

HERMES_HOME = os.path.expandvars(r"%LOCALAPPDATA%\\hermes")
os.chdir(HERMES_HOME)

subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", f"backup {datetime.now():%Y-%m-%d}"],
               capture_output=True)  # 无变更时不报错

result = subprocess.run(["git", "push"], capture_output=True, text=True)
if result.returncode == 0:
    print(f"Backup success {datetime.now():%Y-%m-%d}")
else:
    print(f"Backup FAILED {datetime.now():%Y-%m-%d}: {result.stderr.strip()}")
    sys.exit(1)
```

### 4. Cron 自动化

#### 投递策略选择

`deliver` 有三种策略，按需求选择：

| 投递策略 | 行为 | 适用场景 |
|:---|:---|:---|
| `deliver='origin'` | 脚本 stdout → 推送到当前会话。成功/失败都通知 | 需要每天确认备份状态 |
| `deliver='local'` | 输出存到本地文件，不推送 | 静默后台，不被打扰 |
| `deliver='origin'` + 凌晨错峰 | 推送但跑在 3:00 而非 8:00 | 又要通知又不怕撞车 |

**ℹ️ 微信 iLink 限流碰撞（2026.7.3 实战，已过时）**

> ⚠️ 以下为历史记录。2026.7.4 已迁移到 Telegram 平台，不再使用微信 iLink 通道。Telegram Bot API 无 10 条回复限制，不存在类似碰撞问题。保留此段作为微信时代的故障排查参考。
>
> ~~`no_agent` cron 的投递和正常会话回复走**同一 WeChat iLink 通道**。当两者同时发送时，iLink 返回 `errcode=-2`（频率限制），触发适配器内置熔断器（30s 冷却），冷却期内**所有消息全部被拒**——包括用户正在等待的会话回复。~~
>
> ~~Hermes 的 weixin 适配器已有防御（`_send_text_gate` 串行化、熔断器、退避重试），但无法解决「两个独立调度源同时争夺同一通道」的问题。~~

**三种避撞方案**：

1. **凌晨错峰**（推荐）— cron 改到 3:00~4:00，用户在睡觉不聊天，天然不撞。失败消息醒来看到。
2. **脚本静默成功** — `backup_git.py` 成功时 stdout 为空（`no_agent` 空输出 = 不推送），仅失败时发一条通知。减少 99% 的发送次数。
3. **双通道解耦** — 备份 `deliver='local'`，另建独立 watchdog cron 定时检查输出文件并报告。

**推荐组合：凌晨错峰 + 脚本静默成功。**

## Cron 故障排查指南（2026.7.3 实战路径）

当备份 cron 报错、收不到通知、或 cron 状态显示 `error` 时，按以下路径排查。

### 1. 检查 cron 状态

```bash
hermes cron list
```

查看 `last_status`（ok/error）、`last_delivery_error`（投递错误）、`last_run_at`。

### 2. 手动执行脚本

```bash
python ~/AppData/Local/hermes/scripts/backup_git.py
```

确认脚本本身能跑通。注意 `no_agent` cron 的 `script` 路径相对于 `~/.hermes/scripts/`。

### 3. 检查投递日志

```bash
grep -i "rate limit\|cooldown\|send failed" ~/AppData/Local/hermes/logs/gateway.log | tail -20
grep "delivery error" ~/AppData/Local/hermes/logs/errors.log | tail -20
```

### 4. 识别限流碰撞

关键信号——同一时间戳出现**两种错误**：

```
15:14:55 ERROR [Weixin] send failed: iLink sendmessage rate limited; cooldown 30s
15:14:55 ERROR cron.scheduler: Job 'xxx': delivery error: Weixin send failed
```

第一行 = 会话回复发送失败；第二行 = cron 通知投递失败。两者同时出现 = **限流碰撞**。

### 5. 检查 Windows 脚本格式

| 格式 | 结果 | 排查方式 |
|:---|:---|:---|
| `.py` | ✅ | `python script.py` |
| `.sh` | 反斜杠被吞 | `bash script.sh` 看路径 |
| `.bat` | emoji 语法报错 | 检查 `SyntaxError` |

### 6. 深水区：阅读适配器代码

```bash
ls ~/AppData/Local/hermes/hermes-agent/gateway/platforms/weixin.py
```

关键常量：`RATE_LIMIT_ERRCODE = -2`，`BACKOFF_DELAY_SECONDS = 30`，熔断器 `_rate_limit_circuit_until`，串行化锁 `_send_text_gate`。

#### cron 脚本存放位置

`no_agent` cron 的 `script` 参数路径是相对于 `~/.hermes/scripts/` 的，**不是** `~/AppData/Local/hermes/scripts/`。如果脚本在后者，需要先复制过去：

```bash
cp ~/AppData/Local/hermes/scripts/backup_git.py ~/.hermes/scripts/
```

## 恢复流程

```bash
# 1. 安装 Hermes
# 2. Clone 仓库到真实数据目录
git clone git@github.com:<用户名>/hermes-backup.git ~/AppData/Local/hermes/

# 3. 配置 Git 凭证（SSH key 或 PAT）
ssh-keygen -t ed25519 -C "hermes-backup"
# 添加公钥到 GitHub → ssh -T git@github.com 验证

# 4. 重设 API 认证（auth.json 不在备份里）
hermes auth add <provider>

# 5. 检查 config.yaml 代理地址
# 6. hermes gateway start
```

> **额外需要手动重建的：** cron 任务定义（不在 ~/.hermes 目录里）、.env 中的 API key、Python 运行环境依赖。

## 已落地实例（2026.7.2）

实际部署配置参考（Windows, Telegram 用户）：

| 配置项 | 值 |
|:---|:---|
| 数据目录 | `%LOCALAPPDATA%\\hermes\\` (= `C:\\Users\\<用户>\\AppData\\Local\\hermes\\`) |
| GitHub 仓库 | `Cyrus1993729/cyhermes_agent`（私有） |
| 备份脚本 | `backup_git.py`（`.py` — `no_agent` cron 用 Python 执行，不能用 `.sh`/`.bat`） |
| Cron | `5b4b88f1f8bf`，`0 3 * * *`，`no_agent: true` |
| 投递策略 | `deliver='origin'` + 凌晨 3:00 错峰 |
| 脚本位置 | `~/.hermes/scripts/backup_git.py`（cron 从此目录查找，不是 `~/AppData/Local/hermes/scripts/`） |
| 推送认证 | Windows Git Credential Manager（首次手动弹窗授权） |

**no_agent 模式** — cron 不跑 LLM agent，直接执行脚本。凌晨 3:00 运行避免和用户聊天碰撞。脚本成功时 stdout 为空（静默），失败时推送通知。如需额外保障，可另建轻量 watchdog。

| 来源 | 说明 |
|:---|:---|
| 小红书帖子 6a45239a0000000008002d69 | 鹏叔大玩家，3:59 视频，33赞/86收藏 |
| 分析方式 | faster-whisper ASR + 关键帧 Vision |
| 适用性 | 帖子原为 Linux/Mac 视角，本篇已适配 Windows 路径 |

## 注意事项

- **路径验证** — `~/.hermes/` 在 Windows bash 下不等于真实数据目录。必须确认用 `~/AppData/Local/hermes/`
- **白名单 .gitignore** — 默认全忽略，显式放行。黑名单对新文件不安全
- **auth.json / .env 不入仓库** — 白名单已排除，恢复时手动重建
- **GitHub 私有仓库** — 必须 Private
- **失败通知** — `git push` 失败 cron 不会自动通知，脚本必须显式处理 → cron agent 读脚本 stderr 发送通知
- **首次 push 前安全扫描** — 确认 memory/skill 中没有 API key / 密码 / 手机号
- **未测试的备份 = 没有备份** — 首推后在另一台机器上 clone 验证
- **cron 任务不在备份里** — 换电脑后需重建
