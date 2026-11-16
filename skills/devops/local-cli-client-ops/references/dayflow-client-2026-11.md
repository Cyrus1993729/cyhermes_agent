# Dayflow `home.mjs client` 实测证据（2026-11-04）

本文件只存**实测证据**，业务口径见 `dayflow-personal-planner`。

## 入口

```bash
N="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
M="C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/deployment/home.mjs"
"$N" "$M" client items > items.json
```

## 证据一：`client items` 是两行 JSON

`head -c 300 items.json`：
```
[{"id":"f6d5114a-9d35-424b-8257-9829df3f115c","title":"F地块讨论","date":"2026-10-09",...
```

`tail -c 400 items.json`：
```
..."sourceLocation":""}]
{"requestId":"","operation":"items","attempt":1,"durationMs":1807,"totalMs":1807,"status":200,"recoverable":false}
```

直接 `json.load(fp)` → `JSONDecodeError: Extra data: line 2 column 1 (char 29642)`。

正确解析：
```python
import json
d = json.loads(open('items.json', encoding='utf-8').readline())
rows = [i for i in d if i.get('date') == '2026-11-04']
for i in rows:
    print(i['id'], i['title'], i['status'], i['version'])
```

## 证据二：短 id patch → 404 事项不存在

```bash
# 错：把回读时打印的短 id 直接拿去用
"$N" "$M" client patch bcd9a23a --json-file cancel.json --request-id <uuid>
# → {"error":"事项不存在","details":null}   status:404

# 对：用完整 UUID
"$N" "$M" client patch bcd9a23a-3f9b-4946-92f1-449691691e9d \
  --json-file cancel.json --request-id <uuid>
# → {"status":"saved","result":{...,"status":"cancelled","version":2,...}}
```

## 证据三：钉钉来源事项的字段锁粒度

- `patch {date/start/end}` → 服务端拒绝：「请到钉钉修改工作日程；这里可以记录完成情况和关联目标」
- `patch {status:"completed"}` → **成功**，回执带 `"completedDate":"2026-11-04"`

→ 钉钉来源的**标题/日期/时间**由官方同步维护，**完成状态可本地改**。

2026-11-04 复测（改次日 11-05 的 `F地块讨论会（商业）` 14:00–16:00 → 14:00–15:00）：
带 `version:1` 的 `patch {date,start,end,plannedMinutes,notes}` 依旧 400 同一句文案，
`recoverable:false`、`attempt:1`、`durationMs:1950`——**确认不是网络/版本问题，重试无意义**。
同一次会话里的两条 `create`（hermes 源）均 200 成功，证明被挡的只有同步源条目本身。

处置：不补建重复条目，把回执原文 + 当天完整清单给用户，给「去钉钉改 / 我建本地副本（会重叠）」两个选项。

## 证据四：批量三条写操作

一次执行里连做「取消一条 + 完成两条」，每条独立 UUID，各自回读：

```bash
"$N" "$M" client patch <full-uuid-1> --json-file cancel.json --request-id a34083a2-...
"$N" "$M" client patch <full-uuid-2> --json-file done.json   --request-id 84aaac0a-...
"$N" "$M" client patch <full-uuid-3> --json-file done.json   --request-id a9579575-...
```

三条均 200 `{"status":"saved"}`，version 1→2，回读状态全部到位。

用户没说实际时长时**不记 execution**，只改 status（避免污染时间统计）。

改完当天日程**必须**刷新快照，否则心跳会再推一次重复的「已更新」：
```bash
python "C:/Users/Administrator/AppData/Local/hermes/scripts/dayflow/df_snapshot.py"
# → snapshot refreshed: N items on <date>
```
