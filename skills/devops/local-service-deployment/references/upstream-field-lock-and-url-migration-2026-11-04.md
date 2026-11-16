# 上游来源字段锁定 + 云端地址迁移（2026-11-04 实案）

承接 `sync-stall-capacity-deadlock-2026-11-04.md`：管道被服务端修好之后，同一会话里紧接着做的两件事。

---

## 一、上游来源事项：日程字段锁定，但 status 可改

### 现象

用户说「11-05 上午那条会议实际改到今天上午了」。系统里那条是上游同步来的（`source: "dingtalk"`，带 `externalId`）。

```bash
# 想直接把日期改到今天
$ cat patch_fdikuai.json
{"date":"2026-11-04","version":1,"notes":"..."}
```

回执：

```json
{"error":"请到钉钉修改工作日程；这里可以记录完成情况和关联目标","details":null}
{"operation":"patch","status":400,"recoverable":false}
```

不是 `version_conflict`，不是权限 —— 是**日程字段归上游所有**。

### 但 status 能改

```json
{"status":"cancelled","version":1,"notes":"实际已于 11-04 上午召开；11-05 该时段改为工地巡查"}
```

→ `{"status":"saved", ... "status":"cancelled", "version":2}`，HTTP 200。

### 取消 + 重建的完整流程

```
1. client patch <上游条ID>   --json-file cancel.json   --request-id <uuid>
   → status=cancelled，version+1，原 id / externalId / 标题全部保留

2. client create             --json-file create.json   --request-id <另一个uuid>
   create.json = {title, date, start, end, category:"work", mode:"binary",
                  plannedMinutes:N, source:"hermes", notes:"用户口述：..."}
   → status=saved，返回新 id

3. client items 回读：确认新条 pending、老条 cancelled，两条都在
```

实测结果：

```
11-04 09:30-12:00 | F地块讨论会（规划条件） | pending   | hermes
11-04 14:30-16:30 | 精装修讨论会           | pending   | hermes
11-05 09:30-12:00 | F地块讨论会（规划条件） | cancelled | dingtalk
11-05 10:00-11:00 | H地块设计巡查          | pending   | hermes
11-05 14:00-16:00 | F地块讨论会（商业）     | pending   | dingtalk
```

### 用户边界（明确说过）

> 「我不需要你在我的钉钉里修改工作日程，我只需要你把我告诉你的真实的工作日程在我的日程系统里修改就好了。」

→ 不要建议用户去上游改，也不要驱动浏览器改上游。本地能表达多少表达多少。

---

## 二、改完必须等一轮自然同步

`work-runner.mjs` 里 calendar 需距上次 ≥15 min 才重扫；每轮结束后 `work-host.json` 更新 `lastCalendar`。

**判据位置**：`<release>/runtime/.local/work-automation-observation.jsonl`

- 每行一轮；**只有真正跑了采集的行才带 `"calendar":{...}`**，短周期空转行是 `"calendar":null`
- 带 calendar 的那行长这样：

```json
{"startedAt":"2026-11-04T00:43:58.714Z",
 "calendar":{"runId":"...","complete":true,
   "outcomes":[{"sourceId":"...","status":"complete","added":0,"updated":0,"cancelled":0,"unresolved":0},
               {"sourceId":"...","status":"complete","added":0,"updated":0,"cancelled":0,"unresolved":0}]},
 "error":null,
 "finishedAt":"2026-11-04T00:45:43.422Z"}
```

判定：

| `outcomes` | 含义 | 动作 |
|:--|:--|:--|
| 全 0 + `complete:true` | 同步没覆盖你的改动 | 可以宣布完成 |
| 出现 `updated > 0` | 本地改动被同步改回去了 | 必须告知用户并换方案 |
| 找不到带 calendar 的行 | 这一轮还没到 or 没跑 | 继续等，不要抢答 |

⚠️ 先读 `work-host.json.lastCalendar`：距现在 <15 min ⇒ 下一轮还没来，此刻的回读**没有验证价值**。

---

## 三、云端地址迁移（旧域名 → 新域名，key 不变）

### 三处地址，各管各的

| 位置 | 内容 | 谁在用 |
|:--|:--|:--|
| `runtime/.local/hermes-cloud-connection.json` | `{url, key}` | `work-runner.mjs` 直读 → **同步链路** |
| `deployment/home.mjs` 顶部 `const publicURL='...'` | 写死的副本 | `connection()` → 卡 `preflight` / `activate` / `connection-import` |
| `manifest.json` 里 `deployment/home.mjs` 的 `sha256` + `bytes` | 组包完整性 | `verifyManifest()`，`run` 每轮先跑 |

所以会出现这种迷惑态：**连接文件被改过、home.mjs 没改 → 同步照常能跑，但 preflight 报 `Unexpected cloud connection; not changed`**。

### 对齐步骤（顺序不能反）

```bash
# 1. 备份
mkdir -p /tmp/urlfix_backup
cp <release>/deployment/home.mjs /tmp/urlfix_backup/home.mjs.bak
cp <release>/manifest.json        /tmp/urlfix_backup/manifest.json.bak

# 2. 改 publicURL（用 patch 工具改这一行常量）
#    const publicURL='https://dayflow-personal-planner.<新>.chatgpt.site';

# 3. 重算哈希写回 manifest（manifest 自身无签名，verifyManifest 只比对文件）
python - <<'PY'
import json, hashlib
p='<release>/manifest.json'; tgt='deployment/home.mjs'
m=json.load(open(p,encoding='utf-8'))
raw=open('<release>/'+tgt,'rb').read()
for f in m['files']:
    if f['path']==tgt:
        f['bytes']=len(raw); f['sha256']=hashlib.sha256(raw).hexdigest()
open(p,'w',encoding='utf-8').write(json.dumps(m,ensure_ascii=False,indent=2))
PY

# 4. 校验（文件数不变）
node <release>/deployment/home.mjs verify
# → {"verified":true,"bundleId":"...","sourceCommit":"...","files":55}

# 5. 端到端预检（只读，noCloudWrites）
node <release>/deployment/home.mjs preflight
# → {"cloudReachable":true,"items":57,"calendarBooks":2,"mailboxes":1,
#    "selectedCalendars":2,"selectedMailboxes":1,"identityMatches":true,"noCloudWrites":true}
```

### 收尾

等一轮自然 calendar 同步，确认 `work-host.json.lastCalendar` 推进且该轮 `error:null`。

---

## 四、探针脚本的最小骨架

```js
import fs from 'node:fs';
import path from 'node:path';
import {httpRequest} from 'file:///C:/.../runtime/scripts/http-request.mjs';  // 绝对 file URL

const root = 'C:/.../<release>';
const conn = JSON.parse(fs.readFileSync(path.join(root,'runtime/.local/hermes-cloud-connection.json'),'utf8'));
const cfg  = JSON.parse(fs.readFileSync(path.join(root,'runtime/.local/calendar-automation.json'),'utf8'));
if (cfg.pwshExe) process.env.PATH = path.dirname(cfg.pwshExe) + path.delimiter + process.env.PATH;
//                          ↑ 不做这一步会报 PowerShell 7 is required for Windows HTTP requests

const r = await httpRequest(new URL('/api/v1/sync/work/health', conn.url),
  { headers: { Authorization: 'Bearer ' + conn.key } });
// 只打印 status / error 文案，绝不回显 key
```

路由存在性探测用**全零 UUID**，永远不拿真实记录试写：`405 请求方法不正确` = 路由在但方法不对；`404 接口不存在` = 没这个路由。
