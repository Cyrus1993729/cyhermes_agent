# Dayflow 事项写入：做图前常踩的数据侧坑

来源：2026-10-25 Telegram 端实测。客户端调用方式本身见用户自有 skill `dayflow-personal-planner`，这里只记**改数据时影响出图正确性**的坑。

## 1. 多日/全天事项 vs 每天定点

- 建多日全天：一次 create 传 `{"date":"D1","endDate":"D2","allDay":true}`，start/end 留空，`plannedMinutes` 为 0。图上呈顶部横跨两列的横幅。
- 用户想改成“每天 09:00–17:30”时：
  - `client patch <id>` 传 `{"version":N,"date":"D1","start":"09:00","end":"17:30","allDay":false,"endDate":null}` —— **实测能清掉 endDate 与 allDay**，事项变回单日定时。
  - 剩下那一天**要单独 create 一条**，一次 patch 搞不定两天。

## 2. 🔴 patch 改 start/end 后 plannedMinutes 不重算

改完时间，回执里 `plannedMinutes` 仍是 0。需补一次 `client patch <id> {"version":N+1,"plannedMinutes":510}`。
不做的话时长统计是错的（图上不显，但周复盘会难看）。

## 3. 🔴 新建撞 `409 schedule_conflict`

回执形如：
```json
{"error":"这个时间已有安排，请确认是否保留重叠",
 "details":{"type":"schedule_conflict","items":[{"id":"...","title":"...","start":"14:00","end":"17:00"}]}}
```

**顺序很重要**：
1. 先 patch 把冲突项 `status=cancelled`
2. 再用**完全相同的 request-id 和 JSON** 重试 create —— 实测第二次就成功，且不重复建

不要为了绕冲突换新 request-id，也不要偷偷改时间掩盖冲突。真实冲突要摆给用户选。

## 4. 取消 ≠ 删除

`client patch <id> {"version":N,"status":"cancelled"}`，notes 里写清谁在何时要求取消、原因。取消后 `client items` **仍然返回它**，做图时必须按 `status != "cancelled"` 过滤掉——用户说“不要在系统里显示”指的就是这个。
