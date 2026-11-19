# 线上端点形状取证的实测记录（Dayflow 73 vs Sites43，2026-11-18）

用途：解释「离线测试全过、线上却一条也发不出去」这类**契约错配**怎么在只读阶段查出来。
对应 SKILL.md 的「`200 []` 的三种成因怎么分开」一节。

## 1. 客户端调用链（Dayflow 家主机，`releases/sites29-afdf902-home1`）

```
scripts/dayflow/df_common.py client(op, extra)
  → node deployment/home.mjs client <op> ...
    → runtime/scripts/hermes-cloud.mjs        (只转发，加 --connection)
      → runtime/scripts/hermes-local.mjs      (读连接文件，铺 DAYFLOW_URL/API_KEY/REQUEST_ID)
        → runtime/scripts/hermes-client.mjs   (op→method/route 映射，真正发请求)
```

`hermes-client.mjs` 的映射是固定的（`due:['GET','reminders/due']`），**没有 query 参数处理**：
`grep -c -- '--query'` = 0，多余 argv 直接丢。所以补丁里写「带 `--query calendarChanges=1&lead=18`」
在本机等于没带。

## 2. 裸请求为什么不行

- python `urllib` 只带 `Authorization: Bearer <key>` → `403`，body `error code: 1010`（Cloudflare 边缘挡 UA/指纹）。
- **🔴 2026-11-18 16:40 复核修正：真正的区分项是 `User-Agent`，不是「urllib 这个库」。** 同一把 key、同一条路由，
  加一行 `User-Agent: DayflowHome/1.0` 后 python `urllib` 直接 **200**（`/api/v1/state` 47 KB、
  `/api/v1/reminders/due?lead=1440` 200 4 条）。所以「必须走 release 自带传输层」说得过重：
  缺 UA 时**任何**客户端都会 403/1010（含裸 fetch）；带上常规 UA 后裸 stdlib 也能读。
  只有需要 pwsh 那条链路时（如 `spawn('pwsh')` 的其它能力）才必须前置 `tools/pwsh7` 到 `PATH`。
  看到 `error code: 1010` 先补 UA 再怀疑 key/接口——这个错与鉴权无关。
- 连接配置与代理的定位（不用手抄路径）：
  `DayflowHome/releases/*/runtime/.local/hermes-cloud-connection.json`（取最新 mtime，可用 `DAYFLOW_CONN_FILE` 覆盖），
  代理取同目录 `calendar-automation.json` 的 `httpProxy`（实测 `http://127.0.0.1:10808`），
  `HTTPS_PROXY`/`HTTP_PROXY` 可覆盖。回执里只说「用了连接文件」，不打印 url/key。

## 3. 参数扫描结果（同一天、同一把 key）

| 路由 | status | 条数 | 字段并集 |
|:--|:--|:--|:--|
| `/api/v1/reminders/due` | 200 | 0 | — |
| `?calendarChanges=1&lead=18` | 200 | 0 | — |
| `?lead=20/30/60/120` | 200 | 0 | — |
| `?lead=600` | 200 | 1 | `date,end,itemId,key,start,title` |
| `?lead=1200` | 200 | 2 | `date,end,itemId,key,start,title` |
| `?calendarChanges=1&lead=1200` | 200 | 2 | 同上（无 `kind`，改期通道没体现） |
| `/api/v1/items` | 200 | 98 | `id,source,sourceLifecycle,status,start,end,date,title,version,…` |

结论链：`lead` 被服务端解析（放大才出数据）⇒ 服务端在线、参数通道可用；
但候选字段缺 `source/kind/sourceLifecycle/message/path/leadMinutes` ⇒ **不是补丁期望的 73 契约**。
本地 release 仍是 sites29 build（客户端不认 `--query`）是另一半原因。

## 4. 为什么这会让补丁「静默全停」

`df_reminders73.classify()` 的顺序：

1. `key` 空 → `no-key`
2. `source != 'dingtalk'` → `source-empty`（线上无此字段，恒命中）
3. `lifecycle in LIFECYCLE_BLOCK` → 不阻断（字段空）
4. `message` 空 → `no-message`
5. 去重命中 → `dup-key` / `dup-legacy`
6. `kind=calendar-change` 无窗口直接发；否则 `[13,18]` 分钟窗口

而 `df_watch73.snapshot_reminders()` 已经把 `source==dingtalk` 从快照路径剔掉（钉钉会前提醒整体交给云端候选）。
两件事叠加：旧路径不发、新路径全跳过 ⇒ **钉钉会前提醒全部消失，且日志只写 `r73:ready/sent=0/skip=N`，不报错**。

## 5. 离线测试为什么发现不了

`tests73/due73_fictional.json` 和 `test_df73.py` 的夹具是照补丁**自己的**契约写的
（`key/kind/source/sourceLifecycle/itemId/start/date/leadMinutes/message/path` 全字段），
38 项全绿也只证明「补丁内部逻辑自洽」。契约对不对，只能拿线上真实响应比字段。

## 6. 当时的处置（可作为同类任务的模板）

- 跑完 `DAYFLOW_DRY=1 python tests73/test_df73.py` → PASS 38 / FAIL 0；`py_compile` 两个新脚本通过。
- 只读扫描四组参数 + 字段比对 → 判定契约不匹配。
- **不安装**：`df_watch.py` 保持原样（sha256 `913967…` == `backup_73/df_watch.py.bak_20261118_1534`），
  cron 任务 `1b3cca2ebcd9`（every 5m，deliver=local）不动。
- 落 `scripts/dayflow/RECEIPT_73.json`：`testsPassed:true` / `enabled:false` / `enabledReason`（写成缺哪几个字段）/ 
  `currentScript`+`originalBackup` 的双 SHA256 / `cronEntry.changed:false` /
  `checks{dingtalkSnapshotNoPreMeeting:true, ackRetryNoResend:true, liveDueReadiness:false}` /
  `nextStepNeeded` 给两条路线（下发新版 home 包，或批准 `due.itemId → /items` 回查适配）。
- 回话只给 3 行结论：未切换 + 阻塞事实 + 下一步二选一（对端前两次因长回复超时）。

## 7. 复用检查单

1. `grep -c -- '<flag>' <release>/runtime/scripts/hermes-client.mjs` —— 本地客户端认不认补丁传的 flag。
2. `scripts/probe-endpoint-shape.mjs` 跑裸路径 + 放大窗口 + 改期参数三组（或 `scripts/probe-api-shape.py`，不用 pwsh）。
3. 把线上字段并集抄下来，跟补丁 `normalize()/classify()` 读的字段逐个对，缺一个就写进阻塞项。
4. 补丁是否 fail-close（是否已剔除旧路径）——是则缺字段等于功能停摆，不是降级。
5. 回执里 `testsPassed` 与 `enabled` 分开；现网文件与备份哈希仍相等要单独列一次。

## 8. 第三轮只读探测（2026-11-18 16:40–16:43，带 UA 的 python urllib）

| 路由 | status | 条数 | 字段 |
|:--|:--|:--|:--|
| `due?calendarChanges=1&lead=18` | 200 | 0 | — |
| `due`（裸路径） | 200 | 0 | — |
| `due?calendarChanges=1&lead=1440` | 200 | **4** | 每条都只有 `date,end,itemId,key,start,title`（无 `source`） |
| `client due`（老客户端） | — | 0 | 先 `transport_timeout` 30 s，重试后 200 `[]` |

结论修正：服务端**确实**解析 `calendarChanges`/`lead`（18 分钟窗现在真为空，放大到 1440 才出 4 条），
所以「参数被丢弃」只在**客户端**这一层成立；直连 HTTP 时参数是生效的。
这直接导致补丁设计转向：读取改成直连 + 把 `source` 缺失定义为「非钉钉候选」而不是「未就绪」，
详见 `references/api-contract-adaptation.md`。
