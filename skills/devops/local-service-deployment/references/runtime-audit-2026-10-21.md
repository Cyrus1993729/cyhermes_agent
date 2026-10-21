# 启用后运行期只读审计（Dayflow Home 同步，2026-10-21 实案）

背景：协调端/用户的 activate 回执超时，要求「只读核查一次、立即回执、不重复 activate / Install-HomeTask / work-runner」。
根目录：`C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1`

## 一、状态文件字段映射（最容易误判的地方）

| 想要的信息 | 真实出处 | 说明 |
|---|---|---|
| `calendar.complete` / `mail.complete` / `mail.observed` / `bodyFailures` | `runtime/.local/work-automation-observation.jsonl` 里带 `mail` 字段的那一行 | 每轮 append 一行；只有真正执行了 calendar/mail/backup 的那轮才带这些键 |
| `backup.status` / `bytes` / `sha256` / `counts` / `drill` | 同上那行的 `backup` 对象；旁证 `automatic-backups/dayflow-*.json` 与 `restore-drill-2026-10.json` | drill 在 backup 成功后同轮跑 |
| `lastCalendar` / `lastMail` / `lastMailFull` / `lastBackup` / `backupAttemptAt` | `runtime/.local/work-host.json` | 节流用的游标 |
| 本轮 error / 是否跑完 | `runtime/.local/work-automation-status.json`（`{startedAt,hostId,calendar,commands,error,finishedAt}`） | **不含** complete/backup/drill 字段，别拿它判成败 |
| 激活态 | `runtime/.local/home-enabled.json`（`pause` 会改名 `home-disabled-<ts>.json`） | `homeId/bundleId/oldHostId/oldWriterStopped/issuedAt/expiresAt/activatedAt` |

## 二、节流阈值（来自 `runtime/scripts/work-runner.mjs`，实读代码确认）

- calendar 与 mail：`!lastX || now - lastX >= 15*60000` 才跑
- backup：`lastBackup !== 北京日期` 且距 `backupAttemptAt` > 15 min
- 因此「每 1 分钟的计划任务」绝大多数轮次是空转：`{calendar:null, commands:[], error:null}`，**不是失败**。
- `home.mjs run` 守卫只校验 `homeId/bundleId/oldWriterStopped`；`expiresAt` 过期不影响运行（只在 `activate` 校验 permit）。

## 三、计划任务探针（.ps1，规避 bash 吃 `$`）

写 `C:/Users/Administrator/AppData/Local/Temp/df_sched_check.ps1`：

```powershell
$ErrorActionPreference = 'SilentlyContinue'
$t = Get-ScheduledTask -TaskName 'Dayflow-Work-Sync'
if (-not $t) { 'TASK_MISSING'; exit 0 }
$i = Get-ScheduledTaskInfo -TaskName 'Dayflow-Work-Sync'
'TASK=' + $t.TaskName
'ENABLED=' + $t.Settings.Enabled
'STATE=' + $t.State
'LASTRUN=' + $i.LastRunTime
'LASTRESULT=' + $i.LastTaskResult
'NEXTRUN=' + $i.NextRunTime
'NUMBEROFMISSEDRUNS=' + $i.NumberOfMissedRuns
foreach ($a in $t.Actions) {
  'ACTION_EXE=' + $a.Execute
  'ACTION_ARGS=' + $a.Arguments
  'ACTION_WD=' + $a.WorkingDirectory
}
foreach ($g in $t.Triggers) {
  $cls = $g.CimClass.CimClassName
  'TRIGGER=' + $cls
  if ($cls -match 'Logon') { '  ATLOGON=true' }
  if ($g.StartBoundary) { '  START=' + $g.StartBoundary }
  if ($g.Repetition) {
    '  REP_INTERVAL=' + $g.Repetition.Interval
    '  REP_DURATION=' + $g.Repetition.Duration
    '  STOPATDURATION=' + $g.Repetition.StopAtDurationEnd
  }
}
```

调用：`powershell -NoProfile -ExecutionPolicy Bypass -File 'C:/Users/Administrator/AppData/Local/Temp/df_sched_check.ps1'`

本次结果：`ENABLED=True / STATE=Ready→Running / LASTRESULT=0 / MissedRuns=0`；
Action = `wscript.exe` + `/B /NoLogo "…runtime\scripts\run-node-hidden.vbs" "…tools\node24\node.exe" "…deployment\home-task.mjs" "<release>"`；
Trigger = `MSFT_TaskTimeTrigger`（`PT1M`、StopAtDurationEnd=True）+ `MSFT_TaskLogonTrigger`。

## 四、进程面

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'powershell|pwsh|node|wscript' -and $_.CommandLine -match 'Install-HomeTask|Initialize-Home|work-runner|activate' } | Select-Object ProcessId,CreationDate,Name,CommandLine | Format-List
```

无输出 = 安装器/运行器都没在跑（本次 `install-hometask.log` 末尾即 `{"finished":true}`）。
过滤到 `home.mjs client state` 之类只读子进程时，注明「另一会话并发只读，非本核查发起」。

## 五、回执形态（对方按回执读结论）

1) 激活标记（homeId/bundleId + 时间戳 + `expiresAt` 过期的无害性说明，声明无 signature 回传）
2) 任务（存在/Enabled/State/LastRun/LastTaskResult/NextRun/MissedRuns + Action 前后路径 + Trigger）
3) status（enabled、runnerLock、lastCalendar/lastMail、**首条完整 observation 的分段计数**、最近几条空转的节流解释）
4) 字段出处更正 + 安装进程状况 + 一句「等你给下一步，不自行恢复旧端」。

不写任何文件、不调 activate/install/run —— 只 `status` 一条命令 + 两份 PowerShell 只读查询。
