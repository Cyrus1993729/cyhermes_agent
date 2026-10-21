@echo off
setlocal enabledelayedexpansion
title Hermes venv 切换 (3.11 -> 3.12)

echo ============================================
echo   Hermes Agent - Python 3.12 切换脚本
echo ============================================
echo.
echo   当前: Python 3.11.15 -> 目标: Python 3.12.13
echo.

set "HERMES_HOME=C:\Users\Administrator\AppData\Local\hermes"
set "AGENT_DIR=%HERMES_HOME%\hermes-agent"
set "VENV_OLD=%AGENT_DIR%\venv"
set "VENV_NEW=%HERMES_HOME%\venv312"
set "BACKUP=%AGENT_DIR%\venv_old"

echo [1/4] 停止 Gateway 进程...
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*gateway*'} | ForEach-Object { Write-Host '  停止 PID:' $_.Id; Stop-Process -Id $_.Id -Force }" 2>nul
timeout /t 3 /nobreak >nul
echo   完成

echo.
echo [2/4] 备份旧 venv (Python 3.11)...
if exist "%BACKUP%" (
    echo   删除旧备份...
    rmdir /s /q "%BACKUP%" 2>nul
)
move "%VENV_OLD%" "%BACKUP%" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [失败] 无法备份旧 venv - 可能有文件被占用
    echo   请手动关闭所有 Python 进程后重试
    goto :error
)
echo   已备份 -> venv_old

echo.
echo [3/4] 切换到新 venv (Python 3.12)...
move "%VENV_NEW%" "%VENV_OLD%" >nul 2>&1
if errorlevel 1 (
    echo   [失败] 无法移动新 venv，正在回滚...
    move "%BACKUP%" "%VENV_OLD%" >nul 2>&1
    echo   已回滚到旧 venv
    goto :error
)
echo   完成

echo.
echo [4/4] 验证 + 启动 Gateway...
"%VENV_OLD%\Scripts\python.exe" --version
echo.
echo   启动 Gateway（新窗口，后台运行）...
start "Hermes Gateway" /MIN cmd /c "cd /d "%AGENT_DIR%" && "%VENV_OLD%\Scripts\python.exe" hermes_cli\main.py gateway run"

echo.
echo ============================================
echo   切换成功！
echo.
echo   Python: 3.12.13
echo   Hermes: 0.14.0 (未升级)
echo.
echo   等待 5-15 秒后微信自动恢复连接
echo.
echo   旧 venv 备份: venv_old
echo   (如出问题，把 venv_old 改回 venv 即可回滚)
echo ============================================
pause
exit /b 0

:error
echo.
echo ============================================
echo   切换失败
echo   旧 venv 备份在: venv_old
echo   可手动恢复: 把 venv_old 重命名为 venv
echo ============================================
pause
exit /b 1
