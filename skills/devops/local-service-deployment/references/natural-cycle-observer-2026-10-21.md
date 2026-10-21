# 自然轮次验收观察器实录（2026-10-21，Dayflow home / 61号 HD.4）

## 需求原文要点（协调端 A2A 下达）
- 安装首轮（manual 安装时那一次 run）**不计入**；只统计其后 **commands=[] 且 complete 的两个自然 calendar + 两个自然 mail**。
- 相邻两轮 `startedAt` 间隔 **≥14.5 min**（底层 work-runner 的 15 min 节流）。
- 观察器：只读本目录已有观察日志，每 30 s 更新一个脱敏 receipt，**最多 40 min**，不改生产程序/配置/任务，不联网。
- 同一路径已在运行则不重复启动；启动后立即回 PID/启动时间/当前 receipt，**不等 40 min**。
- 禁止：跑 work-runner、调用 `Install-HomeTask`、改任何同步时间戳、发 Telegram、新增长期计划任务。

## 修正的 bug（本次核心）
旧观察器排除的是**云端 WorkRecord.id**（`1ffa1dae…` / `910eb8af…`），而日志里的 `calendar.runId` / `mail.runId` 是**本地 runId**（`6cdc7774-eee7-4dca-98b7-ea19316e26ce` / `7f54e822-a013-46b1-816b-2f154a5038d8`）。两套 ID 不同命名空间 → 排除失效 → 安装首轮被算成第 1 个自然轮 → 只跑到 1 个真自然轮就 `passed:true`。

自证方式：旧 receipt 的 `calendar[0].runId` 就是被排除的那个本地首次 ID，而 `passed` 为 true，说明它被计入了。

## 修正版关键点
```js
const first={calendar:'6cdc7774-…',mail:'7f54e822-…'};           // 本地首次 runId
const baselineVerified=['calendar','mail'].every(kind=>rows.some(r=>
  r.hostId===host && r[kind]?.runId===baseline[kind] && r.backup?.status==='complete'));
const natural=rows.filter(r=>r.hostId===host&&!r.error&&Array.isArray(r.commands)&&r.commands.length===0);
const runs=kind=>[...new Map(natural.filter(r=>r[kind]?.complete===true&&r[kind].runId&&r[kind].runId!==baseline[kind])
  .map(r=>[r[kind].runId,{runId:r[kind].runId,startedAt:r.startedAt,finishedAt:r.finishedAt,complete:true,commands:0}])).values()]
  .sort((a,b)=>a.startedAt.localeCompare(b.startedAt));
const intervalOK=list=>list.length>=2 && Date.parse(list[1].startedAt)-Date.parse(list[0].startedAt)>=14.5*60000;
passed = baselineVerified && intervalOK(calendar) && intervalOK(mail);
```
- 找不齐基线 → `console.error('Local installation baseline not found; acceptance cannot pass'); process.exitCode=3; break`（**不写 passed**）。
- 主循环用 `if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url))` 守卫，便于被 import 做单测（`inspectNatural(rows, baseline)` 纯函数）。
- 每轮写 `.tmp` 再 `fs.renameSync` 原子替换，避免读到半截 JSON。

## 完整观察器源码
见本 skill 同目录产物：`<release>/runtime/.local/observe-home-natural-cycles.mjs`（2508 B，ASCII，UTF-8 无 BOM，md5 `7e3c95bfaa7d7c1bcf40a774cb9b38f3`）。骨架即上文关键点 + 每 30 s `await new Promise(r=>setTimeout(r,30000))`，`passed||timedOut` 时打印并退出（0 / 2），`!baselineVerified` 退出 3。

## 启动与核对（本机实测）

```bash
cd "<release>/runtime/.local"
# 1) 保旧证据（保留 mtime）
cp -p natural-two-cycles.json natural-two-cycles.invalid-first.json
# 2) 写新观察器后自证：md5 + 新旧 ID 断言
grep -c "6cdc7774-eee7-4dca-98b7-ea19316e26ce" observe-home-natural-cycles.mjs   # 1
grep -c "1ffa1dae" observe-home-natural-cycles.mjs                             # 0（旧云 ID 已清）
# 3) 进程去重（必须限定 exe 名！）
powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'node.exe' -and \$_.CommandLine -like '*observe-home-natural-cycles.mjs*' } | Measure-Object).Count"
# 4) 隐藏启动（异步，wscript 会阻塞到 node 退出）
powershell -NoProfile -Command "\$p = Start-Process -FilePath 'C:\Windows\System32\wscript.exe' -ArgumentList '/B','/NoLogo','<release>\runtime\scripts\run-node-hidden.vbs','<tools>\node24\node.exe','<release>\runtime\.local\observe-home-natural-cycles.mjs','<release>\runtime\.local' -WindowStyle Hidden -PassThru; 'wscriptPID=' + \$p.Id + ' start=' + \$p.StartTime.ToString('o')"
# 5) 拿子进程 PID + 读回执
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'node.exe' -and \$_.CommandLine -like '*observe-home-natural-cycles.mjs*' } | ForEach-Object { 'nodePID=' + \$_.ProcessId + ' ppid=' + \$_.ParentProcessId + ' started=' + \$_.CreationDate.ToString('o') }"
cat natural-two-cycles.json
```

本次结果：wscript PID 64040（08:26:57.34 +08:00）→ node24 PID 66068（08:26:57.50），node v24.22.0，工作目录 `runtime/.local`，观察窗口至 09:06:57 本地时间。

## 首轮 receipt 判读（关键）
```json
{ "baselineVerified": true,
  "excludedLocalRunIds": {"calendar":"6cdc7774-…","mail":"7f54e822-…"},
  "passed": false,
  "calendar": [{"runId":"30319cf8-…","startedAt":"2026-10-21T00:16:59.726Z","complete":true,"commands":0}],
  "mail":     [{"runId":"62320099-…","startedAt":"2026-10-21T00:16:59.726Z","complete":true,"commands":0}],
  "timedOut": false }
```
- `passed:false` 在这里是**正确的**：基线被排除后只剩 1 个自然轮。要看的下一个门槛是「00:31:59Z（本地 08:31:59）之后自然启动的第 2 轮」。
- 同时段 calendar/mail 共用同一个 `startedAt` 是正常的（同一轮 run 里两段）。
- 大量 `calendar:null` 的短周期行是 15 min 节流空转，不是故障；`natural` 过滤已经把它们排除。

## 汇报模板（对方按回执读）
审读结论（只读文件 / 只写文件 / 无网络无 spawn / 缺基线 exit 3）→ 证据保全文件名 → 覆盖文件 md5+字节+关键 ID 断言 → 启动前进程数 0 → wscript+node 两级 PID 与启动时间 → 当前 receipt 关键字段（baselineVerified / passed / 两轮列表 / timedOut）→ 下一步（等第 2 个自然轮，不手动触发）。
