# 受控写入验收实录（Dayflow Home HD.4，2026-10-21）

协调端任务书：只测 Hermes 现有客户端写入通道，不碰调度、不跑 Install-HomeTask/work-runner、不重登、不向 Telegram 发消息。固定根 `C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1`，仅用自带 Node24 调 `deployment/home.mjs client …`（其内部读 `runtime/.local/hermes-cloud-connection.json`，密钥绝不出现在命令/输出里）。

## 调用链（读源码确认，非猜测）

`deployment/home.mjs` 的 `client` 分支 `spawnSync` → `runtime/scripts/hermes-cloud.mjs`（补 `--connection`）→ `runtime/scripts/hermes-local.mjs`（解析 `--json-file` / `--request-id`，把 request-id 塞进 env `DAYFLOW_REQUEST_ID`）→ `runtime/scripts/hermes-client.mjs`（真正发请求，`Idempotency-Key: $DAYFLOW_REQUEST_ID`）。

- 无参数 `client` 打印：`支持 state/items/create/patch/execution/review/goal/draft/confirm/due/ack。写入内容从标准输入读取 JSON，幂等标识用 DAYFLOW_REQUEST_ID。`
- `client create --help` / `client patch --help` → `{"error":"请求必须是 JSON"}`（`--help` 不是 flag，脚本改读 stdin 的空输入）。**这是参数解析行为，不是接口故障。**

## 实际执行序列

```bash
cd <release>
N="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
"$N" deployment/home.mjs client state > runtime/.local/hd4-state-before.json
# 生成基线清单：id/version/status/category/source + sha256(title) 前 12 位
"$N" deployment/home.mjs client create --json-file <payload.json> --request-id 5f5db859-…4155b
"$N" deployment/home.mjs client create --json-file <同文件>     --request-id 5f5db859-…4155b   # 幂等重发
"$N" deployment/home.mjs client items  > runtime/.local/hd4-items-after-create.json
"$N" deployment/home.mjs client patch <测试ID> --json-file <patch.json> --request-id be260f98-…09493a
"$N" deployment/home.mjs client patch <测试ID> --json-file <同文件>      --request-id be260f98-…09493a
"$N" deployment/home.mjs client state > runtime/.local/hd4-state-after.json
```

create 正文（UTF-8 文件，落 `runtime/.local/`）：

```json
{"title":"[部署验收61] 牛来端客户端连通测试","date":"2099-01-01","start":"","end":"",
 "category":"life","mode":"binary","source":"hermes",
 "notes":"仅用于家中部署读写与幂等验收，不是真实安排；验收后取消。"}
```

patch 正文：`{"version": <最新实际version>, "status": "cancelled"}`。

## 实测回执要点

- create，两次（同正文同 request-id）→ 两次 `result.id` 完全相同（`fd692f99-…910b`）、`version:1`、`status:"pending"`、`source:"hermes"` 被接受。
- items 回读：总数 26 → 27，该标题匹配 **1 条**。
- patch，两次（version 1 → cancelled）→ 两次同 id，`version:2`、`status:"cancelled"`；第二次 version 不再自增。
- state 比对：原 26 条 missing=0 / changed=0；goals 2→2（含 archived 那条 version 未变）；reviews 0→0；executions 总数 0；actualMinutes 合计 0；revision 47002→47012。
- 落盘：`hd4-state-before.json`、`hd4-baseline-manifest.json`、`hd4-create-payload.json`、`hd4-create-{1,2}.out`、`hd4-items-after-create.json`、`hd4-patch-payload.json`、`hd4-patch-{1,2}.out`、`hd4-state-after.json`、`hd4-compare.json`；`icacls runtime/.local` = `SYSTEM` + 本人（真收紧）。

## 字段口径

- 「无固定开始/结束时间」= `start:""` / `end:""`（真实库里既有的无时间事项就这么存），不要传 null、不要猜时间、不要传 `allDay` 赌接口。
- `category` 必须取 state 里已出现的真实值（本次 work/life/side/sport，用了 life），不新建分类。
- `source` 除既有 dingtalk/manual/mail 外，`hermes` 也可用（本机录入/验收测试项）。

## 回执形态（对方按结构读）

测试 ID → 相同 ID 重复布尔 → cancelled 状态 → 原数据保持布尔 → 最终计数（items/goals/reviews/executions/actualMinutes/revision 前后）→ 成功时间（`YYYY-MM-DDTHH:MM:SSZ` + 北京时间）→ 落盘文件清单 → 一句口径说明（如 `--help` 报错的正常性）。全程不出现密钥、不出现任何真实日程标题。
