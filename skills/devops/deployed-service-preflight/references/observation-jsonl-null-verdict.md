# observation.jsonl 解析失败导致的「假 null」验收（2026-11-04 Dayflow 实测）

## 现场

对端（A2A）要求只读验收「容量修复 v37 发布后，定时任务自然跑通」，给了一条 PowerShell 单行脚本：
按 `startedAt > cut(2026-11-04T00:09:21.375Z)` 过滤 `runtime/.local/work-automation-observation.jsonl`，
命中「calendar.complete && mail.complete && !error && commands.Count==0」才填 `natural`。

返回：

```json
{"natural":null,"preFixErrors":[],"lastResult":1,"latest":{"at":null,"error":null},"enabled":true}
```

`natural` 与 `latest` 同时为 null，`preFixErrors` 也空 —— 看起来像「还没跑」。实际不是。

## 只读取证链（按这个顺序）

1. `date -u` → 本机 00:07:40Z，cut 00:09:21Z **在未来**：对端发布记录与本机时钟有 ~1.5 分钟偏差。
   所以第一轮 null 里确实混着「时间未到」，但不能就此收工。
2. `Get-ScheduledTaskInfo`：`LastRunTime` 每 60s 前进、`LastTaskResult=1`、`State=Ready`、`Enabled=True`。
   任务 action 的 `WorkingDirectory` = 对端发布的那份 release（`releases/sites29-afdf902-home1`）→ 跑的就是新版本。
3. 日志 mtime 追到 `00:11:06Z`（> cut），3000 行（轮转上限）：**cut 之后确实自然跑了两次**。
4. 但 `$rows` 仍为空 → 逐行 `ConvertFrom-Json` 全失败。用掩码看结构：

```
{"startedAt":"<s>","hostId":"<s>","calendar":null,"commands":[],"error":"<s>"finishedAt":"<s>"}
```

`error` 值与 `"finishedAt"` 之间**没有逗号、没有收尾引号** → JSON 非法。
掩码本身不动结构，所以这行能看出上游是按字节截断了 error（中文字符被切成半个 `连接未完�?`），
既破坏 UTF-8 又吞掉引号/逗号。

5. 用正则抠出 error（不依赖 JSON）：
   `"error":"(?<e>[\s\S]*?)"\s*,?\s*"finishedAt"` → 三轮同一条：`日程服务连接未完成`，
   `calendar:null`、`commands:[]`，即日历/邮件阶段都没进入。

## 时间线（UTC）

| startedAt | finishedAt | 结果 |
|---|---|---|
| 00:08:59.381 | 00:09:05.901 | error（cut 前） |
| 00:09:59.453 | 00:10:06.171 | error（cut 后） |
| 00:10:59.414 | 00:11:06.501 | error（cut 后） |

结论：**修复未生效，判定 FAIL**；同一错误修复前后完全一致。

## 可复用要点

- 「脚本给的 null」永远不是证据，**证据是 mtime + LastRunTime + 逐行 parse 计数**。
- 结构掩码正则：`(?<=":")[^"]*(?=")` → `<s>`；比打印原文安全，又能看出缺逗号/缺引号这类语法病。
- 严格判据下「解析不到合格记录」= FAIL，不是「未完成」；回执要两种都写：原样 JSON + 判定。
- 凭据文件：`Get-Content -Raw hermes-cloud-connection.json` 会直接把明文 key 打进终端。
  只 `Test-Path` / 报「存在明文凭据」，值一律不取不回显。
- 上游缺陷（dump 截断）会让所有 JSON 型验收永久失真，单独列「附带发现」并建议随修复一起改。
