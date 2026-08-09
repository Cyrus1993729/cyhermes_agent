# Gateway 异常停止排查 — 完整工作案例 (2026-08)

## 案例：8/5 手动关机强杀网关

### 症状
用户："排查一下消息网关上次异常停止的原因"。网关进程已死，Telegram/微信消息无人响应，
直到 8/6 19:02 才被重新拉起（用户或桌面应用手动启动）。

### 时间线（UTC+8 本地时间）
- 8/3 23:28 网关 pid=1328 启动（`gateway-starts.log`: 1785770850.86）
- 8/5 08:12:53 网关最后心跳（lifecycle_ledger: `last_heartbeat_at=2026-08-05T00:12:53Z`）
- 8/5 08:13:06 Windows Event 1074 **计划外关机**（RuntimeBroker 记录，原因代码 0x0）
- 8/5 08:13:12 Event 6006 干净关机
- 8/5 当天还有两轮计划外重启：10:58、20:44（Event 1074 + 6006/6005 对）
- 8/5 20:56 Hermes 桌面 serve 启动（desktop.log），但网关未自启
- 8/6 19:02 网关 pid=7144 拉起；启动瞬间 lifecycle_ledger 报上一代 UNCLEANLY

### 判定逻辑
`no exit path ran — SIGKILL / OOM / VM death` + `suspected_oom=False` + 无 Python
traceback + 心跳时间与 Event 1074 咬合（差 13 秒）→ **外部强杀（手动关机），非网关故障**。
用户确认："昨天是我自己手动关机过。"

### 隐藏问题（顺带发现）
- **网关无开机自启**：`schtasks` 无 Hermes_Gateway，注册表 Run 无 hermes →
  关机后当天 3 次开机都没恢复。修复方向：`hermes gateway install`（建计划任务）。
- **api_server 平台 fatal**：`API_SERVER_KEY was rejected by the startup guard` —
  config.yaml `api_server.enabled: true` 但 `.env` 中无 `API_SERVER_KEY`（grep 计数 0）。
  安全守卫拒绝启动无强密钥的 HTTP API 平台。不影响 Telegram/微信。处理选项：
  不用就 `enabled: false`；要用就 `openssl rand -hex 32` 写入 .env。

### Pitfall：terminal 里查 Hermes 版本
`python -m hermes_cli.main --version`（venv）会触发 `cron/lifecycle_guard.py` 误判并抛
`ValueError: open: embedded null character in path`（terminal 工具内部报错）。
查版本/源码状态改用：
```bash
cd $HERMES_HOME/hermes-agent && git log -1 --format="%ci %h %s" && grep -m1 version pyproject.toml
```
（注意 pyproject.toml 版本号可能滞后于代码：本地代码已是 8/3 v0.20 commit，但 version 仍写 0.19.1。）

## 排查命令速查
见 SKILL.md 主体 "Gateway Process Died" 一节（lifecycle_ledger → exit-diag → starts.log →
gateway_state.json → Windows 事件日志 1074/6005/6006/6008/41 → 自启检查）。
