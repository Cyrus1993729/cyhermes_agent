# Hermes Agent 升级指南：v0.14.0 → v0.17.0

> 调研日期：2026-06-21  
> 当前版本：v0.14.0 (pip editable install)  
> 目标版本：v0.17.0 (v2026.6.19, "The Reach Release")  
> 安装位置：`C:\Users\Administrator\AppData\Local\hermes\hermes-agent\`  
> HERMES_HOME：`C:\Users\Administrator\AppData\Local\hermes\`

## 🚨 前置条件：Python 3.12+

v0.16+ 在 Python 3.11 上有已知 Bug（GitHub Issue #42810, Open）：API 调用失败，报 `RuntimeError: Provider returned an empty stream with no finish_reason`。

**必须先升级 Python 到 3.12+。** 用户机器已通过 uv 安装了 Python 3.12.13：
```
AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe
```

重建 venv 命令：
```bash
uv venv --python 3.12 "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv"
```

## 破坏性变更总览

### v0.14 → v0.15 (Velocity Release, 2026.5.28)
- `session_search` 完全重写（3 种模式，无需 aux-LLM，4500× 更快）
- 移除 Vercel AI Gateway 和 Vercel Sandbox
- xAI 旧模型退役（需 `hermes migrate xai`）

### v0.15 → v0.16 (Surface Release, 2026.6.5)
- 🖥️ **原生桌面 App**（Windows/macOS/Linux，简体中文 UI）
- 🌐 **Web Dashboard** 管理面板
- `/undo [N]` 撤回对话
- 默认 Skill 集精简（部分需手动装回）
- ⚠️ **Python 3.11 Bug**（Issue #42810，未修复）

### v0.16 → v0.17 (Reach Release, 2026.6.19)
- 🔥 **memory 工具原子批量操作**（add/replace/remove 一次调用）
- 🔥 **Automation Blueprints**（对话式创建 cron）
- 🔥 **后台异步子代理**（`delegate_task(background=true)`）
- **send_message 工具移除**（cron 若用了需改写）
- Curator consolidation 默认关闭
- 桌面端增强（快捷键、通知、VS Code 主题、子代理观察窗）
- Skills Hub 预览+安全扫描
- 新模型：GLM-5.2(1M ctx)、Claude Fable 5、Cursor Composer

## 升级步骤

```bash
# 1. 备份
hermes backup

# 2. 停止 gateway
hermes gateway stop

# 3. 确认 Python 3.12（必须！）
python --version  # 应显示 3.12.x

# 4. 重建 venv（如未做）
uv venv --python 3.12 "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv"

# 5. 升级（editable install）
cd "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
git stash && git checkout main && git pull origin main
uv pip install -e ".[all]"

# 6. 配置迁移
hermes config check && hermes config migrate

# 7. 验证
hermes --version && hermes doctor

# 8. 重启
hermes gateway start && hermes gateway status
```

## 🚨 网关中断死锁（2026.6.21 实战教训）

**无法通过微信通道升级 Hermes。** 原因：

```
我发 "确认执行吗？" → 你确认 → 我准备执行 gateway stop
→ ⚡ 网关此时重启（6月16日同一天 7 次 auto-resume）
→ 执行窗口丢失 → 你沉默等待 → 手动重启 → 死循环
```

累计 429 次 iLink rate limit + 网关间歇性重启 = 升级命令几乎必然被中断吞掉。

**解决方案：写 `.bat` 脚本，用户双击运行。** 脚本自包含：停止 gateway → git pull → 重装依赖 → config migrate → 启动 gateway。任何一步失败自动回滚。用户全程看窗口输出。

模板见 `templates/upgrade_hermes_0170.bat` 和 `templates/switch_hermes_python312.bat`。

## Git 仓库 "no commits" 状态

Pip editable install 可能留下一个本地无 commit 的 git 仓库（`On branch master, No commits yet`）。`git pull` 会失败。

**处理：**
```bash
git fetch origin
git checkout -B main origin/main   # 强制从远程创建 main 分支
```

不要用 `git pull`，用 `git fetch + git checkout -B`。

## uv venv 相对路径陷阱（Windows + MSYS bash）

`uv venv --python 3.12 ~/AppData/Local/hermes/venv312` 可能在 MSYS bash 下将 `~` 展开失败，导致 venv 创建在相对路径而非绝对路径。

**安全做法：** 使用 Windows 绝对路径 `C:\Users\Administrator\...` 而非 `~/...`。

## Windows 特有注意事项

| 事项 | 说明 |
|:---|:---|
| 文件锁 | 升级前必须关闭所有 `hermes.exe` 进程，否则报 `Another hermes.exe is running` |
| WeChat 插件 | gateway 重启后 5-15 秒自动恢复 |
| 回滚 | `git checkout v2026.5.28` + `pip install -e .` |
| 升级通道 | **不能通过微信**——必须用 .bat 脚本 |

## 已知坑

| 坑 | 状态 | 处理 |
|:---|:---|:---|
| Python 3.11 Bug #42810 | Open | 先升 Python 3.12 |
| `hermes update` uv 失败 #39444 | Open | 设 `VIRTUAL_ENV` 或手动 pip |
| Windows 锁 .exe | 设计如此 | 关进程或用 `--force` |

## 对用户的直接价值

| 功能 | 解决什么痛点 |
|:---|:---|
| memory 批量操作 | memory 1874/2200 快满了，可一次调用来管理 |
| 桌面 App | Windows 原生应用，可跟微信并行使用 |
| Automation Blueprints | 对话创建 cron，不用手写表达式 |
| 后台子代理 | 长任务不阻塞主对话 |
| Dashboard | 图形化配置，不用手改 yaml |

## 信息来源

- [官方 Updating 文档](https://hermes-agent.nousresearch.com/docs/getting-started/updating)
- [v2026.5.28 Release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.5.28)
- [v2026.6.5 Release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.5)
- [v2026.6.19 Release](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.19)
- [Issue #42810 - Python 3.11 Bug](https://github.com/NousResearch/hermes-agent/issues/42810)
- [Issue #39444 - uv update failure](https://github.com/NousResearch/hermes-agent/issues/39444)
