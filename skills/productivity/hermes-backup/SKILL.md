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
!memories/**
!skills/
!skills/**
!scripts/
!scripts/**
!reviews/
!reviews/**
!references/
!references/**
!profiles/
!profiles/**
!cron/
!cron/**
!lessons.md
!safety_invariants.md
!model_routing.md
!config.yaml
!.gitignore

# === 凭证类绝不入库（必须放在所有放行规则之后，后写者优先）===
.env
.env.*
**/.env
**/.env.*
**/auth.json
**/*.pem
**/*.key
**/hermes-cloud-connection.json
**/.local/
profiles/**/.env
profiles/**/auth.json
```

> ✅ **白名单本身不够**：`!profiles/**` 会把 `profiles/health/.env`（真实 API Key）一起放行。
> 白名单只解决了「未预料的新文件」，不解决「已知敏感目录里的敏感文件」。
> **必须在所有放行规则之后再补一段凭证排除**（gitignore 后写的规则优先）。
> 2026-10-21 就是因为漏了这一段，含 DeepSeek key 的提交被 GitHub push protection 拦下，备份连挂 5 天。
> 详见 `references/git-push-protection-2026-10.md`。

> ⚠️ `!config.yaml` 是另一颗雷：config.yaml 里 `api_key:` 是明文真钥匙，
> 放行它 = 密钥进备份仓库。要么备份前脱敏，要么整个不放行。同样见上述 reference。

#### config.yaml 脱敏提交（2026-10-21 已落地并验证）

`scripts/backup_git.py` 已内置脱敏，机制是**不碰工作区文件**：

1. `git add -A` 正常暂存
2. 读工作区 config.yaml → 行级正则把 `api_key/api_secret/access_key/secret_key/secret/token/password` 的值替换成 `"***REDACTED***"`
3. `git hash-object -w --stdin` 写入脱敏内容成 blob，再用 `git update-index --add --cacheinfo 100644,<blob>,config.yaml` 覆盖 index 条目
4. 提交前**回读 `git show :config.yaml`** 自查，若仍匹配 `oc_sk_…/sk-…/sk-ws-…` 特征则**中止提交并报警**（宁可备份失败也不泄露）

实测（2026-10-21）：远程版本真实密钥 0 处、REDACTED 6 处（3 个 api_key + 3 个 token），YAML 结构完全一致，工作区原文件仍有 3 处真 key，Hermes 运行不受影响。

🔴 **副作用必知**：`git status` 会**永远显示 `config.yaml` 已修改**（index 是脱敏版、工作区是真版）。这不是没提交，不要去 `git add` 或 `git checkout` 它。

🔴 **恢复时**：克隆回来的 config.yaml 里 `api_key` 全是 `***REDACTED***`，必须手动重新填真实密钥。

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

> ⚠️ 以下为历史记录。2026.7.4 主平台迁 Telegram，但 **2026-10-18 起微信被重新启用作通知渠道；2026-10-21 起日程提醒也走微信**——所以「cron 投递和会话回复抢同一个通道」重新是个真问题，不是历史遗迹。
> 当前机制与应对见 `hermes-wechat-delivery`：context_token 每轮仅 10 条额度、**分块也占额度**、主动推送单条 ≤900 字、脚本自发送时 cron 要 `deliver='local'`。
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

确认脚本本身能跑通。`script` 相对路径解析到 `~/AppData/Local/hermes/scripts/`（支持子目录），不是 `~/.hermes/scripts/`。

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

### 7. 代理没监听 / GitHub 密钥扫描拦截（比限流更常见，2026-10-21 实战）

看到 `Failed to connect to github.com port 443 via 127.0.0.1 after N ms`，**不要直接当成「网络不通」**：报错里的 `127.0.0.1` 不带端口号，很可能是 git 配了一个**根本没在监听**的代理端口（换了代理客户端，git 全局配置不会自动跟着改）。

```bash
git config --global --get-regexp proxy                       # 它让你走哪个端口
netstat -ano | grep LISTENING | grep -E ":1080[0-9]|:789[0-9]"  # 哪个端口真的在监听
```

代理修好后如果 push 仍然失败，看 remote 段有没有 `GH013` / `push declined due to repository rule violations` / `Push cannot contain secrets`——那就是 **GitHub push protection**，它拦的是「待推历史提交里的密钥」，光改工作区/.gitignore 没用。

完整诊断四连、`git reset --soft origin/main` 重建干净提交的修复步骤、以及「config.yaml 里明文 api_key 已经在远程仓库」这种情况怎么处理，全部写在 `references/git-push-protection-2026-10.md`（必读）。

一句话记牢：**白名单 .gitignore 不等于安全；凭证排除段必须写在所有放行规则之后；密钥一旦确认到过远程，唯一正确做法是轮换密钥，不是擦历史。**

#### cron 脚本存放位置

`script` 相对路径解析到 **`~/AppData/Local/hermes/scripts/`**（不是 `~/.hermes/scripts/`——那是旧版错误认知），并且**支持子目录**：2026-10-21 实测 `script: dayflow/df_morning.py` 直接跑通，无需复制到别处。

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

## 多机共享与迁移（2026-09-01 双机布局咨询沉淀）

两台机器都装 Hermes 时，共享什么、不共享什么：

| 资产 | 共享策略 | 方式 |
|:---|:---|:---|
| skills/ | ✅ 推荐共享 | clone 备份仓库，或 `hermes profile export/import`（官方 tar.gz 一键迁移） |
| memories/ | ⚠️ 选择性 | 90% 是本机环境事实（D:\Workspace 路径、Clash 代理、cron 体系），跨机会误导新机 agent；新机器从零积累更干净 |
| config.yaml | ✅ 可带 | 需按新机改代理地址/模型 provider |
| auth.json / .env | ❌ 不在备份内 | `hermes auth add` + 重填 API key |
| cron 任务 | ❌ 不在备份内 | 手动重建 |

- **skills=可复用流程（跨机有效），memory=本机环境快照（跨机无效）**——共享只带 skills。
- 不要两台机器双向同步同一仓库（会打架）；单向：主机推 → 新机 clone 即可。

## 已落地实例（2026.7.2）

实际部署配置参考（Windows, Telegram 用户）：

| 配置项 | 值 |
|:---|:---|
| 数据目录 | `%LOCALAPPDATA%\\hermes\\` (= `C:\\Users\\<用户>\\AppData\\Local\\hermes\\`) |
| GitHub 仓库 | `Cyrus1993729/cyhermes_agent`（私有） |
| 备份脚本 | `backup_git.py`（`.py` — `no_agent` cron 用 Python 执行，不能用 `.sh`/`.bat`） |
| Cron | `5b4b88f1f8bf`，实际 `0 8 * * *`（文档早前写的 `0 3 * * *` 凌晨错峰**未落地**，按当前 jobs.json 为准） |
| 投递策略 | `deliver='origin'` + 凌晨 3:00 错峰 |
| 脚本位置 | `~/AppData/Local/hermes/scripts/backup_git.py`（`script` 相对路径解析到此目录，支持子目录） |
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
- **auth.json / .env 不入仓库** — 靠白名单末尾的**凭证排除段**，仅靠 `!profiles/**` 会漏；恢复时手动重建
- **config.yaml 含明文 api_key** — 放行它等于密钥进仓库，要么备份前脱敏要么不放行
- **GitHub 私有仓库** — 必须 Private
- **失败通知** — `git push` 失败 cron 不会自动通知，脚本必须显式处理 → cron agent 读脚本 stderr 发送通知
- **首次 push 前安全扫描** — 确认 memory/skill 中没有 API key / 密码 / 手机号
- **未测试的备份 = 没有备份** — 首推后在另一台机器上 clone 验证
- **cron 任务不在备份里** — 换电脑后需重建
