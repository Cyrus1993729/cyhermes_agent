# 「你怎么没反应」的第三种真相：gateway 进程已经不在了（2026-11-17 实战）

## 与另两种真相的区别

| 症状 | 真相 | 证据 |
|---|---|---|
| 只收到几个字 | 投递失败 + 流式预览残留 | `send_path_degraded` |
| 完全空白但回答已生成 | 最终发送整条失败 | `response ready` 有、`failed to deliver` 有 |
| **几十分钟毫无反应** | **gateway 进程已退出** | 该时段 `gateway.log` 无任何消息处理行 |

判据一句话：**`gateway.log` 在那段时间只有 cron、没有消息处理，而 `agent.log` 里 cron 照跑** = 进程没了。
不是网络、不是模型慢、不是投递问题。

## 实战时间线（断联 52 分钟，最后靠重启电脑恢复）

```
17:39:01  response ready（最后一条正常回复）
17:39:03  后台 review 回合启动（线程 bg-review）
          ↓ 此后事件循环零日志
17:41:19  CRITICAL gateway.shutdown_watchdog:
          Gateway event loop missed 3 consecutive liveness probes;
          dumping all thread stacks and exiting with code 75 so the service supervisor can restart it.
17:41–18:33  52 分钟：gateway 进程不存在，消息无人接收
18:33:19  用户重启电脑，桌面端重新拉起 gateway
```

## 定位五步

### 0. 时间基准先对齐

| 文件 | 时区 |
|---|---|
| `logs/gateway.log` `agent.log` `errors.log` | **本地时间** |
| `logs/gateway-exit-diag.log` `logs/desktop.log` | **UTC（带 Z）**，差 8 小时 |
| `gateway-starts.log` / `state.db` | **epoch 秒** |

```python
import re, os
base = r"C:\Users\Administrator\AppData\Local\hermes\logs"
def win(f, start, end):        # "17:38" .. "18:36"
    out = []
    for l in open(os.path.join(base, f), encoding='utf-8', errors='replace').read().splitlines():
        m = re.match(r"^2026-11-17 (\d\d:\d\d)", l)   # ⚠️ 必须带日期，否则跨天误命中
        if m and start <= m.group(1) <= end:
            out.append(l)
    return out
```

### 1. 抓 shutdown_watchdog 那条 CRITICAL

含义：**事件循环被堵，看门狗按设计主动自杀**（exit 75），指望「服务监督进程」拉起。

参数（`hermes-agent/gateway/shutdown_watchdog.py`）：

```
LOOP_WATCHDOG_INTERVAL_S = 30.0   LOOP_WATCHDOG_TIMEOUT_S = 10.0   MAX_STRIKES = 3
→ 循环被堵 ≈2 分钟后退出
```

⚠️ **堆栈默认会丢**：`faulthandler.dump_traceback(all_threads=True)` 写 **stderr**，gateway 以 detached + 控制台窗口启动时 stderr 不落盘。
`logs/gateway-shutdown-watchdog.log` **不存在** = 没有 dump = 诱因只能缩小范围，**不许报「已定位根因」**。

### 2. 确认本机有没有 supervisor（决定性）

```bash
schtasks /query /fo LIST | grep -i hermes
sc query type= service state= all | grep -i hermes
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" | grep -i hermes
reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" | grep -i hermes
ls -1 "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup"
```

全空（启动夹只有 `desktop.ini`）= **没有任何东西会重启 gateway**，exit 75 = 死到重启电脑为止。
补充证据：`logs/desktop.log` 搜 `exit code 75` / `gateway exited` **零命中** → 桌面端只负责启动子进程，**不监听子进程退出**，它不是 supervisor。

### 3. `state.db` 取证：谁活着、丢了什么消息

```python
import sqlite3, datetime, os
con = sqlite3.connect(os.path.join(os.environ['LOCALAPPDATA'],'hermes','state.db'))
con.row_factory = sqlite3.Row
def t(ts): return datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M:%S")
try:    # 心跳表：分清「桌面后端 pid」与「gateway pid」
    for r in con.execute("select * from gateway_heartbeats order by last_heartbeat desc limit 4"):
        print(r['pid'], t(r['started_at']), t(r['last_heartbeat']))
except sqlite3.OperationalError:
    pass   # 旧库没有这张表
for r in con.execute("select role, substr(content,1,60), timestamp from messages "
                     "where role='user' and timestamp > ? order by timestamp", (epoch_start,)):
    print(t(r['timestamp']), r[1])
```

三处 pid 来源别混淆：`gateway_state.json`（当前 gateway）/ `state/gateway.lifecycle.json`（**下次启动会被覆盖**）/ `gateway-starts.log`（**唯一可靠的历次启动清单**）。

### 4. 找独立目击证人

`logs/tg_delivery_watchdog.log` 每分钟一条「扫描完成: 待接管 N 条」。空窗期它照常每分钟一条
→ 机器没关机、cron 在跑、网络基本通，**唯独 gateway 进程不存在**。这比任何推断都硬。

### 5. 诱因按证据强度排序（不许编）

1. **后台 review 回合**（线程 `bg-review`）：时间紧贴停摆起点、此后零日志（从未完成）——嫌疑最大
2. **MCP server 保活/重连**：`ping timed out`、`still alive after the kill escalation; abandoning it`（僵尸 stdio 进程）
3. **网络/代理抖动**：Telegram 频繁 `Timed out` 重连、`final-send NOT suppressed ... possible duplicate`

## 结论必须分层写

> 直接原因 **100% 可确证**：看门狗 exit 75 + 本机无 supervisor → 死了 52 分钟。
> 诱因 **只能缩小到空间**：堆栈没落盘。

把一个「缩小到三个嫌疑」写成「已定位根因」是报告事故。

## 修法三选

| 方案 | 内容 | 评价 |
|---|---|---|
| **A 根治** | 计划任务 / 服务看守 gateway，见退出码 75 自动拉起 | 唯一能消除长时间空窗 |
| **B 取证** | `faulthandler` 输出重定向到 `logs/gateway-shutdown-watchdog.log` | 低风险，下次能坐实诱因 |
| **C 别做** | `gateway.loop_watchdog: false` 关掉看门狗 | 等于拆安全阀，变静默假死 |

建议 **A + B**，不动 C。

## 顺带确认「有没有丢消息」

只要 gateway 重启后能重新 `getUpdates`，Telegram 侧未确认的更新会补投（日志：`Dragged 1 inbound message(s) queued during startup restore`）。
所以空窗期用户发的消息通常**不丢**，只是延后——但这不能当“没事”的白嫖，主动告知具体晚了几分钟。
