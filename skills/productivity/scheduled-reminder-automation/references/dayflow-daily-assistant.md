# Dayflow 日程助手实例（2026-10-21 牛来端落地）

用户诉求：每天提醒当天安排、事项开始前 15 分钟提醒、每晚收尾复盘、钉钉新增安排自动同步后重发当天日程。全部走微信。

## 组成

脚本目录 `~/AppData/Local/hermes/scripts/dayflow/`：

- `df_common.py` 公共库：client 调用、send（微信优先→Telegram 兜底）、快照读写、今日消息组装、提醒去重
- `df_morning.py` 07:30 今日全貌
- `df_watch.py` 每 5 分钟：变更检测 + 开始前 15 分钟提醒
- `df_evening.py` 21:30 收尾（编号→事项映射落 `evening_<date>.json`）
- `df_snapshot.py` 对话中改完日程后刷新快照，避免心跳重复推「已更新」
- `test_df.py` 离线自检（dry，不写云端不发消息）

cron（均 `no_agent=true` + `deliver=local`，脚本自己发微信）：

- 日程早报-0730 `30 7 * * *`
- 日程心跳-变更与提前15分提醒 `5m`
- 日程收尾-2130 `30 21 * * *`

状态目录 `~/AppData/Local/hermes/state/dayflow/`：`snapshot_<date>.json`、`reminded_<date>.json`、`evening_<date>.json`、`delivery.log`；保留 14 天自动清理。

## 变更检测的取舍

快照过期才拉云端，diff 出新增/取消/改期 → 推**完整版**今日日程 + `【变动】` 摘要。
只发「新增了一条 15:00 的会」不够用：用户看不出来是否撞了别的安排。
同一窗口内多个变更合并成一条，避免上游一次同步来三条就刷三屏。

## Dayflow API 字段实测

- `Item.status`: `pending|partial|completed|cancelled`；`mode`: `binary|progress`；`source`: `manual|hermes|dingtalk|mail`
- `executions[]`: `{date, minutes, status}`，`actualMinutes = sum(minutes)`；写 execution 会同步 item.status
- `client review`: body `{date, text, reviewVersion?}`，同一 date 视为更新（带版本校验）
- `client patch`: 必须带当前 `version`，否则 `version_conflict 事项已发生变化`
- 同一 `--request-id` 重试返回同一 id 且 version 不增 → 幂等可直接复用
- `client due` = `GET /reminders/due`（候选提醒，默认 `settings.reminderMinutes=30`）；`client ack` = `POST /reminders/ack`。日提醒未依赖它，改为脚本自算窗口，不猜云端语义。
- 分类 ID 先读 `state` 取真实值，不发明固定目录。

## 坑

- `home.mjs --help` 返回 `Unknown deployment operation`，帮助用 `client --help`。
- `client items` 输出是单个 JSON 数组，直接解析；解析前 strip BOM。
- 钉钉/邮件同步由 Windows 计划任务每 15 分钟驱动（`runtime/.local/calendar-automation.json` 的 `intervalMinutes`），**不是 Hermes cron**；不要重复造同步任务，只做「同步坏了告警」。
- 客户端 home.mjs 自己读受保护连接配置并在内存中使用密钥，脚本只调它，绝不把密钥写进参数或日志。
