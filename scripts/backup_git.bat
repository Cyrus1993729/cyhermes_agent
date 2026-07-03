@echo off
chcp 65001 >nul
cd /d "%LOCALAPPDATA%\hermes"
git add -A
git diff --cached --quiet
if %errorlevel% equ 0 exit /b 0
git commit -m "auto backup %date% %time%" >nul 2>&1
git push 2>&1
if %errorlevel% neq 0 (
    echo ❌ Hermes backup failed! %date% %time%
    echo Check network / GitHub credentials
    echo Manual: cd %%LOCALAPPDATA%%\hermes && git push
    exit /b 1
)
