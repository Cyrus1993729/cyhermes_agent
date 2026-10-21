#!/usr/bin/env bash
# 钉钉 device-flow 授权链接投递前校验（git-bash/MSYS 可用）
# 用法: verify-auth-url.sh <本轮 stderr 日志> <待发正文文件> [本轮进程启动时刻 HH:MM:SS]
# 退出码: 0 = 可发; 1 = 不通过（逐项打印原因）
set -u
LOG=${1:?需要 stderr 日志路径}
MSG=${2:?需要待发正文文件}
START=${3:-}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
fail=0

# 1) 新鲜度：日志 mtime 必须晚于本轮启动
if [ -n "$START" ]; then
  MT=$(stat -c '%y' "$LOG" | cut -d' ' -f2 | cut -d'.' -f1)
  echo "log_mtime=$MT  round_start=$START"
  [ "$(echo -e "$MT\n$START" | sort | tail -1)" = "$MT" ] || { echo "FAIL 日志 mtime 不晚于本轮启动，可能是旧链接"; fail=1; }
fi

# 2) URL 原样：日志与正文里第一条 verify.htm 必须逐字节一致
PAT='https://login\.dingtalk\.com/oauth2/device/verify\.htm?[^[:space:]]*'
grep -o "$PAT" "$LOG" | head -1 > "$TMP/url-log"
grep -o "$PAT" "$MSG" | head -1 > "$TMP/url-sent"
if [ ! -s "$TMP/url-log" ] || [ ! -s "$TMP/url-sent" ]; then
  echo "FAIL 日志或正文里没抓到 verify.htm URL"; fail=1
else
  echo "log_url_len=$(wc -c < "$TMP/url-log")  msg_url_len=$(wc -c < "$TMP/url-sent")"
  if diff -q "$TMP/url-log" "$TMP/url-sent" >/dev/null; then echo "URL_IDENTICAL=YES"; else echo "FAIL URL 不一致（被改写/丢参数）"; fail=1; fi
  grep -q 'user_code=' "$TMP/url-sent" || { echo "FAIL 正文里的是无 user_code 的『手动输入』链接，换个 URL"; fail=1; }
fi

# 3) ANSI/控制字符必须为 0
n=$(grep -c $'\033' "$MSG" || true)
echo "ansi_in_msg=$n"
[ "$n" = "0" ] || { echo "FAIL 正文含 ANSI 转义字符"; fail=1; }

# 4) 脱敏打印日志头（贴给对端 agent 用，不含真码/真链）
echo '--- log head (sanitized) ---'
head -12 "$LOG" | sed -E 's/[A-Z0-9]{4}-[A-Z0-9]{4}/<CODE>/g; s/(user_code=)[^& ]+/\1<CODE>/g; s#(callerUmt=)[^& ]+#\1<REDACTED>#g; s#(verify\.htm\?)[^ ]*#\1<REDACTED>#g'

exit $fail
