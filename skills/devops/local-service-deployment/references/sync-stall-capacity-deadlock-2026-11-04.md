# 常驻同步任务停摆：容量型死锁排查（2026-11-04，Dayflow 家庭同步端）

现场：用户报「后天上午的会议没在我日程系统里」。查下来不是漏建一条，而是**整条钉钉同步管道已经静默停了 6 天**，没有任何告警。

## 一、时间线（本案）

| 时点 | 事实 |
|---|---|
| 2026-10-21 | 家中同步端部署（sites29 home1） |
| 2026-10-28 19:18–19:20（北京） | **最后一次成功同步**（`work-host.json.lastCalendar/lastMail`、`state.sync.lastSuccess` 三处一致） |
| 2026-10-28 之后 | 每分钟触发，每轮 10 秒后退出，`LastTaskResult=1` |
| 2026-11-04 06:12 | 用户发现新会议没进系统 |

⚠️ `work-automation-observation.jsonl` 首条是 `2026-11-01T20:12:59Z`，**那不是故障起点**——文件按 `slice(-3000)` 轮转，3000 行 × 每分钟 1 行 = 50 小时。数首条会被骗。

## 二、当轮运行回执

`runtime/.local/work-automation-status.json`：

```json
{
  "startedAt": "2026-11-03T22:11:59.445Z",
  "hostId": "7d4b5206-...",
  "calendar": null,
  "commands": [],
  "error": "工作来源或运行记录超过字节容量",
  "finishedAt": "2026-11-03T22:12:09.941Z"
}
```

`calendar: null` + `commands: []` 定位到死在 `work-runner.mjs` 的 `request('sync/work/maintenance',{})`（`try` 块第 4 步），日历采集（第 71 行）根本没跑到。

## 三、云端容量实况

`GET /api/v1/sync/work/health`：

```
counters: 事项 54/1000 · run 2042/3000 · command 12/100 · host 2/5 · source 3/50 · mail 34/10000 …
bytes:
  主业务          1,079,272 / 15,000,000   (7.2%)
  来源业务与运行   2,215,709 / 12,582,912   (17.6%)
  临时运行         2,095,036 /  2,097,152   (99.90%)  ← 卡在这
```

判定：`run` 条数离 3000 上限还有 958 条，**超的是字节不是条数**。只剩 2,116 字节余量。

上限来源 `runtime/lib/work-records.ts`：

```ts
export const WORK_BYTES=12*1024*1024, WORK_RUNTIME_BYTES=2*1024*1024;
export const portableWorkKinds=['source','event','mail','candidate','decision','application','setting','checkpoint','call'];
// validateWorkRecords():
if(utf8Size(rows)>WORK_BYTES ||
   utf8Size(rows.filter(r=>!portableWorkKinds.includes(r.kind)))>WORK_RUNTIME_BYTES)
  throw new DomainError('工作来源或运行记录超过字节容量',413);
```

非 portable 的 kind = `run` / `command` / `host` / `summary`，就是这 2MB 池子在涨。

## 四、接口实测状态码矩阵

| 请求 | 结果 |
|---|---|
| `GET /api/v1/state` | 200 |
| `GET /api/v1/sync/work/status` | 200 |
| `GET /api/v1/sync/work/health` | 200（含 `counters` + `bytes` 分组） |
| `GET /api/v1/sync/work/runs` | 200（分页 30 条/页，中位 1111 字节/条） |
| `POST /api/v1/sync/work/maintenance` | **413 工作来源或运行记录超过字节容量** |
| 同上 + body `{prune}` / `{keepRuns:500}` / `{compact}` / `{dryRun}` | 全部 413（body 不影响） |
| `DELETE /api/v1/sync/work/runs/<全零uuid>` | 405 请求方法不正确（路由存在、方法不允许） |
| `GET /api/v1/sync/work/runs/<id>` | 404 |
| `POST /api/v1/sync/work/runs/<id>` | 404 同步接口不存在 |
| `POST /api/v1/sync/work/runs/prune` · `POST /api/v1/sync/work/prune` | 404 |

结论：**接口层没有任何删除/裁剪运行记录的入口**，而唯一的清理动作 maintenance 又被它要清理的东西卡死 → 死锁，只能服务端修（先裁剪再校验 / 给 run 设保留期 / 提高 `WORK_RUNTIME_BYTES`）。

## 五、可复用探针脚本

放在程序根目录（如 `releases/sites29-afdf902-home1/probe.mjs`），用完删。

```js
import fs from 'node:fs';
import path from 'node:path';
import {httpRequest} from './runtime/scripts/http-request.mjs';

const root = 'C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1';
const conn = JSON.parse(fs.readFileSync(path.join(root, 'runtime/.local/hermes-cloud-connection.json'), 'utf8'));
const cfg  = JSON.parse(fs.readFileSync(path.join(root, 'runtime/.local/calendar-automation.json'), 'utf8'));
if (cfg.pwshExe) process.env.PATH = path.dirname(cfg.pwshExe) + path.delimiter + process.env.PATH; // 不加这行会报 PowerShell 7 is required

async function probe(route, method = 'GET', body) {
  try {
    const r = await httpRequest(new URL('/api/v1/' + route, conn.url), {
      method,
      headers: {
        Authorization: 'Bearer ' + conn.key,
        ...(body !== undefined ? {'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID()} : {}),
      },
      ...(body !== undefined ? {body: JSON.stringify(body)} : {}),
    });
    let v = '';
    try { v = JSON.stringify(JSON.parse(r.body)).slice(0, 400); } catch { v = String(r.body).slice(0, 200); }
    console.log(`[${method}] ${route} -> ${r.status} | ${v}`);
  } catch (e) { console.log(`[${method}] ${route} -> EXC ${e.message}`); }
}

await probe('sync/work/health');                    // 先看 bytes 分组，定位贴顶的池子
await probe('sync/work/maintenance', 'POST', {});   // 复现 413
// 探不存在的路由/方法，一律用全零 id，别拿真实记录试写：
await probe('sync/work/runs/00000000-0000-0000-0000-000000000000', 'DELETE', {});
```

跑法：

```bash
cd "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1" \
  && "C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe" probe.mjs
```

跑完 `rm probe.mjs`，再 `node deployment/home.mjs verify` 确认 `verified:true`。

## 六、四个容易走错的岔路

1. **把手动跑 `home-task.mjs` 的输出当真**：撞上每分钟的计划任务会返回 `{"skipped":"active_runner"}`——那是锁冲突（`work-sync.lock`，`acquireRunnerLock` 用 pid 存活判定），不是故障本身。
2. **把同步停摆当成上游授权过期**：`dws auth status --format json` 返回 `authenticated:true, token_valid:true`，授权是好的，别让用户去重新扫码。
3. **把故障起点定在 observation.jsonl 首条**：见第一节，那只是 3000 条轮转窗口。
4. **以为「同步挂了 = 日程不能用」**：停的只有 `sync/work/*` 写；业务写入 `client create/patch` 正常（本案改日程一次成功，回执 `status:saved` + version 递增）。

## 七、影响面与兜底

- 冷处理路径：先手工补录用户报的那几条（走业务写入通道），同时推动服务端修容量
- 同步停摆**没有任何告警**，除非另建看门狗：`lastCalendar` 超 N 小时未更新 → 报警。看门狗脚本可直接复用本 skill 的 `scripts/log_freshness_watchdog.py`（把「日志新鲜度」换成「work-host.json.lastCalendar 新鲜度」）；**加之前先问用户**，不要默认建 cron。
