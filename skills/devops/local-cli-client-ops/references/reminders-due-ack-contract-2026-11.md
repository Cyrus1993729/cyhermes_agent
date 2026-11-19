# Dayflow 提醒 due/ack 契约核查（2026-11-18，A2A 73 号 A08 联调）

任务形态：对端要求**只读确认**「提醒适配器换到云端 due/ack」的可行性与缺口，不装、不改 cron、不发消息。
结论：**契约未上线，维持现状**。

## 1. 客户端能力边界（`runtime/scripts/hermes-client.mjs`）

- mapping 里已有 `due:['GET','reminders/due']`、`ack:['POST','reminders/ack']`。
- **route 是常量**，`args[0]` 只被 `models-test-status` / `category-patch` / `category-delete` / `confirm` 用
  ⇒ 客户端**传不了查询参数**。`?calendarChanges=1&lead=18` 必须自建探针（`scripts/probe-auth-get.mjs`）。
- `hermes-local.mjs` 的 stdin 白名单：`state/items/due/categories/category-delete/models/models-catalog/models-test-status`
  免 stdin；`ack` 属写命令 → 必须 `--json-file` + `--request-id`。
- 连接文件只有 `{url, key}`（无 siteToken 也能跑）；`home.mjs.connection()` 校验 `url === publicURL` + key 正则，
  `get(route)` 用 `c.url+'/api/v1/'+route` 字符串拼接（所以 query 能过去），但两者都**未 export**。

## 2. 线上实测（只读 GET，2026-11-18 15:06 CST）

| 请求 | 状态 | 结果 |
|---|---|---|
| `/api/v1/reminders/due` | 200 | `[]` |
| `?calendarChanges=1&lead=18` | 200 | `[]` |
| `?lead=abc`（非法值） | 200 | `[]` |
| `?bogus=1`（胡编） | 200 | `[]` |

⇒ 服务端**不解析也不校验**任何查询参数。契约确实未上线（不是「支持但没数据」）。
本地镜像 `runtime/lib/domain.ts:164 dueReminders()` 与之一致：无视 query，提前量取
`state.settings.reminderMinutes`（`settings.patch` 限 0–1440，默认 30），返回项仅
`{key, itemId, title, date, start, end}` —— **无 message / path / source / calendarChange**。

## 3. df_watch.py 逐函数边界（172 行，cron every 5m，deliver=local，投递在脚本内）

| 行 | 函数 | 职责 |
|---|---|---|
| 21-26 | `_start_dt(day,hhmm)` | "HH:MM"→datetime，失败返 None |
| 29-41 | `_slim(item)` | 快照投影 10 字段（含 `source`/`sourceLocation`） |
| 44-63 | `diff_items(old,new)` | added/dropped/changed；取消过滤 3 处：新增但已 cancelled 不算 added(50)、旧非取消→新取消记 dropped(54)、新列表缺失且旧非取消记 dropped(61) |
| 66-83 | `build_update_message(...)` | 【变动】头 3 条 + `build_today_message(reason="update")` |
| 86-168 | `main()` | 静默时段(90-92) → 刷新判定(94-99) → 建基线/比对(102-116) → 提醒候选(119-136) → 发送+去重(138-163) → 日志(165) |

- 刷新：`snap is None or age >= SNAPSHOT_TTL_MIN(15)` 才拉 `get_items()`；新鲜则不碰云端。
- 提醒候选：status∈(pending,partial)、start&end 齐全、`13 <= lead <= 18`（LEAD_MINUTES=15，±2/+3）、去重键 `id|start|day`。
- 成功回执：`send()` 返 ok 才写 `reminded_<date>.json`；微信失败转 TG 仅 ok=True 算成功。

## 4. 六处最小改动点

1. 99 行前插 due 拉取（建议独立 `_dingtalk_due(now, day)`）。
2. 131 行窗口判定加分支（calendar-change 无窗口限制）。
3. 123 行加 `source` 过滤，否则钉钉事项本地也会被提醒（双发）。
4. 133 行去重键需同时保留服务端 key（ack 用）。
5. 160-163 落盘后再 ack；ack 失败要留可重试标记。
6. 94-99 云端读取整体加 try/except（现在 `get_items()` 抛 RuntimeError 会让整轮 traceback 退出，连非钉钉提醒都不发）。

## 5. 缺口（按严重度）

1. **契约不存在**：无 message/path/source/calendarChange，无法「直接用返回的 message 和 path」。
2. **ack key 不同构**：`id:date:start:reminderMinutes` vs `id|start|date`；lead 或 start 一变键就变 → 改期二次提醒。
3. **窗口语义冲突**：服务端只给 `[start-lead, start)`；本机 [13,18] 是「提前量落在 13–18 分钟」。df_watch **没有钟点 13/18 配置**（只有 QUIET_START=0 / QUIET_END=6）。
4. **双发/漏发**：跳过 `source=dingtalk` 必须「仅在 due 成功时跳过」；否则云端挂 + 快照新鲜(<15min) 会漏，反过来 due 失败还发快照项就双发。
5. **发送能力**：`send()` 只吃纯文本、>900 截断、无附件；相对 path 只能拼成绝对链接塞正文。
6. **去重格式**：`reminded_<date>.json` 值是 ISO 字符串，扩成对象需兼容当天已有文件/跨零点。

## 6. 可直接用的现成件

`client due` 免 request-id；`ack` 必须 `--request-id`；`df_common.client(op, extra, payload, request_id)` 两者都能调；
快照已存 `source` 可过滤；先发后记去重已存在；微信优先+TG 兜底+900 字截断在 `send()`；
`reminded_<date>.json` 仅 df_watch 读写（已 grep 确认），可安全扩字段。

## 7. 下一轮应向云端索要的四项确认

1. due 响应字段清单（message / path / source / calendarChange）。
2. calendar-change 的判定规则与 ack key 规则（改期后旧 key 是否失效）。
3. `lead` / `calendarChanges` 非法值应返回 400，而不是静默忽略。
4. ack 重复提交的幂等语义。
