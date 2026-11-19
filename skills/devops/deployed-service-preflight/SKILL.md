---
name: deployed-service-preflight
description: "只读预检/脱敏回执：打补丁升级在跑服务，或只核验现有备份能否被新读取器读时用。"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [preflight, readonly, scheduled-task, manifest, desensitized, ops]
---

# 在跑服务的只读预检与脱敏汇报

适用：对一个**正在提供服务**的本机部署（Dayflow 家主机、TrendRadar、任何带定时任务的常驻服务）做
"打补丁前/后核对"。典型请求来自用户本人或 A2A 对端，措辞类似「核对活动目录/哈希/任务状态/在途锁，
只读，不暂停调度、不重启」。

## 铁律

1. **只读**：不改配置/数据、不停任务、不删锁、不重启。要写就先把发现汇报回去等授权。
2. **每条结论都来自真实命令输出**，不凭上一次预检的记忆填报。
3. **对端/群里只给脱敏结果**：版本号、计数、哈希、状态枚举、进程存活判断。
   **不给** URL、key/token、业务正文、配置正文。
4. 临时把某目录前置进 `PATH` 或给单次调用加 timeout 都**不需要**改全局 config.yaml。

## 预检六项（按序，能并行就并行）

| # | 核对项 | 怎么判 |
|---|---|---|
| 1 | 活动版本目录 | 列出 releases/，确认只有/只有一套在跑；别把根目录那份旧清单当活动清单 |
| 2 | 内容完整性 | 官方自带的 verify 子命令优先（`<node> <entry>.mjs verify`），不要手工逐个比哈希 |
| 3 | 定时任务 | `Enabled` / `State` / `LastResult` / `NextRun`；`LastResult` 要会翻译（Windows `267009`=实例在跑，不是失败） |
| 4 | 在途锁 | 锁文件里一般带 pid：读 pid → 判进程存活；**不删锁不停进程**；检查期间锁消失=那轮已正常收尾 |
| 5 | 最近一轮结果 | 服务自写的 status/observation 日志取末几条，比翻大日志快 |
| 6 | 远端状态版本 | 调一次只读 GET（state/status），只取 revision 与各类计数 + 最近成功时间；容量类故障改打 `GET /api/v1/sync/work/health`，看 `bytes[]`/`counters[]` 谁顶格（见下节） |
| 7 | 容量顶格 | `临时运行`/`主业务` 字节 vs limit、`run` 条数 vs limit；占用率**带余量字节**一起报，卡顶只剩几千字节时 99% 说明不了问题 |

Windows 具体命令、Dayflow 家主机实测基准值、pwsh PATH 坑：见 `references/dayflow-home-preflight-ops.md`。

**容量顶格型故障**（现象：定时任务每分钟 `LastTaskResult=1`、observation 里同一句容量错误反复出现）
走该 references 的「3b. 容量顶格诊断」：`GET /api/v1/sync/work/health` 用连接 key 直接 Bearer 调用，
按 `bytes[]` / `counters[]` 数组逐条对 limit 定位是谁顶格，回执只给对端点名的字段。
只读任务里绝不自行删日志/清 run 来「腾地方」——服务端语义是停新增保原数据，处置要用户决定。

## 验收类只读：脚本返回 `natural:null` 的判读

对端给的验收单行脚本（按 `startedAt > cut` 过滤 observation，命中才填 `natural`）返回 null 时，
**null 有四种成因，必须只读区分后才能下结论**：

1. 真没跑（cut 落在本机时钟未来、任务被禁用）；
2. 日志行**全部解析失败**——`ConvertFrom-Json` 抛错被 `catch{}` 吞掉，`$rows` 为空，
   `preFixErrors` 与 `natural` 会同时为 null，这是**假信号**；
3. 跑了但判据不满足（`calendar.complete`/`mail.complete` 非 true、`error` 非空、`commands` 非空）；
4. **空轮**——分钟级心跳轮本就不填 `calendar`/`mail`（设计如此，不是故障），见下节
   「补丁后独立复验 / observation 里的 `calendar:null` 第 4 种成因」。

区分手段（全部只读）：`date -u` 对比 cut（本机与对端时钟常有 1–2 分钟偏差）；日志 mtime 是否 > cut；
`Get-ScheduledTaskInfo` 的 `LastRunTime` / `LastTaskResult` / `State`；逐行 parse 成功计数；
任务 action 的 `WorkingDirectory` 是否就是对端发布的那份 release。

实测坑：`error` 字段按字节截断，中文字符被切成半个（`连接未完�?`）且丢了收尾引号 → 整行 JSON 非法 →
上面那条链一路 null。看法：用 `(?<=":")[^"]*(?=")` 掩掉字符串值只看结构，再用
`"error":"(?<e>[\s\S]*?)"\s*,?\s*"finishedAt"` 把 error 抠出来（不依赖 JSON 合法）。

回执纪律：

- 对端说「原样返回此脱敏 JSON」就原样给，但**必须紧跟一句诚实判定**（如 FAIL），
  不能让规定的格式把假 null 洗成「尚未跑完」；
- 读日志一律掩码，**绝不 `Get-Content -Raw` 凭据类文件**（本次差点把明文 key 打进回执）；
  发现明文凭据只报「存在明文凭据」，不给值；
- 顺带发现的上游缺陷（如 dump 截断丢引号会让所有 JSON 型验收永久失真）单列「附带发现」，
  不混进验收结论。

现成探针 `scripts/verify-natural-run.ps1 -ReleasePath <release> -Cut <ISO8601>`：ASCII 键 JSON，
含任务状态、日志 mtime/行数/解析失败数、cut 之后逐轮 startedAt/finishedAt/掩码 error、判定 pass/fail/not_run。
实测时间线与原文见 `references/observation-jsonl-null-verdict.md`。

## 「没有云端心跳 / 没有新行」的判读（心跳缺口）

触发：对端说「T 时刻之后为什么还没有心跳/没有新记录」，怀疑进程卡住、任务跑错 release 或代理报错。
**默认假设是「记录落盘时机」问题，不是故障**——必须按下面四步证伪后才敢下「卡住」结论。
完整判定树、实测时间线与码表见 `references/heartbeat-gap-verdict.md`；逐轮时间线直接跑
`scripts/observe-run-timeline.py <observation.jsonl> [N]`（只读，输出指定字段 + 尾部连续失败计数）。

1. **任务侧**：`Get-ScheduledTask` + `Get-ScheduledTaskInfo` 取 State / LastRunTime / NextRunTime / LastTaskResult。
   `0x800710E0`(2147946720) = 触发被拒：上一轮没结束且 `MultipleInstances=IgnoreNew`，**不是失败**；
   `0x41301`(267009) = 实例在跑；`0x0` = 成功。所以同一任务前后两次采样结果不同是常态，要连时间和
   State 一起报。
2. **release 一致性**：磁盘 `releases/` 只有一个目录 ⇒ 不存在「跑错 release」。再用
   `Get-CimInstance Win32_Process` 看**真实进程的 cmdline** 是否也指向它——Action、WorkingDirectory、
   实际进程三者都要对上，只看 Action 不够（wscript→node 两层包装，容易只看到 wscript）。
3. **心跳是否真发出去**：多数 runner 把 heartbeat 放在一轮的**最开头**。若该轮 `error=null` 且其后
   云端调用全部 2xx，心跳必然已送达；此时「没有心跳」只是**观测文件没落盘**，不要写成发送失败。
4. **为什么没落盘**：observation 一般在 `finally` 里写 ⇒ 一轮跑长就留下「上一行之后空白」的窗口。
   实测：当日备份 + 隔离恢复演练把一轮从 7s 拉到 134s（备份 00:13:48Z 完成、演练 00:14:00Z），
   期间每分钟触发全被 `IgnoreNew` 拒掉（就是上面那个 `0x800710E0`），对端在两分半钟里查文件当然看不到新行。

在途但尚未落盘的证据（不依赖 status 文件，因为它也常在末尾才写）：进程 `CreationDate` 与
`TotalProcessorTime` 在增长、`Responding=True`、`Get-NetTCPConnection` 无异常连接；**同目录兄弟文件的
mtime 比 observation 新**（host 元数据 / mail-cache / client-diagnostics / automatic-backups）⇒ 那轮正在干活。

**错误字符串的归属**：`grep -rn "<错误原文>" runtime/ deployment/`。本地搜不到 ⇒ 是云端返回的 `v.error`
业务错误（如容量类），不是本地崩溃；回执里要写「远端 API 返回」，不能写成「代码抛错」。

**滚动窗口**：observation 常被裁到最近 N 行（实测 3000 行 ≈ 50 小时，`finishedAt` 早于 30/90 天的行被丢）。
窗口首行**不是**故障起点，只能报「窗口内连续失败 N 次」，不能报「从某日某时起一直失败」。

脱敏：连接配置只报 **mtime**（域名迁移发生的时刻往往就是它，本次 `00:11:07.6Z` 正是新连接配置的写入时间），
不给 url / key；给 runId、布尔、计数、时间戳就够对端定位。

## Windows/MSYS 通用坑（会让预检本身出错）

- **`schtasks /query` 中文系统下 GBK 乱码**，`/FI "PID eq 123"` 还会被 bash 吃引号报
  `无效参数/选项 - 'eq'`。统一用 PowerShell `Get-ScheduledTask` + `Get-ScheduledTaskInfo`，
  只拼要的字段输出。
- **`icacls` 别经 `cmd /c`**：反斜杠+括号被 MSYS 吃掉，报「文件名、目录名或卷标语法不正确」
  （还会打印骗人的「成功 0 个」）。写 `.ps1` 用 `powershell -NoProfile -ExecutionPolicy Bypass -File` 跑，
  末尾 `Get-Acl` 回显当验证。
- **原生 CLI 内部 `spawn('pwsh')` / `spawn('node')` 走 PATH**：报 `PowerShell 7 is required`
  是 PATH 缺 pwsh，不是客户端坏。本次调用 `env['PATH'] = pwsh_dir + ';' + env['PATH']` 即可。
- **二进制位置常在部署根而不是 release 里**（如 `tools/node24/node.exe`）；在 release 目录写
  `./tools/...` 会 `No such file`。先 `find <root> -maxdepth 3 -name node.exe`。
- 服务自带单请求硬超时很常见（30–35s）；Hermes `terminal` 的 `timeout` 单次可给 100–300s，
  前台上限 600s，更长用 `background=true`。
- **对端给的 `node -e '...'` 单行校验命令在 PowerShell 下会塌**：PowerShell 解析 `-e` 时剥掉 JS 内部双引号，
  `from "node:fs"` 变成 `from node:fs`，报 `SyntaxError: Unexpected identifier 'node'`。
  别硬改写那一行，把 JS 落成 `.mjs` runner 传路径（已固化：`scripts/verify-backup-readable.mjs`）。
- **原生命令 stderr 被 `ErrorActionPreference='Stop'` 吞成一行**（只剩 `file:///...[eval1]:1`，
  真正的 SyntaxError 丢了）：原生调用期间用 `'Continue'`，加 `1> out.txt 2> err.txt` 重定向再 `Get-Content -Raw`。
- **PowerShell 5.1 缺 .NET Core 的静态方法**：`[Convert]::ToHexString` 在 5.1 里不存在
  （`MethodNotFound`），算哈希统一 `[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','')`。
  脚本自己回传的 JSON **只用 ASCII 键与布尔**：PS 5.1 的中文报错经 bash 是 GBK 乱码，读不出原文。

## 备份 / 读取器兼容性核验（只读）

触发：对端说「只核验现有备份能不能被**更新后的读取器**读，不创建/恢复正式数据、不改配置/调度、不发 Telegram」。
这类任务不是「核对已知清单」，而是**证明兼容性**，所以：

1. 只取**最新一份**备份（`Sort-Object LastWriteTime -Descending | Select-Object -First 1`），读它、绝不写它；
   顺带报候选份数，避免「最新那份其实不是每日备份」的误判。
2. 调用前先确认导出名还在：`typeof m.validateBackup === 'function'`，不是就报「读取器导出变了」，不要让它崩在栈里。
3. 回执只给字段名与计数：`valid / backupVersion / exportedAt / requiredFeatures / items / goals / reviews /
   newReaderUsed / noRestore`，加元数据（文件名、mtime、候选份数）。**不给条目正文**、不给邮件/复盘原文、不给密钥。
4. `requiredFeatures: []` 是「无特性门槛」，不是缺失——别写成异常。
5. 结论里显式声明「未做 restore、未改配置/调度、未发 Telegram」，对端才认这条账。
6. 路径不存在：只报错（原话：不自行改造目录、不补跑备份）。

现成脚本 `scripts/verify-backup-readable.mjs`：`node <runner> <runtime/lib/backup.ts> <backup.json>`。
node ≥23 默认开类型擦除，`.ts` 可直接 `import()`，不需要额外 flag。
踩坑原文与 PowerShell 包装见 `references/backup-reader-verify.md`。

### 云端直取 + 内存演练（`GET /api/v1/backup` + `isolatedBackupDrill`）

触发：对端说「用活动 release 和已有私有连接 GET /api/v1/backup，**只把响应留在内存**，
调 `runtime/scripts/work-backup.mjs` 的 `isolatedBackupDrill(backup)` 在内存 SQLite 做空库/非空恢复核对，
绝不调云端 restore/POST」。—— 与上一节的区别：那份读的是**磁盘上最新备份文件**，这份读的是**云端实时备份**。
一键探针 `scripts/backup-drill-verify.mjs <release> <connection.json>`（stdout 单行脱敏 JSON）；
实测数值、403 取证与 drill 内部流程见 `references/backup-drill-api-verify.md`。

1. **传输层必须用 release 自己那份，别用裸 `fetch`。** `runtime/scripts/http-request.mjs` 在 win32 上
   `spawn('pwsh',['-File','http-request.ps1'])`，只有非 Windows 才走 `fetch`。裸 `fetch` 打云端会拿
   `403 text/html`（`server: cloudflare` + `cf-ray`），**且同一把 key 打 `/api/v1/state`、
   `/api/v1/sync/work/status` 同样 403** —— 这是边缘层挡 undici 指纹，不是 key 过期、不是接口不存在
   （同一分钟定时任务每轮全 2xx、`error:null`）。看到 403 HTML 别报「鉴权失败/无此接口」，也别去绕校验：
   换成 `import('…/scripts/http-request.mjs').httpRequest(url,{method:'GET',headers:{Authorization:'Bearer '+key,
   Accept:'application/json'}})` 即 200。`spawn('pwsh')` 走 PATH ⇒ 先把 `<root>/tools/pwsh7` 前置，
   否则报 `runtime_missing`。这条差异要作为「附带发现」写进回执。
2. **响应只留内存**：`body` 字符串进变量 → `Buffer.byteLength` 报字节、`createHash('sha256')` 报全量哈希；
   不落盘、不打印正文/标题。脚本体可落 `$LOCALAPPDATA/Temp/*.mjs`（原生 node 才认该路径），跑完删。
3. **计数口径**：items/goals/reviews 在 `data.*`，history/coach/work 在**顶层**，`requiredFeatures` 也在顶层
   （`[]` = 无门槛）。`GET /api/v1/backup` 给的是 v5 全量，不是 `backup/transfers/*` 分片——只读任务别碰分片。
4. **空库/非空都由 drill 覆盖，不要自己写恢复**：它 `new DatabaseSync(':memory:')` → 建 `planner_state`
   +`STORAGE_SCHEMA`（真空库）→ `recoveryPreview`/`controlledRestore` → `fullBackup()` 回读并逐段
   `isDeepStrictEqual(data/history/coach/work)` → 再带 `recoveryEpoch` 二次恢复。回执取
   `status/isolated/nonemptyRestore/items/workRecords`，并**交叉核对 `drill.items==counts.items`、
   `drill.workRecords==counts.work`**（实测 61/139 全等）；不相等就是丢数据，比它自报 complete 更可信。
5. **时间戳两个来源**：`exportedAt` 是服务端时钟（实测快本机 2–3 分钟），`drill.at` 是本机时钟；
   「备份比演练晚」是时钟差，不是顺序错乱，回执里标清来源。
6. **`requiredFeatures` 只是门槛标记，载荷在 `coach[]` 里。** `["ai-models-v1"]` 的真实内容不占顶层字段：
   `coach[]` 中 `purpose:'ai_model_configuration'` 的 body 只有 `{purpose, selection:{schema,defaultModel,overrides}}`，
   另有若干 `purpose:'model_operation'`（`operation/status/model/requestId/configurationVersion/finishedAt`）测试回执。
   要证明「新配置 + 测试回执都能读」，必须同时给 selection 摘要、回执条数、最近一条 status；只给 requiredFeatures 不算证据。
7. **导出的 SHA256 只属本次。** 每次 `GET /api/v1/backup` 的 `exportedAt` 都变 ⇒ 字节数与哈希随之变。
   回执里写「SHA 为本次导出专属」并附 `exportedAt`，否则对端拿另一时刻的哈希来对必然对不上。
8. **自然同步取证走云端，别只翻 observation。** `GET /api/v1/sync/work/status` 的 `runs[]` 取 `type` 为 calendar / mail
   各最后一条（`status` / `updatedAt` / `error`），再带 `checkpoints[].sequence`、`hosts[].authStatus`、`commands[]`（历史回执）。
   `work-host.json` 的 `lastCalendar`/`lastMail` 是**本机落盘时刻**，与云端 `runs[].updatedAt` 常差几十秒，以云端为准。

## 成对写读：临时锁 → 对端独立核验 → 还原

触发：A2A 对端要「先证明配置能被独立读取，再原样还原」，典型是把某用途的模型 override 临时设成它**当前 effective 的同一型号**、
等对端用自己的 HTTP 通道回读确认，再用一次新写入把 override 置回 `null`。实测回执与坑见
`references/model-override-pair-write.md`。

1. **两步语义别搞混**：第一步只让 `source` 由 `default` 变 `independent`，型号一字不改；第二步才是还原
   （`overrides.<用途>=null`）。写前必核 version / epochDigest / defaultModel / 四个用途 effective 全部等于对端口述值，
   任一不符或 409 就停，不覆盖。
2. **每步用新 request id**（`--request-id <uuid>`，env 变量在 MSYS 里不生效），payload 走 `--json-file`。
3. **调用姿势**：bash 里 `export PATH=<root>/tools/pwsh7:$PATH` **不生效**（传进 node 后 spawn 仍找不到 pwsh）。要
   `pwsh.exe -Command "$env:PATH='<root>\tools\pwsh7;'+$env:PATH; & '<root>\tools\node24\node.exe' 'scripts\hermes-local.mjs'
   --connection '.local\hermes-cloud-connection.json' --request-id <uuid> --json-file '.local\<payload>.json' models-set; 'EXIT='+$LASTEXITCODE"`，
   cwd 设到 `runtime/`。首调报 `runtime_missing`（30ms 级失败）先改这条，别怀疑 key。
4. **回执给四段**：before DTO、payload、写入响应、after DTO，各带 requestId 与退出码；再补一句 version 连续性
   （如 0→1→2 无跳号）——连续性本身就是「没有第三方插队」的证据，比口述可信。
5. 临时 payload 写 `runtime/.local/`，跑完删掉，release 里不留残留；回执声明「未输出连接文件/密钥」。

## 私有连接配置的 URL 迁移（校验 → 原子替换 → 独立回读）

触发：对端说「原域名 307 跳到新域名、客户端拒绝跟随重定向，只改私有连接配置里的 `url`，
不换密钥、不改清单/脚本/Hermes 配置、不重启、不触发同步、不发消息」。
完整实测流程、回执样例与坑见 `references/connection-url-migration.md`；
可直接复制改的骨架：`templates/atomic-config-url-swap.ps1`。

1. **先证明是新域名还是同一生产库，再动手**：`GET <new>/api/v1/sync/work/status` 必须 200，且
   `MaximumRedirection = 0`（默认跟随会把 307 洗成 200，等于没验证）；身份指纹对得上才算过——
   已知同步 host key 在 `hosts[]` 里、`sources[]` 中 `body.selected` 的条数 == 对端说的数。不符就停。
2. **写操作只有 `url` 一个字段**。`ConvertTo-Json` 会重排整个文件，所以「只动了 url」靠
   写前记下「除 url 外每个字段的哈希串」、写后逐项比对来证明，不能眼看 diff。
3. **原子替换**：`.tmp`（UTF-8 无 BOM）→ `Set-Acl` 拷原 ACL → `[IO.File]::Replace($tmp,$p,$bak)`。
   所有哈希/校验放在写入分支最前面，任何 throw 都落在写盘前 → 失败即零改动。
4. **换一个独立只读脚本回读**，不要拿同一个脚本的自报当结论：url 已新、JSON 仍可解析、
   key 与 `.bak` 逐字符相同、ACL 的 Sddl 与 `.bak` 一致、`.bak` 恰好 1 个、残留 `.tmp` 为 0。
5. 回执只给对端点名的布尔 + 时间戳；另附一句「首次失败是否发生在写前」，以及
   「未改清单/脚本/配置、未重启、未触发同步、未发消息」。下一轮由对端自然核验，不主动补跑。

## 交付形状

1. 一段 JSON（分块：release / task / lock / sync / remote state / snapshot 路径），哈希只给前 8–12 位或全量但**不带正文**。
2. 3–6 行结论：哪些对上了、哪些是正常现象（例如旧清单哈希不同、`LastResult` 是在跑）。
3. 附一句操作痕迹：「未发消息、未做正式写入、仅 N 次只读 GET」。
4. 预检发现的**供补丁设计参考的事实**（如客户端单请求 35s 上限、总预算 70s 正好两次）单独列，不说成故障。

## 安装前对照快照

补丁前把「补丁后要能证明没被动过」的东西落盘到本机私有目录（不带正文、不发对端）：

- `SHA256SUMS.txt`：`config.yaml`、其中 `a2a_agents` / `model` 等关键块的**抽取后哈希**（抽出来算哈希，不落正文）、
  服务私有连接/主机/启用/切换配置文件、相关 skill 的 `SKILL.md`
- 受管文件原文备份（例如 skill 原文 `.orig`），补丁后好 diff
- 目录权限收口到本账户（见上 icacls 坑）

---

## 补丁安装（对端下发升级包，本技能的下半场）

触发：A2A 对端或用户给一个 zip + SHA256 + 字节数 + 新 manifest 哈希 + 期望文件数，要求「按这个范围安装」。
完整实测流程与字段见 `references/patch-install-a2a.md`；装完的核验探针可直接跑 `scripts/verify-release-manifest.mjs`。

1. **先验包，再解包。** 下载后立刻比字节数与 SHA256，任一不符就停，不解压不安装。内网下载绕代理：
   `Invoke-WebRequest -NoProxy`（只对这一条命令，不动全局代理配置）。
2. **解到独立新目录** `patches/<patchId>/`。绝不覆盖既有 patch 目录或 old release；目标目录已存在就先问/换名。
3. **读 `patch.json` + `upgrade.ps1` + `apply.mjs` 再执行**（三者都小，读得起）。至少确认：
   - `changes[]` 的 `before` 哈希 == 活动 release 现文件哈希；`before:null` 的条数 == 对端口述的「新增文件数」；
   - 安装器里的 `allowed` 白名单 == `changes` 路径集（白名单多出路径就是不守范围）；
   - 只有 disable → 轮询等在途自然结束 → apply → `finally` 复原 `Enabled`；**没有**网络请求、重启、kill、删锁；
   - 失败路径有回退（拷回 backup、删掉新增文件）。
4. **一条终端调用跑完 driver**，别拆成多步（中途超时更麻烦）：
   `<root>/tools/pwsh7/pwsh.exe -NoProfile -ExecutionPolicy Bypass -File <patch>/upgrade.ps1 -ReleasePath "<活动 release>"`，
   `timeout` 给 300s（等待在途上限 120s + 安装）。先 `export LOCALAPPDATA=... USERPROFILE=...`，
   否则脚本里 `$env:LOCALAPPDATA` 为空，报 `Unexpected release path`。
5. **失败只回报，不重跑。** 脚本超时/报错时回报错误 + 任务是否已复原 Enabled，不自行强装、不第二次执行。
6. **装完三项核验**：新 `manifest.json` SHA256 == 对端给的值；`verifyManifest` 文件数 == 期望数（缺失/不匹配 0）；
   技能标记按 patch 自己的约定核验——**单 marker 恰好出现 1 次** + `startsWith(旧全文)` 为真（追加型），
   或**开/闭注释成对**（包裹型）。不要假定是哪一种，看 `skill-append.md` 里写的是哪种。
   - 对端说的「N 文件」= `manifest.json` 的 `files[]` 条数，**不是** `find -type f | wc -l` 的结果
     （release 里还有 `runtime/.local/` 的缓存、备份、锁，实测同一 release 两种算法 55 vs 192）。
     报数前先说明口径，否则对端会因为 192≠55 判你装错了。
   - 核验别只信自己的 python/sha256sum 循环：用部署自带的 `deployment/home.mjs` 的 `verifyManifest()`
     再独立跑一遍（`node -e "import('file:///…/home.mjs').then(m=>m.verifyManifest('<release>'))"`），两个都过才算过。
     **它的返回形状要注意**：成功时把 manifest 对象原样返回（带 `files[]`），**没有** `missing`/`mismatch`
     这类判定字段，不匹配就直接 throw。所以「verify=ok」的判据是**没抛异常**，别去找字段、也别把
     `files.length` 当成第二重校验结果（实测 `{files:[…56 条], …}` 就是全部输出）。
   - **「只动了对端点名的那 N 个文件」用升级自身的备份清单做 path 级 diff**：`<backupDirectory>/manifest.json`
     是安装前清单（driver 在 apply 之前拷的），装后按 path 逐条比 `bytes+sha256`，报 `changed / added / removed`。
     实测单文件补丁得到 `diffVsBackup ["CHANGED runtime/scripts/hermes-local.mjs 1780->1957"]`、其余 55 条零差异——
     这就是「未重装两个已装 CLI 与读取器」的正面证据，比口述「我没动它们」可信得多。
7. **回报形状**：upgrade 的脱敏 receipt JSON（`installed` / `originalEnabled` / `enabledRestored` /
   `taskDefinitionUnchanged` / `privateConfigurationsUnchanged` / `noReboot` / `noCloudWrites`）+ apply 的
   `patched` / `files` / `sourceCommit` + 上面三条核验结论。原文摘录，不要转述成「都成功了」。
   apply 的那行 JSON **不在 upgrade 的 stdout 里**——`upgrade.ps1` 用 `*>` 把它重定向进了备份目录的
   `install.log`，要从 `<backup>/install.log` 末尾 tail 出来（备份目录路径在 receipt 的 `backupDirectory`）。

## 补丁后「独立复验」（不改文件、不重装、不联网）

触发：对端说「只读独立补验，不重复安装、不改文件/任务、不触发模型或云端写入」，并给出上次备份
manifest 路径 + 两个文件的 expected SHA256 + 要核的原任务状态。**不要重跑 upgrade.ps1/apply.mjs**，
核对全部靠读。一键探针：`scripts/reverify-patch-manifest.py --release <release> --backup-manifest <backup>/manifest.json
--expect runtime/scripts/x.mjs=<sha> --old-skill <backup>/SKILL.md --skill <hermes>/skills/.../SKILL.md --marker DAYFLOW-XXX-`
（stdout 就是脱敏 JSON；`--install-write-utc` 不给时取变更文件的最大 mtime 当安装时刻）。

1. **先定位部署根，别盲搜。** 不知道 root 时直接按活动 release 目录名搜：
   `find /c /d -maxdepth 7 -type d -name "sites29-afdf902-home1"`（Dayflow 家主机实测 =
   `C:/Users/Administrator/AppData/Local/DayflowHome`）。`maxdepth 3–4` 搜 `patches`/`releases`/`ai-models*` 会全空，
   别据此认为「部署不在这台机器」。根目录那份 `manifest.json` 是安装初版，活动清单在 `releases/<name>/manifest.json`。
2. **manifest 对差按 path 逐条比全字段**（不是只比 sha256）：报 `changed / addedPaths / missingPaths /
   unchangedCount`，并声明「其余 N 条逐项零差异（path+bytes+sha256 全字段）」——对端问的正是这个数。
3. **顶层字段单列**：`missingInCurrent` 必须为空；`preservedIdentical` 逐项列（`compatibilityPatch`、`fix66Patch`、
   `fix66SiteVersion`、`fix66SourceCommit` 这类旧官方兼容补丁元数据要在里面）；`addedOnly` 只应对端点名的那几个
   （如 `patches`、`aiModels69SourceCommit`）。**`patches` 是新增数组时只表示「本轮标记」，不是「旧元数据被删」，
   回执里要写清这句**，否则对端会判你丢字段。
4. **私有配置「未变」的独立证据只能靠 mtime**：receipt 只有 `privateConfigurationsUnchanged` 布尔，upgrade 不落
   前后哈希。做法＝按安装器里的候选路径表探针（实测 8 个候选、7 个存在），逐个 mtime 全部早于安装写入时刻 →
   `unchanged: true`。报布尔 + 文件数 + 最新 mtime，**不报哈希列表、不报路径正文**。
5. **技能前缀用字节比**：`new_bytes[:len(old_bytes)] == old_bytes`，不要 decode 后比字符串（会掩盖 BOM/换行差异）；
   marker 用 `count` 报恰好 1 次，另报 `name:` 行仍在。
6. **任务与运行面**：`Get-ScheduledTask`/`-Info` 报 State/Enabled/LastRunTime/LastTaskResult(=0 才算成功)/NextRun，
   并核 `WorkingDirectory` 就是对端那份 release。运行面报「装后 N 轮、errors 0、首个完整周期」的时间。
7. **回执**：脱敏 JSON + 一句判定；末尾声明「零网络、零写入、未重跑安装」，并补一句任务自身分钟级轮次是
   它的常规同步、不是本次检查发起的写入。

### observation 里的 `calendar:null` 第 4 种成因：空轮

除「没跑 / JSON 解析全失败 / 判据不满足」外，还有一种是**设计如此**：分钟级 cheap tick 只做心跳，
`calendar`/`mail`/`runId` 全为 null；只有完整工作日周期才填。所以「最后一行 calendar=null」**不是故障**。
判法：取窗口内**最后一条 `calendar` 非空**的记录，报它的 `startedAt`/`finishedAt` + `calendar.complete` +
`mail.complete` + `mail.observed`/`bodyFailures`；再配 `work-host.json` 的 `lastCalendar`/`lastMail`/`lastMailFull`。
实测同一 release：21 轮里只有 1 轮完整周期（`07:23:59Z→07:25:15Z`，两源 complete、0 变更，mail observed 5/失败 0），
其余全 null 仍 error 0——把它写成「有 20 轮缺 calendar」就是误报。

### 安装类任务的坑

- **复原任务状态的二次核对脚本里，路径必须写 `C:/…`**。从 bash 传 `/c/Users/...` 进 `pwsh -Command "…"`
  会变成 `C:\c\Users\...`，`[IO.File]::ReadAllText` 报 `Could not find a part of the path`，
  于是 `definitionSame` 算出 **false**——这是路径错，不是任务被改坏。别急着回报「定义未恢复」，
  先看报错里的路径是不是多了个 `\c\`，改用原生 `C:/…` 重跑（实测重跑即 true，两边都是 2233 字符）。
  同一坑也吃 `-File <脚本>`、`Get-FileHash`、`Test-Path` 的一切参数。

- **预检时 `work-sync.lock` 存在≠停止条件**：分钟级任务每轮都建/删锁，实测 4 秒后自己消失。做法是
  `Test-Path` 一次、隔几秒再 stat 一次（`ls` 报 `No such file` 即那轮已收尾）就当它不存在；driver 自己会
  disable 后轮询 120s（超时只 throw，不 kill 不删锁）。真正该停的是「disable 后等满 120s 锁仍在」。
- **跑 driver 前先算 payload 哈希**：`hash(<patch>/<change.path>) == change.after`（apply 会 throw
  `File baseline/payload mismatch`）。连同 manifest 基线、每类标记的顶层键一起预核，避免白暂停一次任务。
- **复原 `Enabled` 后分钟级任务会立刻自然跑起来**，可能产生它自己的云端同步。必须主动声明「这是它自身的常规同步，不是我发起的写入」，
  否则对端会以为你违反了「不做云端写入」。
- **对端常明确说「先不做整套长验收」**——那就只给要求的三项，不要顺手跑全套用例把回执淹掉。
- 私有配置改动只能报**布尔**（`privateConfigUnchanged: true`）与文件数，不能报哈希列表、路径内容、凭据。
- **补丁可以改到 Hermes 自己的技能文件**（`%LOCALAPPDATA%/hermes/skills/<cat>/<skill>/SKILL.md` 末尾追加段）。
  这是合法范围，不要事后再手工「整理」那段文字——那会让 `startsWith(旧全文)` 的前缀证明失效；
  只核验「前缀零改动 + marker 恰好一次 + YAML `name:` 行仍在」。

- **系统 PATH 里没有 `pwsh` 是常态：别装 PowerShell 7、也别退回 5.1 硬跑。** 部署自带便携版在
  `<root>/tools/pwsh7/pwsh.exe`（实测 7.6.7，`tools/` 下同目录还有 `node24/node.exe`）。定位别靠
  `find /c -maxdepth 5 -name pwsh.exe`——实测全空，是深度不够（在 `AppData\Local\DayflowHome\tools` 第 6 层）；
  直接 `ls <root>/tools` 或 `grep -n pwsh <root>/logs/deploy-log.md`（部署日志里就写着 `tools/pwsh7/`）。
  driver 用了 PS7 专用语法（`[Text.UTF8Encoding]::new(...)`、`*>`），5.1 会静默错。

- **跑 driver 前先自己把 apply 会 throw 的前置全核一遍**（否则要等它先 disable 了任务才炸）：
  `manifest.json` 的 SHA256 == 对端给的基线（本例 55 条 / `1772c065…a5c6`）；`changes[]` 每条 `before`
  等于活动 release 现文件哈希；`before:null` 的新文件**确实不存在**；`work-sync.lock` 不存在；
  记下任务 `Enabled` 真值（`finally` 就靠它复原）；apply 会读的那个 skill 文件存在
  （缺了直接 `throw 'Unexpected skill'`，白暂停一次）。
  第三种补丁形状（只换读取器模块 + 新增一个 schema 模块、不含技能追加、带 `check-reader.mjs` 内存演练）
  与第四种形状（单文件包装替换、`changes` 只 1 条、manifest 只追加 marker + 一个 sourceCommit 键）
  的实测值与回执见 `references/patch-install-a2a.md` 末两节。

---

## 暂存补丁的验收（只跑已有测试，不改任何文件）

触发：对端说「已有补丁 N 在暂存目录，正式站已发布，**只跑已有 tests/test_*.py 和 py_compile**，
设好 dry 开关，禁止真实投递，顺手只读 GET 某个新路由确认状态码，立刻回测试是否通过 / 两个文件的
SHA256 / 备份是否可用，未完成的单列」。这类任务**不是安装也不是复验**：一个字节都不该写。
本次实测（Dayflow 73 号提醒补丁，2026-11-18）见 `references/staged-patch-acceptance.md`。

**门禁顺序（跑完再报告，别边跑边下结论）**

1. `sha256sum -c <HASHES_N>.txt` —— 一次核对整套暂存物 + 线上原文件 + 备份（对方已有的清单优先用，
   比自己现算一套更能证明「没被动过」）。
2. `python -m py_compile <新脚本> <被改脚本> <测试>` —— 编译通过才谈跑测试。
3. dry 跑已有测试：`DAYFLOW_DRY=1 python tests/test_x.py`，取末尾 `PASS n / FAIL m` 与退出码。
4. 只读 GET 新路由（用部署自带传输层，见 `local-cli-client-ops` 第九节），报 status + 形状 + 条数。
5. 备份可用性 + 「线上零改动」+「任务未切换」三项旁证。

**「禁止真实投递」要给证据结构，不是复述环境变量**

- 读测试源码确认它把通道换成了假的：`C.send = Rec()` 注入 + 状态目录指向 `tempfile.mkdtemp()`；
  只覆盖 DRY 的段落靠 `[DRY]` 输出，覆盖状态机的段落靠假通道。仅凭 `DAYFLOW_DRY=1` 不能证明
  第 C/D/F 段（它们内部会把 dry 改回 0）没有真发。
- 任务侧旁证：读 `cron/jobs.json`（或计划任务）**仍是旧脚本**，报告里写一句「未切换」——这同时回答
  「补丁是否已上线」和「我刚才的测试是否可能被心跳撞上」。
- 测试自己会在 `%TEMP%` 留沙箱目录（本次 34 个 `*_test_*`）；说明「只落在 Temp、项目目录零改动」，
  要不要删由对方定。

**备份可用 ≠ 备份存在：两步证明**

1. 逐字节相同：备份 vs 线上现文件 `sha256sum` 相等（说明可直接覆盖回滚）。
2. 可编译：把备份**复制到 Temp** 再 `py_compile`。🔴 `py_compile` 会在源文件旁写 `__pycache__`——
   就地编译备份 = 往备份目录里写文件，直接违反「不改任何文件」。同理别在 `backup_*/` 下跑测试。
3. 顺手说清备份范围：只备份了会被改的原文件；新增文件无需备份（回滚就是删掉它们）。

**「服务端已发布」≠「本地客户端已升级」**

对端说正式站发布了新版本时，只读 GET 的结果必须和本地 release 名一起报：本地仍是 `releases/sites29-…`
而服务端已到 Sites43 是可能且常见的。此时新路由回 `200 []` 有三种成因（真无候选 / 旧契约 / 参数没透传）。
别停在「只读无法区分」——下面的参数扫描可以真的分开（2026-11-18 实测），**分开之前不许写「接口正常」**。

### `200 []` 的三种成因怎么分开：参数扫描 + 字段级契约比对

一键探针：`scripts/probe-endpoint-shape.mjs <releaseRoot> <connection.json> <route> [route...]`
（逐条 GET，输出 status / 形状 / 条数 / 字段并集 / 字节数，不打印 url、key、正文）；
没 pwsh 或就想用 stdlib 时用 `scripts/probe-api-shape.py auto <route> [route...]`（自带 UA、自找连接文件与代理）。
完整实测（Dayflow 73 vs Sites43）见 `references/live-endpoint-shape-diff.md`。

1. **先查本地客户端认不认补丁要传的 flag**：`grep -c -- '--query' <release>/runtime/scripts/hermes-client.mjs`。
   本次 = **0**，说明 `--query calendarChanges=1&lead=18` 被静默丢弃（mapping 里只有 op→method/route，多余参数没人看）。
   结论要写「本地客户端丢参数」，不是「接口没有数据」。别信补丁注释里写的「73 客户端才认」。
2. **直连的关键是 `User-Agent`，不是「用哪个库」**（2026-11-18 复核修正）。缺 UA 时裸 `fetch`、python `urllib`
   都会回 `403 error code: 1010`（Cloudflare 挡指纹），**这不是鉴权失败、也不是接口不存在**；补一行常规
   `User-Agent` + 同样的 `Authorization: Bearer` 后，python `urllib` 直接 200（同日实测：`/api/v1/state` 47 KB、
   `due?lead=1440` 200 4 条）。两条路都行：release 自带的 `http-request.mjs`（win32 下 `spawn('pwsh')`，
   要把 `<root>/tools/pwsh7` 前置进 `PATH`，否则 `runtime_missing`），或 stdlib + UA（探针
   `scripts/probe-api-shape.py`，不需要 pwsh）。连接文件取 `releases/*/runtime/.local/hermes-cloud-connection.json`
   里 mtime 最新那份，代理取同目录 `calendar-automation.json` 的 `httpProxy`。
3. **参数扫描分辨三种成因**：同一条路由跑四组 —— 裸路径 / `?calendarChanges=1&lead=18` / `?lead=1200` /
   `?calendarChanges=1&lead=1200`。窗口放大（1200 分钟）能逼出候选 ⇒ 服务端在、参数被解析（否则 `[]` 且
   畸形值也 200）；仍全 `[]` ⇒ 旧契约未上线。本次正是靠这条把「没候选」证伪成「有候选但字段不对」。
4. **字段级契约比对（这一步才是重点）**：线上候选字段清单 vs 补丁 `normalize()/classify()` 必须读的字段。
   本次线上每条只有 `{date,end,itemId,key,start,title}`，而 `classify()` 先看 `source`（空 ⇒ `source-empty` 跳过）、
   再看 `message`（空 ⇒ `no-message` 跳过）⇒ **一条都不会发**。
5. **判定规则**：补丁是 fail-close（快照路径已剔除钉钉）+ 线上缺关键字段 ⇒ **不切换，保留旧入口**。
   这是比「测试失败」更隐蔽的拦路：离线夹具是照补丁**自己**的契约编的，38/38 全过也发现不了；
   缺字段的后果是通知静默全停，不是报错。
6. 替代路线要作为「待用户定」的选项列出，不自行改设计：例如用 `due.itemId` 回查 `/api/v1/items`
   （`items` 里 `source`/`sourceLifecycle` 齐全，实测 98 条中 dingtalk 30），或等对端下发新版 home 包。

**回执形状（对方要的就是这几项，按序给）**

1. 测试：`PASS n / FAIL m` + 退出码 + 分块计数；py_compile 单独一行。
2. 两个文件的 SHA256 原文（一行一个），并注明与对方提供的清单一致。
3. 备份：相等哈希 + 编译通过 + 范围说明 → 「可直接覆盖回滚」。
4. 只读 GET：status / content-type / body 字节数 / 形状 / 条数（正文与密钥一律不打）。
5. **未完成项单列，每条写清为什么阻塞**（本次：空数组判定歧义会把整轮提醒失败关闭；客户端丢 query
   参数；cron 未切换等对方确认；真实一轮观察会发消息故禁止）。不要把这些塞进「结论：通过」。
6. 对端点名要 `RECEIPT_N.json` 时：`testsPassed` 与 `enabled` 是**两个独立字段**，`testsPassed:true` +
   `enabled:false` 是合法且常见的结论，别把两者压成一个「结果」。`enabled=false` 的理由要写成可复核的事实
   （缺哪几个字段、哪条检查没过、现网脚本哈希与备份是否仍相等），不写「有风险」。回执里附
   `checks{dingtalkSnapshotNoPreMeeting, ackRetryNoResend, liveDueReadiness}` 这类逐项布尔，比一句结论好核。
7. A2A 对端说「前两次回复超时」时：**先把回执文件落盘，再回话**，回话压到 3 行内（结论 + 阻塞事实 + 下一步二选一），
   细节全留在 JSON 里让对方自己读。

### 第二轮：批准后把契约改成格式自适应（仍不切 cron）

触发：对端看了第一轮的阻塞项后回来说「读取改直连带认证 HTTP，按实际格式兼容：X 才接管、Y 缺省是什么、
空列表和非目标候选都算正常」。完整配方（字段→行为映射、重试表、测试矩阵、回执字段）见
`references/api-contract-adaptation.md`。要点：

1. **读取换直连，并写清老客户端为何弃用**：`client due` 实测先等 30 s 超时再回 `[]`，参数被 mapping 丢掉。
2. **判定顺序决定回执好不好看**：先判「是不是我这路的来源」再要求 `key`/`message`；反过来会把一堆正常候选
   报成 `no-key`/`no-message`，看着像故障。
3. **「缺失=跳过」还是「缺失=失败」要逐个字段问**：只有契约必需字段才 fail-close；可选字段缺失按对端口径给默认值。
4. **空响应/非目标候选 = 正常**（对端明确这么说时才改），并在 docstring 里写死口径，别只留在代码注释。
5. **测试要能注入 transport**：`run(..., transport=fake)`；注意 fixture 分支若优先于 transport，带 fixture 的用例会
   静默绕过假通道（本次踩过）。必测 `403→200` 自愈、5xx 用尽、429 `Retry-After`、坏 JSON 不重试、异常形态。
6. **已知缺口单独成段**：「查询失败时本轮该来源提醒会被跳过且无兜底」，并写「要回退需另外批准」——
   这比藏在「已按 fail-close 处理」里诚实，对方才敢批上线。
