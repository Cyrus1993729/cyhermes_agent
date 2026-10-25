# 邮件 → 日程 链路排查（2026-10-24 实测）

场景：早报推了今天 08:25 的团建，用户回“最新邮件已通知改期了呀”。
结论：**邮件采集正常，是落地环节断了**。采集器只把邮件写进缓存，永远不会改云端事项；早报读云端主库，所以照样推旧日期。

## 1. 先确认采集任务在跑

```bash
powershell -NoProfile -Command "\$t=Get-ScheduledTask -TaskName 'Dayflow-Work-Sync'; \$t.Actions | Format-List * | Out-String -Width 300; Get-ScheduledTaskInfo -TaskName 'Dayflow-Work-Sync' | Format-List LastRunTime,LastTaskResult,NextRunTime"
```

- State=Ready；执行链 `wscript.exe /B /NoLogo run-node-hidden.vbs node24 node.exe deployment/home-task.mjs`
- LastRunTime 与 NextRunTime 差约 1 分钟 ⇒ **每分钟**轮询（不是 15 分钟）
- LastTaskResult=0 ⇒ 上一轮成功

> `schtasks /query /fo LIST | grep ...` 在本机输出是 UTF-16，grep 只回 `Binary file matches`，别走这条路，用上面的 PowerShell。

## 2. 邮件落在哪

`C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/runtime/.local/mail-cache/*.json`

```json
{"sourceId":"99e847dd-...","collectedAt":"2026-10-24T01:22:32Z",
 "input":{"subject":"...","receivedAt":"2026-10-23T06:26:22Z","body":"<markdown>", ...}}
```

- 文件 mtime ≈ 本轮重写时间，**不是**收信时间；判新旧看 `input.receivedAt`（UTC，+8 才是北京时间）。
- 采集窗口默认回看 30 天（`mail-collector.mjs` 的 `full=true`），排除已删除/垃圾箱类 folderId。
- 同目录 `work-automation-status.json` 有本轮 startedAt/finishedAt/error；`hermes-client-diagnostics.jsonl` 是写请求耗时日志。

## 3. 按关键词找邮件

```bash
cd "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/runtime/.local/mail-cache" && python -c "
import json,glob
for f in glob.glob('*.json'):
    try: d=json.load(open(f,encoding='utf-8'))['input']
    except Exception: continue
    if '团建' in (d.get('subject','')+d.get('body','')):
        print(d.get('receivedAt'), d.get('subject'))
"
```

看最近清单：把条件换成 `d.get('receivedAt','') >= '2026-10-21'`，按 receivedAt 倒序打印。

## 4. 定位云端事项并回写

```bash
node <home.mjs> client items | python -c "
import json,sys
d=json.load(sys.stdin)
for it in sorted(d,key=lambda x:x.get('date','')):
    if '2026-10-24' <= it.get('date','') <= '2026-11-02':
        print(it['date'], it.get('start','') or '--', it['title'],'|',it['status'],'| src=',it['source'],'| id=',it['id'][:8])
"
```

`source` 区分来源：`mail`=邮件、`dingtalk`=钉钉同步、`manual`=手建、`hermes`=助手写入。

回写：`client patch <id> --json-file <绝对路径.json> --request-id <uuid>`，JSON **必须带当前 version**。
实测可改字段：`date` / `start` / `end` / `plannedMinutes` / `sourceLocation` / `notes`。

🔴 `notes` 是**整体覆盖**：旧内容先原样复制进来，再追加一行溯源
`[YYYY-MM-DD 更新] 依据 <发件日期 时间> 邮件《标题》：<改了什么>`。

改完跑 `python "C:/Users/Administrator/AppData/Local/hermes/scripts/dayflow/df_snapshot.py"` 刷新快照。

## 5. 实际案例：一天漏两封

| 邮件（北京时间收信） | 内容 | 云端原状态 | 处理 |
|:--|:--|:--|:--|
| 10-23 14:26《团建活动延期的通知》 | 台风“蔷琵”延期至 10-31（下周六），其余安排不变 | 10-24 08:25–15:30 pending | date→2026-10-31，时间地点不动 |
| 10-23 14:42《结业汇报…【以此邮件为准】》 | 14:30–17:15、14:15 签到、星塘大厦410会议室 | 10-29 14:00–16:35 @党群服务中心 | 改 start/end/plannedMinutes/sourceLocation |

两封都躺在 mail-cache 里没人落地。教训：**同一批邮件可能同时改日期和改时间地点，要逐封核，别改完一封就收工。**

## 6. 不要自动化的部分

- 归属不明的通知（“相关岗位人员、有兴趣可参加”）不要自己排进日程，问一句“你去不去，去我就排上”。
- 采集器本身不写日程；能做的是**收到邮件后主动核一遍“时间/地点/改期”类邮件**，其余只提示。
