# 心跳缺口判定：T 时刻之后「没有新记录」到底是没发、没跑、还是没落盘

适用：A2A 对端或用户拿一个时间点（如 `2026-11-04T00:11:07Z`）问「之后为什么还没有云端心跳」，
并点名要查：任务指向哪个 release、LastRunTime/LastTaskResult、是否在运行、observation 末 N 条。
只读，不触发、不重启、不修改。

## 0. 先记住机制，再查现象

Dayflow 家主机这类 runner（`runtime/scripts/work-runner.mjs`）一轮的顺序是：

```
request('state') → auth status → request('sync/work/heartbeat')   ← 心跳在轮首
→ maintenance → claim 命令 / 日历 / 邮件 → 备份（每日一次）
finally: 写 work-automation-status.json，再 append observation.jsonl，再裁到最近 3000 行
```

两个直接推论：

1. 一轮 `error=null` 且之后云端调用全 2xx ⇒ **心跳已经发出去了**，云侧「没有心跳」是展示/落盘问题。
2. observation 是**轮末**才写的 ⇒ 任何「正在跑」的窗口里，文件看起来都是停的。

## 1. 判定树

| 步骤 | 命令 | 结论 |
|---|---|---|
| ① 任务是否启用/在跑 | `Get-ScheduledTask` / `Get-ScheduledTaskInfo` | `State=Running/Ready`、`enabled=true` 才继续；`LastTaskResult` 见码表 |
| ② 有没有在途实例 | `Get-CimInstance Win32_Process`（wscript + node + work-runner） | 有进程且 CPU 在涨 ⇒ 不是「任务没被触发」 |
| ③ 在途那轮是否真在干活 | 同目录兄弟文件 mtime + `Get-NetTCPConnection` | 兄弟文件比 observation 新 ⇒ 干活中 |
| ④ 心跳是否已送达 | 那轮 `error` 是否 null + 后续请求是否 2xx | null 且 2xx ⇒ 已送达，只是没落盘 |

四步都指向「在途/已成功」时，结论写：**不是卡住，是轮末落盘造成的观测空窗**，并给出该轮真实 finishedAt。

## 2. LastTaskResult 码表（实测）

| 值 | hex | 含义 |
|---|---|---|
| `0` | `0x0` | 上一轮成功 |
| `267009` | `0x41301` | 实例正在运行（不是失败） |
| `2147946720` | `0x800710E0` | 触发被拒：上一轮未结束 + `MultipleInstances=IgnoreNew`；或 operator refused |
| `1` | `0x1` | 通用失败，去看服务自己的 status/observation |

注意：1 分钟重复触发 + `ExecutionTimeLimit=PT12M` 的组合下，只要有一轮超过 1 分钟，中间那些触发就会
留下 `0x800710E0`。这属于策略行为，不是故障，但要单独说明，否则对端会当成错误码。

## 3. 本次实测时间线（2026-11-04，可当基准）

```
00:06:59Z – 00:10:59Z   5 轮 error=日程服务连接未完成   （连接仍指向旧域名，网络层失败）
00:11:07.6Z             hermes-cloud-connection.json 被写入新域名+新 key  ← 迁移时刻
00:11:59Z               新一轮：心跳 OK，calendar complete=true，mail complete=true
00:13:48Z               当日备份完成（57 items / 135 records）
00:14:00Z               隔离恢复演练完成
00:14:13.435Z           该轮落盘（耗时 134s，正常 7–20s）
00:14:59Z 起            每分钟一轮，error=null，任务 LastTaskResult=0x0
```

对端在 00:11:07Z–00:14:13Z 之间查文件，看到的就是「00:11:06 之后没有新行」，但心跳其实在 00:11:59Z 就发了。

## 4. 现成命令

```bash
# 任务状态（GBK 乱码/引号被吃 → 一律走 .ps1，不直接 schtasks）
powershell -NoProfile -ExecutionPolicy Bypass -File check.ps1
# check.ps1 内：Get-ScheduledTask -TaskName 'X' / Get-ScheduledTaskInfo -TaskName 'X'
#   输出 JSON：state / enabled / actions[execute,arguments,workdir] / last_run_time /
#   last_task_result(+hex) / next_run_time / settings.ExecutionTimeLimit / MultipleInstances

# 真实进程（Action 之外的证据）
Get-CimInstance Win32_Process -Filter "Name='node.exe' OR Name='wscript.exe'" |
  Select ProcessId,ParentProcessId,CreationDate,CommandLine

# 逐轮时间线 + 尾部连续失败计数
python scripts/observe-run-timeline.py <release>/runtime/.local/work-automation-observation.jsonl 6

# 错误归属：本地有没有这句
cd <release> && grep -rn "<错误原文>" --include=*.mjs --include=*.js runtime/ deployment/
```

## 5. 报告形状（对端要求「只输出这几项」时）

- 任务表：任务名 / 是否启用 / Actions 指向的 release / 磁盘上 release 个数 / LastRunTime / LastTaskResult（含 hex）
  / 核对期间观察到的历史值（说明为何两次采样不同）。
- 逐轮表：`startedAt | finishedAt | error | calendar.complete/runId | mail.complete/runId/bodyFailures/analysisStopped`。
  子对象为 null 时写 `null / null`，并说明「该轮在 15 分钟最小间隔内，只做心跳+维护」是正常现象。
- 三条专项答复（对端一定会点名）：release 是否不一致 / 有没有代理错误 / 进程是否卡住 —— 逐条给结论 + 依据。
- 附带发现单列（如迁移前连续 2991 轮容量类远端拒绝、模型服务不可用导致分析未执行），不与本次结论混写。
- 结尾声明操作痕迹：「未触发、未重启、未修改」。

## 6. 脱敏红线

不给：`hermes-cloud-connection.json` 的 url/key（只给 mtime）、mail-cache 内容、日历/邮件正文、
observation 全文、任何 Bearer 头。给：runId、布尔、计数、时间戳、进程 pid、文件 mtime。
