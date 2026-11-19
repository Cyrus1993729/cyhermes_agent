# Dayflow 73 号提醒补丁 — 暂存说明（未上线）

状态：**只暂存 + 离线验证，未替换线上脚本、未改 cron、未发任何消息。**
日期：2026-11-18（16:43 二次修订：读取改直连 HTTP）　端点：牛来端（PC-20260524NEAI）

## 文件

| 文件 | 作用 |
|:--|:--|
| `df_watch.py` | **线上原文件，零改动**（sha256 见文末） |
| `df_common.py` | **零改动**（sha256 见文末） |
| `backup_73/df_watch.py.bak_20261118_1534` | 原文件备份 |
| `backup_73/df_common.py.bak_20261118_1534` | 原文件备份 |
| `df_reminders73.py` | 新增：73 候选查询（**直连带认证 HTTP**）/ 判定 / 发送 / 去重 / ack |
| `df_watch73.py` | 新增：心跳补丁版入口（复用 df_watch 的变更检测，多一步云端候选） |
| `tests73/due73_fictional.json` | 纯虚构响应夹具（13 条候选，覆盖全分支 + 站点真实形态） |
| `tests73/test_df73.py` | 离线验收脚本（55 项，假通道 + 假 transport + 临时状态目录） |

## 读取链路（本次修订重点）

- 旧客户端（sites29 build）**不认识 `--query`**：实测 `client due` 先空等 30s 超时、再返回
  `[]`，既慢又永远为空。故读取不再走 home 客户端，改为直连云端：
  `GET {url}/api/v1/reminders/due?calendarChanges=1&lead=18`，头
  `Authorization: Bearer <hermes-cloud-connection.json 里的 key>`。
- **必须带常规 `User-Agent`**：缺 UA 时 Cloudflare 直接 403（`error code: 1010`），
  与凭据无关，加 UA 即 200。
- 代理沿用 `calendar-automation.json` 的 `httpProxy`（127.0.0.1:10808），
  可用 `HTTPS_PROXY/HTTP_PROXY` 覆盖；连接文件可用 `DAYFLOW_CONN_FILE` 覆盖。
- 只读重试：最多 2 次，重试条件 = 传输异常 / 403 / 408 / 425 / 429 / 5xx；
  429 优先按 `Retry-After` 等待（上限 5s）。坏 JSON 与 4xx 鉴权失败不重试。

## 行为契约（照需求书落地）

1. 每轮独立查询 `GET /api/v1/reminders/due?calendarChanges=1&lead=18`（直连，见上）。
2. **只接管 `source=dingtalk`**；source 缺失或非钉钉一律不动，继续走旧快照路径。
3. 旧快照**不再**发钉钉会前提醒；`sourceLifecycle` = cancelled / pendingReschedule 等失效态不兜底。
4. 字段按实际格式容错：`kind` 缺省 = 普通会前，`kind=calendar-change` = 改期通知（无时间窗，按 key 去重）；
   `sourceLifecycle`、`leadMinutes` 都可以不存在；普通候选的提前分钟由 `date`+`start`
   与**北京时间**现算，不依赖主机时区；`message`/`path`/`key` 只在钉钉候选上是必须字段。
5. 普通候选守原 **[13,18] 分钟**窗口（= LEAD 15 的 -2/+3）。
6. 消息 = 响应 `message` + 同站 `path`（拼 `SITE_BASE`），交既有 `df_common.send`（微信优先、私人 TG 兜底，收件人不变）。
7. **渠道成功 → 才落本地去重 → 再 POST ack**（`{"key":…}` + 稳定 `Idempotency-Key`=uuid5(key)）。
   ack 失败：进 `pending_ack_<date>.json`，下一轮**只补 ack、绝不重发**。
8. 常规候选同时写旧键 `本地事项ID|开始时间|日期`，因此**回滚到 df_watch.py 不会重复提醒**。
9. **空列表、只有非钉钉候选 = 正常响应**（Sites43 实际行为），`ready=true`、零发送、不算故障。
   只有「HTTP 失败」或「响应既不是数组也没有数组字段」才算未就绪 → 失败关闭，不读旧快照。
10. 干跑 `DAYFLOW_DRY=1`：只打印消息文本，不落盘、不 ack、不发渠道。

## 验证结果

```
DAYFLOW_DRY=1 python tests73/test_df73.py   → PASS 55 / FAIL 0
python test_df.py（原回归）                  → 全部通过
python -m py_compile（两个新文件 + 测试）     → OK
```

分区：A 干跑 / B 判定分支（含北京时区口径与窗口边界）/ C 去重与旧键兼容 / D ack 语义 /
E 直连读取路由与重试（403→200 自愈、5xx 重试、Retry-After、传输异常、坏 JSON、异常形态）/
F 空列表与只有非钉钉候选 / G 与旧脚本分工 / H 线上文件哈希。

真机只读探测（`DAYFLOW_DRY=1`，只 GET，不发消息）：

| 探测 | 结果 |
|:--|:--|
| `due?calendarChanges=1&lead=18` | HTTP 200，`[]`，`ready=true`，零发送 |
| `due?calendarChanges=1&lead=1440`（开发端 24h 窗） | HTTP 200，**4 条候选**，字段仅 `[date,end,itemId,key,start,title]` → 全部 `source-empty` 跳过，零发送 |
| 旧客户端 `client due` | 30s 超时后返回 `[]`（已弃用，不再参与） |

## 上线步骤（等确认后）

1. 改心跳 cron 的 `script`：`dayflow/df_watch.py` → `dayflow/df_watch73.py`。
   其余（每 5 分钟、`deliver=local`、脚本内自发微信）不动。
2. 观察一轮真日志：`watch73 ... pushed=...,r73:ready/sent=…`。
3. 等 Sites43 开始下发 `source=dingtalk` 候选（含 message/path）后，钉钉会前提醒才真正接管。

## 回滚

cron 的 `script` 改回 `dayflow/df_watch.py` 即可 —— 本次未改线上任何文件，
`df_reminders73.py` / `df_watch73.py` 留着不引用无副作用。

## 已知缺口（明确记录，不是猜）

- 查询失败（HTTP 层挂了）时本轮钉钉会前提醒会被跳过且无快照兜底 —— 这是「旧快照不再发钉钉」
  这条规则的直接后果。若要求失败时回退到快照路径，需要另外批准，本补丁不做。
- 服务端目前对 18 分钟窗返回空、24h 窗返回的 4 条都不带 `source`，即**尚无钉钉候选可比对**；
  钉钉链路的端到端真机验证要等 Sites43 真正下发钉钉候选。

## 未定项

- 候选字段拼写的容错别名集中在 `normalize()` 一处，实测字段名不符只需改那里。
- `SITE_BASE` 取 `home.mjs` 里的 `publicURL`（公开站点地址，不含凭据）。
- ack 的幂等语义以服务端为准：本端用 `uuid5(key)` 保证同 key 同键。

## 哈希（sha256）

见 `HASHES_73.txt`（由 `sha256sum` 现场生成）。
