# 云端备份直取 + 内存演练（实测：69 号读取器兼容验收）

对端请求形状（A2A）：

> 用当前活动 release 及已有私有连接 GET /api/v1/backup，**只把响应留在内存**；
> 调 `runtime/scripts/work-backup.mjs` 导出的 `isolatedBackupDrill(backup)`，在内存 SQLite 做空库与非空恢复核对；
> 绝不调云端 restore、POST 或改云端业务；返回 HTTP 状态、SHA256/字节数、items/goals/reviews/coach/work 条数、
> requiredFeatures、drill 脱敏结果，以及同步任务 Enabled/LastResult 与最近 calendar/mail 成功时间。

## 最大坑：403 不是你被拒，是传输层指纹

第一版用 `await fetch(new URL('/api/v1/backup', cfg.url), {headers:{Authorization:'Bearer '+cfg.key}})`：

```json
{"httpStatus":403,"contentType":"text/html; charset=UTF-8",
 "headers":{"server":"cloudflare","cf-ray":"a553894e…-LAX"}}
```

关键取证（决定不要误判）：同一把 key、同一时刻打**已知可用的** `/api/v1/state` 和
`/api/v1/sync/work/status`，**也是 403 HTML**。而 `runtime/.local/work-automation-observation.jsonl`
末行显示那一分钟任务刚跑完 `error:null`、云端调用全 2xx。⇒ 边缘层（Cloudflare）在挡 Node/undici 的
TLS 指纹，与 key、路由、服务健康无关。

正解：**用 release 自己那份传输层**，它本来就是产品跑通的那条路——
`runtime/scripts/http-request.mjs` 在 `process.platform==='win32'` 时
`spawn('pwsh',['-NoLogo','-NoProfile','-NonInteractive','-File','http-request.ps1'])`，请求从子进程 stdin 进；
只有非 Windows 才走 `fetch`。改造后：

```
{"path":"/api/v1/sync/work/status","status":200,"bytes":33078}
{"path":"/api/v1/backup","status":200,"bytes":302539}
```

包装要点：`spawn('pwsh')` 走 PATH ⇒ 先把 `<root>/tools/pwsh7` 前置；`httpRequest` 的返回是
`{status, body, headers}`（body 是字符串），响应就留在 `body` 变量里，不落盘。

## 备份结构与计数口径（v5 全量）

`GET /api/v1/backup` 直接给 `dayflow-backup` 全文，不是 transfer 分片（分片那条路是
`backup/transfers/export` + `parts/:index`，只读任务不要碰）。

| 字段 | 位置 |
|---|---|
| items / goals / reviews | `data.*` |
| history / coach / work | 顶层数组 |
| requiredFeatures | 顶层，缺省或 `[]` = 无特性门槛 |
| version / exportedAt / timeZone | 顶层 |

实测：`bytes 302539`、`sha256 bc36528d…659d`、`version 5`、`requiredFeatures []`、
`items 61 / goals 2 / reviews 1 / history 128 / coach 1 / work 139`，`validateBackup` 通过。

## isolatedBackupDrill 到底做了什么（所以不必自己写恢复）

`runtime/scripts/work-backup.mjs` 第 11–13 行：

1. `new DatabaseSync(':memory:')` + `sqliteStorage(native)` ⇒ **真空库**；
2. 建 `planner_state(id,payload,revision)` + `STORAGE_SCHEMA` 全部表；
3. `recoveryPreview(db, backup)` → `controlledRestore(db,{backup,revision,digest,confirm:true},uuid)`；
4. `fullBackup(db)` 回读，对 `data/history/coach/work` 逐段 `isDeepStrictEqual`（不等即
   `isolated restore differs: <field>`）；
5. 再 `recoveryPreview` + 带 `recoveryEpoch` 的二次 `controlledRestore`（幂等/epoch 语义也验了）；
6. 返回 `{at,status:'complete',isolated:true,nonemptyRestore:true,items,records}`。

回执必须**交叉核对** `drill.items == counts.items` 且 `drill.workRecords == counts.work`——
实测 61/139 全等；不等即「恢复丢数据」，比 drill 自己报 complete 更可信。

## 时间戳的两个来源（别写成顺序错乱）

- `exportedAt` = **服务端**写进备份的导出时刻；
- `drill.at` = **本机**时钟。

实测同一次运行：`drill.at 12:12:16Z` 早于 `exportedAt 12:15:14Z`，而本机 `date -u` 当时是 `12:12:39`。
⇒ 服务端时钟比本机快约 2–3 分钟。回执里要标清哪条来自服务端，别据此判「先演练后取备份」。

## 同一份回执要带的运行面

- 任务：`Get-ScheduledTask -TaskName 'Dayflow-Work-Sync'` 的 `Settings.Enabled`（真值，别用 State 反推）、
  `State`、`Get-ScheduledTaskInfo` 的 `LastTaskResult`（`267009`=实例在跑，不是失败）、`LastRunTime`(UTC)、`NextRunTime`；
- 最近同步成功：`runtime/.local/work-host.json` 的 `lastCalendar` / `lastMail` / `lastMailFull`，
  再配 observation 里**最后一条 `calendar` 非空**的行（实测 `11:55:58.819Z→11:57:11.787Z`，
  `calendar.complete=true`、`mail.complete=true`、`mail.observed=5`、`bodyFailures=0`、`error=null`）。

## 回执骨架（实测通过）

```json
{"release":"<dir>","endpoint":"GET /api/v1/backup","httpStatus":200,
 "bytes":302539,"sha256":"<64 hex>","format":"dayflow-backup","backupVersion":5,
 "exportedAt":"...","requiredFeatures":[],"valid_newReader":true,
 "counts":{"items":61,"goals":2,"reviews":1,"history":128,"coach":1,"work":139},
 "drill":{"status":"complete","isolated":true,"nonemptyRestore":true,"items":61,"workRecords":139,"at":"..."},
 "workSync":{"task":"Dayflow-Work-Sync","enabled":true,"state":"Running","lastResult":267009,...},
 "lastSync":{"cycleStart":"...","cycleEnd":"...","calendarComplete":true,"mailComplete":true,...}}
```

末尾必写：只读 GET 次数、响应仅存内存未落盘、未调云端 restore/POST、未改配置或调度、未重启、未重新授权、
未手动触发同步、未发 Telegram；并把 403→传输层切换作为「附带发现」如实披露（对端要脚本化时得走同一条通道）。
