@echo off
chcp 65001 >nul
REM ============================================================
REM  服务启动脚本模板（本地部署用）
REM  手动双击运行 或 由 Windows 计划任务定时调用
REM  用法：复制到服务根目录，改项目路径/命令；密钥放同目录 run_secrets.bat
REM ============================================================

REM 清空 Hermes 注入的 PYTHONPATH（防止子进程导错包）
set PYTHONPATH=

REM 加载密钥（token / key 等，独立文件，已 gitignore）
call "%~dp0run_secrets.bat"

REM 进入项目目录
cd /d "%~dp0"

REM 确保日志目录存在
if not exist "output\logs" mkdir "output\logs"

REM 运行（输出追加到日志，含时间戳）
echo [%date% %time%] ===== 服务开始运行 ===== >> "output\logs\run.log"
uv run python -m <module> >> "output\logs\run.log" 2>&1
echo [%date% %time%] ===== 服务运行结束（退出码 %errorlevel%）===== >> "output\logs\run.log"
