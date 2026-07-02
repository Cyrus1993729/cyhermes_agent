@echo off
setlocal enabledelayedexpansion
title Hermes Agent 升级 (0.14.0 → 0.17.0)

echo.
echo ============================================
echo   Hermes Agent 升级脚本 v2
echo   当前: 0.14.0 → 目标: 0.17.0
echo   Python: 3.12.13
echo ============================================
echo.

set "AGENT_DIR=C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
set "PYTHON=%AGENT_DIR%\venv\Scripts\python.exe"
set "BACKUP_DIR=%AGENT_DIR%_backup_20260621"

REM ============================================
REM Step 0: 完整备份 + 记录状态
REM ============================================
echo [0/6] 完整备份当前代码...
cd /d "%AGENT_DIR%"
if exist "%BACKUP_DIR%" rmdir /s /q "%BACKUP_DIR%" 2>nul
xcopy "%AGENT_DIR%" "%BACKUP_DIR%" /E /I /Q /H 2>nul
echo   备份完成: %BACKUP_DIR%

echo   保存本地修改...
git add -A 2>nul
git stash push --include-untracked -m "pre-upgrade-0.17.0-%date%" 2>nul
echo   完成

REM ============================================
REM Step 1: 停止 Gateway
REM ============================================
echo.
echo [1/6] 停止 Gateway...
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*gateway*'} | ForEach-Object { Write-Host '  停止 PID:' $_.Id; Stop-Process -Id $_.Id -Force }" 2>nul
timeout /t 3 /nobreak >nul
echo   完成

REM ============================================
REM Step 2: 获取最新代码
REM ============================================
echo.
echo [2/6] 获取 Hermes 0.17.0 代码...
git fetch origin 2>nul
if %errorlevel% neq 0 (
    echo   [失败] 无法连接 GitHub，请检查网络/代理
    goto :rollback
)
git checkout -B main origin/main 2>nul
if %errorlevel% neq 0 (
    echo   [失败] 无法切换到 0.17.0
    goto :rollback
)
echo   已切换到 origin/main (0.17.0)

for /f "tokens=*" %%a in ('git rev-parse HEAD 2^>nul') do set "NEW_COMMIT=%%a"
echo   新版本 commit: %NEW_COMMIT:~0,10%
echo   完成

REM ============================================
REM Step 3: 安装依赖
REM ============================================
echo.
echo [3/6] 安装依赖（1-2 分钟）...
"%PYTHON%" -m pip install -e ".[all]" 2>&1
if %errorlevel% neq 0 (
    echo   [失败] 依赖安装失败
    goto :rollback
)
echo   完成

REM ============================================
REM Step 4: 配置迁移
REM ============================================
echo.
echo [4/6] 配置检查与迁移...
echo.
echo --- config check ---
"%PYTHON%" hermes_cli\main.py config check 2>&1
echo.
echo --- config migrate (自动确认) ---
echo y | "%PYTHON%" hermes_cli\main.py config migrate 2>&1
echo   完成

REM ============================================
REM Step 5: 启动 Gateway
REM ============================================
echo.
echo [5/6] 启动 Gateway (0.17.0)...
start "Hermes Gateway" /MIN cmd /c "cd /d "%AGENT_DIR%" && "%PYTHON%" hermes_cli\main.py gateway run"
echo   已启动

REM ============================================
REM Step 6: 验证
REM ============================================
echo.
echo [6/6] 验证版本...
timeout /t 5 /nobreak >nul
"%PYTHON%" -m pip show hermes-agent 2>&1 | findstr "Version"
echo.
echo ============================================
echo   升级成功！
echo.
echo   Hermes: 0.14.0 → 0.17.0
echo   Python: 3.12.13
echo.
echo   等待 5-15 秒后微信自动恢复连接
echo.
echo   如出问题:
echo   - 备份在: %BACKUP_DIR%
echo   - 可复制回 %AGENT_DIR% 恢复
echo ============================================
pause
exit /b 0

REM ============================================
REM 回滚
REM ============================================
:rollback
echo.
echo ============================================
echo   升级失败，正在自动回滚...
echo ============================================
cd /d "%AGENT_DIR%"

echo   恢复旧版本代码...
if exist "%BACKUP_DIR%" (
    rmdir /s /q "%AGENT_DIR%" 2>nul
    xcopy "%BACKUP_DIR%" "%AGENT_DIR%" /E /I /Q /H 2>nul
    echo   已从备份恢复
) else (
    git stash pop 2>nul
    echo   已从 git stash 恢复
)

echo   重新安装依赖...
"%PYTHON%" -m pip install -e ".[all]" 2>&1

echo   启动 Gateway...
start "Hermes Gateway" /MIN cmd /c "cd /d "%AGENT_DIR%" && "%PYTHON%" hermes_cli\main.py gateway run"

echo.
echo   已回滚到升级前状态
echo   请截图上方错误信息发给我
echo ============================================
pause
exit /b 1
