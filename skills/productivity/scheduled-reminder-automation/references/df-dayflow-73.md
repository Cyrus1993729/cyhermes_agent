# Dayflow dayflow/ 脚本目录实照（2026-11-18 只读取证）

## 实际绝对路径解析
- HERMES_HOME = `C:\Users\Administrator\AppData\Local\hermes`（由 hermes_constants.get_hermes_home() 确认，非用户主目录 ~）
- jobs.json 相对 script `dayflow/df_watch.py` → 实跑路径 = `C:\Users\Administrator\AppData\Local\hermes\scripts\dayflow\df_watch.py`

## 任务「日程心跳-变更与提前15分提醒」(id=1b3cca2ebcd9)
- schedule: interval 5m, enabled, no_agent=true, deliver=local
- jobs.json 的 last_run=null（无参考价值）
- executions.db：job_id=1b3cca2ebcd9 共 552 次全部 completed（error=None）；最近一次 2026-11-18 16:09:17 → 16:09:18 completed；外部问的 15:57 成功对应 15:57:16.480→15:57:16.989
- 心跳实跑的是 `df_watch.py`（6447B, mtime 2026-10-21 10:02），**不是** `df_watch73.py`

## scripts/dayflow/ 同目录文件（11-18 实况）
- `df_watch73.py`（5258B, 11-18 15:36）、`df_reminders73.py`（14651B, 11-18 15:35）、`RECEIPT_73.json`（3289B, 11-18 15:57）、`HASHES_73.txt`（795B, 15:40）、`README_73.md`（3959B, 15:39）均存在
- 同目录还有旧版：df_common.py / df_evening.py / df_handoff.py / df_morning.py / df_snapshot.py / df_watch.py（10-21 mtime）
- 子目录：backup_73/、tests73/、__pycache__

## cron 数据目录实况
- `cron/jobs.json`（18 个任务：14 no_agent / 4 agent）+ 历次 .bak 备份
- `cron/executions.db` 表：executions（id, job_id, source, process_id, pid, process_started_at, status, claimed_at, started_at, finished_at, error, handoff_pending, handoff_started_at）、cron_incidents
- 结论模式：73 后缀文件在同目录存在但未被心跳任务引用，属备份/演练产物；查任务真正跑的是哪个文件，以 jobs.json 的 script 字段 + scheduler 解析规则为准

注意：此为单次只读快照，mtime/字节数会随更新漂移，用 `ls -la` 现查，不要照抄。
