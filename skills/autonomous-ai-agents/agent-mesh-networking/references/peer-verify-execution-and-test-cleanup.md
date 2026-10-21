# 对端请你核查「另一通道指令是否执行」并取消测试项

2026-10-21 实案：用户在 Codex 确认自己直接向本机 Telegram 发了一条 dayflow 指令（查明天安排 + 建 2099-01-02 无固定时间测试待办），对端（另一台机的独立 agent）转来请求：核查是否收到/是否真查询/是否真保存，授权确认后取消该测试项，并给了固定 request-id。

## 处理顺序（照做，别跳）

1. **先认清语义**：A2A 这条消息是**核查请求**，不是创建请求。用户的原指令只在他的 Telegram 会话里跑过一次；你在 A2A 侧再建一次 = 重复入库。
2. **收到没**：`grep -a 'inbound message' gateway.log | grep <本人chat_id> | tail` → 比对 `msg='...'` 与原文标题。
3. **跑完没**：同文件找 `response ready: platform=telegram chat=<id> time=Ns api_calls=N response=N chars`，看是否伴随 `Suppressing normal final send ... content_delivered=True`。没有 response ready = 还在处理中，只能报「进行中」。
4. **真调了接口没**：查 `state.db` 的 tool 行回执（query 命中条数、`{"status":"saved","result":{...}}`、回读命中条数），不认 assistant 自述。
5. **唯一性**：从真实 API 重新拉全量（如 `client items`），按 **日期 + 标题** 双条件筛，确认目标库里只有这一条测试项；标题相近但日期不同的历史测试项要点出来「未动」。
6. **取消**：`client patch <id>` / `PATCH items/<id>`，body `{"version":<当前>,"status":"cancelled"}`，request-id 用对端给的固定值；回执应 `status:"saved"` 且 version+1。
7. **回读**：再拉一次真实数据源，按 ID 命中确认 status/version 已变；顺带报总数与 pending/cancelled 计数，证明其它真实事项未被动过。
8. **不动的东西要主动申明**：未重启网关、未动调度、未代建、未主动再发 Telegram（原会话自己会回）。

## 本次实测证据链（可复用的判据形态）

| 环节 | 回执形态 | 结论 |
|:--|:--|:--|
| 收到 | `inbound message: platform=telegram user=<名> chat=8938729624 msg='请使用 dayflow-personal-planner …'` 08:08:09 | true |
| 查询 | tool 回执「全部事项数: 27 / 明天 2026-10-22 未取消事项: 1」08:09:21 | true（真调 API） |
| 保存 | `{"status":"saved","result":{"id":"3030d4d0-…","status":"pending","version":1}}` 08:09:34 | true |
| 回读 | 「回读命中条数: 1」+ 当日全部事项:1 08:09:42 | true |
| 原任务状态 | `response ready: time=102.9s api_calls=13` + `content_delivered=True`，正文末尾在问「要不要现在取消」 | 已完成，等用户对取消的回复 |
| 取消 | patch 回执 `saved`，version 2，status cancelled | 成功 |
| 取消回读 | items 里该 ID 命中 1 条，cancelled/version=2；总数不变 | 成功 |

## 坑

- 别把「对端刚才读取时没看到」当成失败判据。本次对端称 00:12Z 读取未见，而本机创建回执是 00:09:34Z —— 创建早于读取却可见性不一致。正确做法：**报时间线冲突，请对端重读**，并提示可能是读端点/home scope/边缘缓存差异；不要替对端下结论，也不要因此重建成「让它看见」。
- 标题相似的历史测试项（如 2099-01-01 的同类验收项，早已 cancelled）要单独说明「上一轮遗留、未动」，否则对端会以为重复。
- 回执里不贴真实日程/邮件正文。本次只报「明天命中 1 项」，不列标题时间，也不泄任何连接凭据。
- 时间基准：主机 `date` 报的是 UTC 却常被标成 GMT；北京时间 = +8h。所有「明天/今天」的解析都用北京时间，并把参考日期写进回执（如「明天 = 2026-10-22」）。
