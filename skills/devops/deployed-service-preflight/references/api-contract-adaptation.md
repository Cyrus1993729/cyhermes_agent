# 把 fail-close 补丁改成「格式自适应」（Dayflow 73b，2026-11-18）

前置：第一轮只读预检判定契约不匹配（见 `live-endpoint-shape-diff.md`），对端回来说
「沿用它已验证能直连的带认证 HTTP 请求，按实际格式兼容」。仍**未启用**、**不改 cron**、**不发通知**。

## 1. 读取：直连带认证 HTTP（不再用老客户端）

```
GET  {url}/api/v1/reminders/due?calendarChanges=1&lead=18
Authorization: Bearer <hermes-cloud-connection.json.key>
User-Agent: <任意常规 UA>          ← 缺它就 403 error code: 1010
Accept: application/json
```

- 连接文件定位：`<root>/releases/*/runtime/.local/hermes-cloud-connection.json` 取 mtime 最新，
  可用 `DAYFLOW_CONN_FILE` 覆盖（release 升级换目录不用改代码）。
- 代理：同目录 `calendar-automation.json` 的 `httpProxy`（`http://127.0.0.1:10808`），env 可覆盖；
  不用代理时要**显式** `ProxyHandler({})`，否则 urllib 会悄悄读 env。
- 老客户端为什么弃用：`client due` 先 `transport_timeout` 30 s、重试一次，最后返回 `[]` —— 慢且恒空，
  参数 `--query` 被 mapping 丢掉。

## 2. 只读重试策略（与 home 客户端对齐，别自己发明）

| 情形 | 动作 |
|:--|:--|
| 传输异常 / 403 / 408 / 425 / 429 / 5xx | 重试，最多 2 次；429 按 `Retry-After`，上限 5 s |
| 坏 JSON | 不重试，`error=bad-json` |
| 其它 4xx（401/404…） | 不重试，失败关闭 |
| HTTP 层失败 | **fail-close**：本轮不读旧快照、不发消息（旧快照已剔除该来源，这是规则不是 bug） |

403 要进重试列表：边缘层瞬时拒绝（1010）是真实出现过的形态，重试一次很便宜；鉴权失效一般是 401。

## 3. 字段→行为映射（本次对端给的实际口径）

| 字段 | 缺失/取值 | 行为 |
|:--|:--|:--|
| `source` | **必须** `dingtalk` 才接管 | 缺失 = 非钉钉候选 → 跳过，且**不再要求 key/message/path** |
| `kind` | 缺失 = 普通会前 | `calendar-change` = 改期，无时间窗，按 key 去重 |
| `sourceLifecycle` | 可缺失 | 有值时 cancelled/pendingReschedule 等一律不兜底 |
| `leadMinutes` | 可缺失 | 缺失则由 `date`+`start` 与**北京时间**现算 |
| `message`/`path`/`key` | **仅钉钉候选必须** | 缺失 → `no-message`/`no-key`，只在 dingtalk 上生效 |
| 空列表 / 只有非钉钉候选 | — | **正常响应**：`ready=true`、零发送、无 error |
| 既不是数组也无数组字段 | — | `unexpected-shape` → fail-close |

顺序有语义：**先判 source 再判 key/message**。反过来的话，4 条只有 `{date,end,itemId,key,start,title}` 的
真实候选会全报 `no-key`/`no-message`，看着像故障；先判 source 就变成干净的 `source-empty` ×4。
提前分钟用固定 `timezone(timedelta(hours=8))` 换算，naive `now` 视为北京本地，不依赖主机时区。

## 4. 测试怎么写（全虚构，零联网）

- 夹具造**真实形态**：4 条只有 `date/end/itemId/key/start/title`（无 source）+ 若干 dingtalk 候选（含缺 kind、
  缺 lifecycle、缺 leadMinutes、缺 message、cancelled、客串 hermes 源、旧键重复）。
- 读取链路用**注入的假 transport**：`query_due(fixture=None, transport=fake)`，`run(..., transport=fake)`。
  ⚠️ 若 `run()` 里 fixture 分支优先于 transport，带 fixture 的测试会**静默绕过 transport**（本次先踩再修）。
- 必测的传输结局：`403→200`（2 次调用自愈且仍打同一路由）、5xx 两次用尽→fail-close、429+`Retry-After=3`
  （把 `time.sleep` 换成记录器，断言 `[3.0]`）、`Retry-After=120` 截断到 5、status=0 传输异常、
  200 坏 JSON（断言只调 1 次）、200 但形态不认识。
- 保留原失败重试段（ack 失败进 `pending_ack_<date>.json`、下轮只补 ack 不重发、渠道失败不落去重不 ack）。
- 线上零改动用哈希段兜住（`df_watch.py`/`df_common.py` vs `backup_*/`）。

## 5. 回执与交付

- `RECEIPT_<N>.json` 里加 `readPath`（老客户端为何弃用、新路由、必需头、代理、重试表）、
  `formatCompat`（逐字段口径）、`liveReadOnlyProbes[]`（路由/status/条数/跳过原因）、`stagedNotInstalled` 逐文件 SHA256。
- 单独一节记**已知缺口**：「查询失败时本轮该来源提醒会被跳过且无兜底」，并写明「要回退到快照路径需另外批准」——
  这比埋在一句「已按 fail-close 处理」里诚实，对端也才敢批上线。
- 不打印 key/url/日程正文；探针只输出字段名、条数、跳过原因、跳过原因分布。
- 上线仍是一步显式动作：改 cron `script` → 观察一轮 `r73:ready/sent=…`；回滚就是改回去。

## 6. 复用检查单

1. 直连探针带 UA（`scripts/probe-api-shape.py`），先确认 200 再谈字段。
2. 每个字段问一句「缺失时应该跳过还是失败」——跳过=业务，失败=契约；只有后者才 fail-close。
3. 空响应到底算「正常空」还是「未部署」，必须由对端明确；拿到口径后写进 docstring，别留在代码注释里。
4. 测试要能被 transport 注入，否则只测了夹具。
5. 交付时把「没做什么」（不改 cron、不发通知、不联网写）与「还缺什么」分开写。
