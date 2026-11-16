# Dayflow 家主机（妈妈端）只读预检 —— 可复跑清单

来源：2026-10-22 「66 号补丁」前预检（妈妈端 PC，A2A 对端请求）。全程只读：不暂停调度、不安装、
不改配置/数据、不重启、不删锁。用户自有技能 `dayflow-personal-planner` 管业务写入，这里只管运维侧核对。

## 目录结构（易错）

```
C:/Users/Administrator/AppData/Local/DayflowHome/
  tools/node24/node.exe        # ← Node 在 home 根，release 下没有 tools/
  tools/pwsh7/                 # ← 客户端 spawn('pwsh') 靠这个，调用前前置 PATH
  manifest.json                # 早期根级清单：51 文件（≠ 活动清单）
  releases/sites29-afdf902-home1/
    manifest.json              # ← 活动清单：52 文件
    deployment/home.mjs        # verify / client 入口
    runtime/scripts/hermes-client.mjs
    runtime/.local/            # 私有状态：连接、锁、状态、观测日志
  backup/                      # 预检对照快照放这儿
```

## 1. 活动目录 / homeId / manifest

```bash
R=/c/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1
sha256sum "$R/manifest.json"                       # 只需这一份
NODE="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
cd "$R" && "$NODE" deployment/home.mjs verify
# → {"verified":true,"bundleId":"sites29-afdf902-home1","sourceCommit":"975d8984...","files":52}
```

homeId 看 `runtime/.local/home-deployment.json` 与 `home-enabled.json` 是否一致
（`home-enabled.json` 的 `expiresAt` 是切换窗口，早已过期属正常，看 `activatedAt` 有没有写）。

2026-10-22 基准：活动目录 `releases/sites29-afdf902-home1`（唯一 release）；homeId
`7d4b5206-0989-4ca6-9e29-f817197b6414`；manifest SHA256
`756b3b7eb122e5b868ba031189467e1a456accf2ec13603faa595685d86c4cfe`，52 文件；
sourceCommit `975d8984666fb3a12fa0827915efbdb023502239`；`categoryAPIPatch=category-api-v2`。

## 2. 同步任务 / 锁 / 最近一轮

```bash
powershell -NoProfile -Command "\$t=Get-ScheduledTask -TaskName 'Dayflow-Work-Sync'; \$i=Get-ScheduledTaskInfo -TaskName 'Dayflow-Work-Sync'; 'Enabled='+(\$t.Settings.Enabled); 'State='+\$t.State; 'LastRun='+\$i.LastRunTime.ToString('HH:mm:ss'); 'LastResult='+\$i.LastTaskResult; 'NextRun='+\$i.NextRunTime.ToString('HH:mm:ss')"
cat "$R/runtime/.local/work-sync.lock"    # {"pid":81032,"at":"...Z","token":"..."}
```

- 每分钟一轮（`Repetition=PT1M`；TimeTrigger + LogonTrigger），单轮 20–50 秒。
- **锁由每轮现建现删**，`at` 是本轮开始时刻。判在途：读 pid → `Get-Process -Id <pid>`。
  **不删锁、不停进程**。检查过程中锁消失 = 那轮已正常收尾，不是丢锁。
- 最近一轮：`runtime/.local/work-automation-status.json`（`startedAt/finishedAt/error/commands`）+ `work-automation-observation.jsonl` 末两行。

## 3. 云端 state 只读核对（只回计数）

凭据在 `runtime/.local/hermes-cloud-connection.json`（`url` + `key`，**不外传**）。用子进程 env 传，
key 不出现在命令行/输出里；同时前置 pwsh PATH：

```python
conn = json.load(open(R+'/runtime/.local/hermes-cloud-connection.json'))
env = dict(os.environ, DAYFLOW_URL=conn['url'], DAYFLOW_API_KEY=conn['key'])
env['PATH'] = r'C:\Users\Administrator\AppData\Local\DayflowHome\tools\pwsh7' + ';' + env['PATH']
p = subprocess.run([node, 'runtime/scripts/hermes-client.mjs', 'state'], capture_output=True, text=True, env=env)
d = json.loads(p.stdout)
print({'revision': d['revision'], 'counts': {k: len(d.get(k, [])) for k in ('items','goals','reviews','drafts')},
       'sync': d['sync'], 'bridgeConnected': d['bridgeConnected']})
```

`state` 是 GET，无需 request-id；写入类命令才要 `--request-id`。汇报只给 revision + 四类计数 + `sync.lastSuccess`。
2026-10-22 基准：revision 53817；items 39 / goals 2 / reviews 1 / drafts 0；storageVersion 5；bridgeConnected true。

## 3b. 容量顶格诊断：GET /api/v1/sync/work/health（只读）

触发措辞：「Dayflow 同步容量故障」「同步每分钟报错」「只返回临时运行和主业务字节、run 条数」。

服务端电话就在同一份凭据里，直接走 `Authorization: Bearer <key>`，不必经客户端 spawn（更快、不碰 pwsh PATH）：

```python
import json, subprocess
c = json.load(open(R + '/runtime/.local/hermes-cloud-connection.json', encoding='utf-8'))
r = subprocess.run(['curl', '-s', '--max-time', '30', '-H', 'Authorization: Bearer ' + c['key'],
                    c['url'].rstrip('/') + '/api/v1/sync/work/health'], capture_output=True, text=True)
d = json.loads(r.stdout)
```

key 只经 `-H` 传给子进程，不打印、不出现在回执里；`curl` 在 MSYS 下能用，不必开浏览器。

返回形状（**数组，不是字典**，别按名字取）：

- `bytes[]`：`{label, bytes, limit}` —— 四条 `主业务` / `分析记录` / `来源业务与运行` / `临时运行`
- `counters[]`：`{label, count, limit}` —— 16 条 `事项/复盘/历史/分析及讨论/application/call/candidate/checkpoint/command/decision/event/host/mail/run/setting/source`
- 标量：`at` `revision` `operations` `recordLimit` `attention` `notice`；`backup{bytes,limit,recoverable,revision}`

用法要点：
- 先 `for x in d['bytes']: print(x)` 全量看，再只挑对端要的字段拼回执；**不要把整个 d 丢出去**（counters 带 mail/event 计数、notice 是长文案）。
- 用 `round(used/limit*100,2)` 算占用率，并给 `headroom = limit - bytes` —— 卡顶时余量只有几千字节，光说 99% 看不出「还剩多少」。

### 报错签名对照（实测 2026-11-04 牛来端）

| 现象 | 含义 |
|---|---|
| `LastTaskResult=1` + 每分钟重复 | 进程非零退出，不是「在跑」；Windows 里 0 才是成功 |
| observation `error="工作来源或运行记录超过字节容量"` | 服务端容量保护触发，**每分钟都失败**，`calendar:null`、`commands:[]` 是后果不是原因 |
| `临时运行` 字节 ≈ limit（99.90%，剩 2116 B） | **真正的顶格项**，与上面那句错一一对应 |
| `run` 条数 2042/3000（68%） | 尚未触顶，别当成主因 |
| `主业务` 1,079,272/1,500,000（71.95%） | 仍有余量，别误报成主业务爆了 |

保护语义（服务端 notice 原文要点）：达容量时**停止新增、保留原数据**；正确处置是**先下载完整备份，再缩小处理范围或联系维护**，
日志清理不影响业务历史与用户决定。→ 只读任务里**不要**自行删日志/清 run、不要改配置、不要触发任务。

2026-11-04 基准：revision 97248，operations 16701 / recordLimit 20000，attention=true；
临时运行 2,095,036/2,097,152；主业务 1,079,272/1,500,000；来源业务与运行 2,215,709/12,582,912；run 2042/3000。

## 4. 安装前对照快照（本机私有）

`DayflowHome/backup/preflight-66-<YYYYmmdd-HHMMSS>/`：

- `SHA256SUMS.txt`：只存哈希 —— `hermes/config.yaml`、其 `a2a_agents` 块与 `model` 块（抽出算哈希、不落正文）、
  `runtime/.local/` 下 `hermes-cloud-connection.json` / `work-host.json` / `home-enabled.json` /
  `home-deployment.json` / `cutover-permit.json` / `runtime-paths.json` / `calendar-automation.json` /
  `work-automation-status.json`，以及 `skills/productivity/dayflow-personal-planner/SKILL.md`
- `dayflow-personal-planner.SKILL.md.orig`：技能原文备份（补丁后 diff 用）
- ACL 收口到 `Administrator`（写 .ps1 跑 Set-Acl，别用 `cmd /c icacls`）

## 5. 对外汇报模板（脱敏）

给：release 目录名、homeId、manifest SHA256 + 文件数、verify 结果、任务 Enabled/State/LastResult、
锁 pid 与存活判断、最近一轮时间/error、远端 revision + 四类计数、快照路径。
不给：URL、key/token、事项/复盘正文、配置正文。
附操作痕迹：「未发 Telegram、未做正式写入、仅 1 次只读 GET /state」。

## 6. 补丁相关实测事实（供设计参考，不是故障）

- 客户端单请求硬上限 **35 秒**（`runtime/scripts/http-request.mjs` 的 timer，非 Windows 分支是 30s）。
  因此「总预算 70s、最多两次同键重试」= 2×35s 正好卡上限，外层 80/85/90s 包装 + Hermes 侧 100s 调用时限都有余量。
- `hermes-client.mjs` 用 `spawn('pwsh')` 走 PATH；直接跑报 `PowerShell 7 is required for Windows HTTP requests` 是 PATH 问题。
- 批量删/改类别时服务端偶发 `TaskCanceledException`，同一操作重试 1–2 次即可（业务侧细节见 dayflow-personal-planner）。
