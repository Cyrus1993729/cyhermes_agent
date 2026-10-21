# Hermes Agent 升级指南：v0.14.0 → v0.17.0

## 升级路线

```
v0.14.0 → Python 3.12 → v0.17.0
  │           │              │
  │           └─ 先升 Python（0.16+ 在 3.11 上有 Bug #42810）
  └─────────────┘
```

## 前置条件

### Python 3.12 升级（必须先做）

0.16.0+ 在 Python 3.11 上有 open bug：#42810（API 调用返回 empty stream with no finish_reason）。

**步骤：**
1. 检查已有 Python 3.12：`uv python list | grep 3.12`
2. 创建新 venv：`uv venv --python 3.12 <new_venv_path>`
3. 记录旧包：`pip freeze > old_packages.txt`
4. 安装 hermes-agent（保持旧版本）：`cd <repo> && uv pip install -e ".[all]" --python <new_venv>/python.exe`
5. 批装旧包：`grep -v "^-e " old_packages.txt | cut -d= -f1 > pkgs.txt && uv pip install -r pkgs.txt --python <new_venv>/python.exe`
6. 重新挂 editable：`uv pip install -e ".[all]" --python <new_venv>/python.exe`
7. 验证关键包：faster-whisper, akshare, yfinance, rapidocr, playwright, imageio-ffmpeg, openai
8. 验证核心：`from run_agent import AIAgent; from hermes_constants import get_hermes_home`

**不能通过网络消息执行 venv 切换。** 需用 `.bat` 脚本（见下文）。

## 升级脚本模式

### 为什么需要 .bat 脚本

通过微信/Telegram 等消息平台执行 `gateway stop` 存在逻辑悖论：
- 执行 stop 后通信通道断开
- 如果后续 start 失败，agent 活着但不可达
- "确认→执行" 的 round-trip 窗口可能被网关中断吞掉上下文

### 脚本模板要点

```batch
@echo off
chcp 65001 >nul
title Hermes Agent Upgrade (0.14.0 -> 0.17.0)

set "AGENT_DIR=%LOCALAPPDATA%\hermes\hermes-agent"
set "PYTHON=%AGENT_DIR%\venv\Scripts\python.exe"
set "BACKUP_DIR=%AGENT_DIR%_backup"

REM 安全日期（中文 Windows 上 %date% 含空格）
for /f "tokens=1-3 delims=/-. " %%a in ("%date%") do set "SAFE_DATE=%%a%%b%%c"
set "BACKUP_DIR=%BACKUP_DIR%_%SAFE_DATE%"

REM 1. 验证 + 备份（robocopy，非 xcopy）
robocopy "%AGENT_DIR%" "%BACKUP_DIR%" /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NJH /NJS 2>nul
if %errorlevel% geq 8 goto :rollback

REM 2. 停止 Gateway（Get-CimInstance，非 Get-Process）
powershell -Command "$procs = Get-CimInstance Win32_Process | Where-Object { ... -like '*gateway*' } | ... Stop-Process ..."

REM 3. git fetch + checkout
git fetch origin && git checkout -B main origin/main || goto :rollback

REM 4. 安装依赖
"%PYTHON%" -m pip install -e ".[all]" || goto :rollback

REM 5. 配置迁移
"%PYTHON%" hermes_cli\main.py config check
echo y | "%PYTHON%" hermes_cli\main.py config migrate

REM 6. 启动 Gateway
start "Hermes Gateway" /MIN cmd /c cd /d %AGENT_DIR% ^&^& %PYTHON% hermes_cli\main.py gateway run

:rollback
robocopy "%BACKUP_DIR%" "%AGENT_DIR%" /E /COPY:DAT ...
```

### 常见坑

1. **中文编码**：cmd.exe 默认 GBK，中文 `echo` 会乱码。加 `chcp 65001` 或全用英文。
2. **`Get-Process` 无 `CommandLine` 属性**：必须用 `Get-CimInstance Win32_Process`。
3. **`%date%` 含空格和斜杠**：中文 Windows 格式为 `2026/06/21 周六`，会破坏 git 命令。用 `for /f` 提取。
4. **`start` 命令嵌套引号**：变量用 `set "VAR=..."` 定义后直接 `%VAR%` 展开，不加额外引号。
5. **`/COPYALL` 需管理员权限**：改用 `/COPY:DAT`。
6. **版本号残留**：重写脚本后检查 `echo` 语句里的版本标签，别留 `v4` 在 `v5` 脚本里。

### Claude 审查检查清单

提交脚本前用 Claude (`--model sonnet`) 逐项检查：
1. Gateway 进程能否正确识别并停止？（Get-CimInstance vs Get-Process）
2. `cd` 失败后脚本是否继续执行？
3. `%date%` 在中文 Windows 上是否安全？
4. PowerShell 通配符是否加了引号？
5. 关键错误是否被 `2>nul` 吞掉？
6. 路径是否硬编码用户名？（应用 `%LOCALAPPDATA%`）
7. 备份是否用 robocopy（非 xcopy）？
8. `start` 命令是否有嵌套引号问题？

## Git 仓库修复

如果本地 git 仓库损坏（object 缺失、fetch 失败）：
```bash
cd ~/AppData/Local/hermes/hermes-agent
rm -rf .git
git init
git remote add origin https://github.com/NousResearch/hermes-agent.git
git fetch --depth 1 origin main
git checkout -f FETCH_HEAD
git checkout -b main
```

浅克隆 (`--depth 1`) 避免下载完整历史。

## 升级后验证

```bash
grep "^version" pyproject.toml    # 应为 0.17.0
git log --oneline -1              # 确认 commit
python -c "from run_agent import AIAgent; print('OK')"
hermes config check
hermes gateway status
```

## v0.17.0 send_message 移除影响

`send_message` 工具在 0.17.0 中从 agent 工具箱移除。受影响的 skill：
- `xiaohongshu-analysis`：微信发送步骤需改用普通回复 + gateway 自动送达
- `yuanbao`：元宝消息发送功能失效

修复方式：升级后让 agent 读取 0.17.0 的消息发送机制，修改对应 SKILL.md 中的发送步骤。

## iLink 微信限流

住宅 IP 低频账号可能遇到 `iLink sendmessage rate limited: ret=-2`。诱因：
- 多段消息密集发送（如 6 段分析报告在 2 秒内连续发出）
- 消息 + MEDIA 文件快速连续发送

v0.17.0 未完全解决此问题。缓解措施：减少分段数（每段更少但更长），段间留自然间隔。
