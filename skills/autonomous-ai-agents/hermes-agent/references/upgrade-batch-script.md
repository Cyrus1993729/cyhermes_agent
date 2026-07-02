# Hermes Agent 升级批处理脚本模式

## 何时需要批处理脚本

当操作需要 `hermes gateway stop/start`（切断通信通道）时，不能从消息平台会话中执行。编写 `.bat` 脚本供用户双击运行。

## 脚本模板（v5，Claude 审查通过）

```batch
@echo off
chcp 65001 >nul
title Hermes Agent Upgrade (0.X.0 -> 0.Y.0)

set "AGENT_DIR=%LOCALAPPDATA%\hermes\hermes-agent"
set "PYTHON=%AGENT_DIR%\venv\Scripts\python.exe"
set "BACKUP_DIR=%AGENT_DIR%_backup"

REM Safe date for Chinese Windows (avoids spaces/slashes in %date%)
for /f "tokens=1-3 delims=/-. " %%a in ("%date%") do set "SAFE_DATE=%%a%%b%%c"
set "BACKUP_DIR=%BACKUP_DIR%_%SAFE_DATE%"

REM Step 0: Verify + backup
if not exist "%AGENT_DIR%" (echo [FATAL] Directory not found & pause & exit /b 1)
cd /d "%AGENT_DIR%" || (echo [FATAL] Cannot enter directory & pause & exit /b 1)
if not exist "%PYTHON%" (echo [FATAL] Python not found & pause & exit /b 1)
robocopy "%AGENT_DIR%" "%BACKUP_DIR%" /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NJH /NJS
if %errorlevel% geq 8 (echo [FATAL] Backup failed & pause & exit /b 1)

REM Step 1: Stop gateway (PowerShell, NOT Get-Process)
powershell -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*gateway*' }; if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }"

REM Step 2-N: Maintenance steps...

REM Step N: Start gateway
start "Hermes Gateway" /MIN cmd /c cd /d %AGENT_DIR% ^&^& %PYTHON% hermes_cli\main.py gateway run

pause
exit /b 0

:rollback
REM Restore from backup, reinstall, restart
robocopy "%BACKUP_DIR%" "%AGENT_DIR%" /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NJH /NJS
"%PYTHON%" -m pip install -e ".[all]"
start "Hermes Gateway" /MIN cmd /c cd /d %AGENT_DIR% ^&^& %PYTHON% hermes_cli\main.py gateway run
pause
exit /b 1
```

## Claude 审查时发现的常见问题

| 问题 | 错误写法 | 正确写法 |
|:---|:---|:---|
| Gateway 停止无效 | `Get-Process ... \| Where { $_.CommandLine }` | `Get-CimInstance Win32_Process \| Where { $_.CommandLine }` |
| 中文 Windows date | `-m "msg-%date%"` | 用 for /f 提取安全日期 |
| start 嵌套引号 | `cmd /c "cd "path" && "exe""` | `cmd /c cd /d %VAR% ^&^& %EXE%` |
| 备份需管理员 | `/COPYALL` | `/COPY:DAT` |
| 硬编码用户名 | `C:\Users\Administrator\...` | `%LOCALAPPDATA%\...` |
| xcopy 不可靠 | `xcopy src dst /E /I /Q` | `robocopy src dst /E /COPY:DAT /R:1` |
| 2>nul 吞错误 | 全局静默 | 只在非关键命令使用，关键步骤保留错误输出 |
| 延迟展开未用 | `enabledelayedexpansion` 但用 `%var%` | 移除 enabledelayedexpansion |
| 中文编码乱码 | 批处理正文用中文 | chcp 65001 + 全英文 |

## 审查流程

1. 写出脚本 → 保存到 `~/Desktop/script_name.bat`
2. `cat ~/Desktop/script_name.bat | claude -p '审查这个 Windows 批处理脚本...' --model sonnet --max-turns 3`
3. 修复 Claude 发现的问题
4. 第二轮审查（本轮尤为关键——第一轮修复可能引入新问题）
5. 确认零中文字符：`python -c "import re; ..."`
6. 发送 MEDIA 文件给用户
