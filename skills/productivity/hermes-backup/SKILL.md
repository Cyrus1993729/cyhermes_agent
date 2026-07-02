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

**首推前必做：** 让 Hermes 扫描要备份的内容，确认没有 API key / token / 密码 / 手机号后，再 push。

### 3. 日常备份脚本（带失败通知 ⚠️ Opus 要求）

**不能用裸 cron 一行命令**——push 失败是静默的，用户不会知道。写 `scripts/backup.sh`：

```bash
#!/bin/bash
cd ~/AppData/Local/hermes || exit 1
git add -A
git commit -m "backup $(date +%Y-%m-%d)" 2>/dev/null
if git push 2>&1; then
    echo "备份成功 $(date +%Y-%m-%d)"
else
    echo "备份失败 $(date +%Y-%m-%d)"
    exit 1
fi
```

### 4. Cron 自动化

cron agent 运行备份脚本，成功安静、失败通过 WeChat 通知用户：

```
schedule: 0 8 * * *（每天早8点）
prompt: "运行 scripts/backup.sh。成功则安静；失败则把错误信息发微信给用户。"
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

## 已验证

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
- **失败通知** — `git push` 失败 cron 不会自动通知，脚本必须显式处理 → cron agent 读脚本 stderr 发微信
- **首次 push 前安全扫描** — 确认 memory/skill 中没有 API key / 密码 / 手机号
- **未测试的备份 = 没有备份** — 首推后在另一台机器上 clone 验证
- **cron 任务不在备份里** — 换电脑后需重建
