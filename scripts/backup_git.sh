#!/bin/bash
# Hermes 自动备份脚本 — 每天 cron 触发
# 成功：静默退出（无输出、exit 0）
# 失败：输出错误信息（cron agent 自动通过微信通知用户）

set -e

HERMES_DIR="$LOCALAPPDATA/hermes"

cd "$HERMES_DIR" || {
    echo "❌ 备份失败：无法进入目录 $HERMES_DIR"
    exit 1
}

# 暂存所有变更
git add -A

# 提交（如果没有变更则跳过）
if git diff --cached --quiet 2>/dev/null; then
    exit 0  # 无变更，静默退出
fi

git commit -m "auto backup $(date '+%Y-%m-%d %H:%M')" 2>/dev/null

# 推送（这是关键步骤）
if git push 2>&1; then
    exit 0  # 成功，静默
else
    echo "❌ Hermes 备份失败！$(date '+%Y-%m-%d %H:%M')"
    echo "请检查：网络是否连通 / GitHub 凭证是否过期"
    echo "手动验证：cd %LOCALAPPDATA%\\hermes && git push"
    exit 1
fi
