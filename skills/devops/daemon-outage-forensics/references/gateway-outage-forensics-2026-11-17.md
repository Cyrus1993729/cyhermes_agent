# 实案：Hermes gateway 17:41–18:33 断联（2026-11-17）

用户原话：「从下午5点多到6点多，我重启电脑之前为什么你没有任何反应？」
前提：用户以为 agent 卡了，实际是 gateway 进程已经不在了。

---

## 一、时间线（本地 UTC+8）

```
17:35:33  用户发来请求，正常处理
17:36:25  模型输出流中途断："Unrepairable tool_call arguments for write_file
          — replaced with empty object" + "Stream ended with no finish_reason"
17:38:40  一次 API 调用 latency=133.5s
17:39:01  assistant 回复发出（该 turn 耗时 208.5s / 6 次 API）
17:39:03  后台 review 回合启动（同 session，history=86），17:39:08 建流
17:39:13  最后一条事件循环日志   ← 真正的卡死起点
17:41:12  MCP 'amap' 保活：ping 超时但 list_tools 成功
17:41:19  CRITICAL shutdown_watchdog → exit code 75
17:41–18:33  空窗 52 分钟
18:33:19  用户重启后桌面端重新拉起 gateway（gateway-starts.log 新增一条）
```

**真正的卡死时长 ≈ 17:39:13 → 18:33 = 54 分钟，不能全算在看门狗头上。**

---

## 二、怎么坐实「确实退了」

源码 `gateway/shutdown_watchdog.py` 尾部：

```python
faulthandler.dump_traceback(all_threads=True)
mark_exited(exit_code, reason="loop_liveness_watchdog")
os._exit(exit_code)          # ← 硬退，不是 sys.exit
```

`gateway/lifecycle_ledger.py`：启动时 `record_startup()` 若遇 `phase="running"`，
必然写一条 `gateway.previous_unclean_exit` 到 exit-diag + 一条 WARNING。

实测：18:33 那次启动，exit-diag 全天**只有一条** `gateway.start`，无
`previous_unclean_exit`；agent.log 也无 WARNING。
→ 上一个生命跑过 `mark_exited` → `os._exit` 必然执行 → **真的是死的**。

---

## 三、为什么没人把它拉起来

```bash
schtasks /query /fo LIST | grep -i hermes     # 无
sc query type= service | grep -i hermes       # 无
reg query HKCU\...\Run                        # 无
ls $APPDATA/Microsoft/Windows/Start Menu/Programs/Startup   # 只有 desktop.ini
```

- `gateway-exit-diag.log`：`detached: true`、`console_window_attached: true`
- `logs/desktop.log`（2.4 万行）对「子进程退出 / exit 75 / watchdog」**零记录**
- `hermes_cli/config_defaults.py` 多处注释只提 systemd / launchd，**Windows 无对应实现**
- 反证：事故期间桌面后端（pid 进程心跳到 18:30:41）、cron 调度器（17:42/18:00/18:13/18:30
  正常跑）、TG 投递看门狗（每 60s 扫到 18:51）都活着——**只有 gateway 死了**，
  而 Telegram 轮询在 gateway 里 → 消息没人接

---

## 四、用了但用错的证据（GPT 审查时抓出来的）

`state.db` 的 `gateway_heartbeats` 表：

```
pid 10376  start 11-17 18:33:23   last_hb 18:50:23   ← 桌面/serve 后端
pid 10804  start 10-30 19:29:08   last_hb 11-17 18:30:41
```

gateway 当时的 pid 是 3228（`gateway_state.json`），**表里根本没有它**。
→ 拿「10804 活到 18:30」去支撑任何事情都是错的，那张表只能证明后端活着。

---

## 五、诱因线索（收窄但**未坐实**）

卡死起点前 12 秒，后台 review 回合刚好启动，之后**一条日志都没有**（从未完成）。
其他线索：

```
17:04  MCP server 'amap' keepalive failed: TimeoutError
17:11  MCP server 'x': could not reach the MCP server
17:11  MCP server process 189096 is still alive after the kill escalation; abandoning it
17:24/17:32/17:35  [Telegram] Telegram network error (attempt 1/10) 反复重连
17:39  Normal final-send NOT suppressed despite active stream consumer ... possible duplicate
17:41  MCP server 'amap': ping timed out but list_tools succeeded
```

**没拿到线程堆栈的原因**：`faulthandler.dump_traceback` 默认写 stderr；gateway detached + 保留
控制台窗口启动，stderr 未落文件 → dump 丢失；`logs/` 下不存在 `gateway-shutdown-watchdog.log`。

---

## 六、外部模型（gpt-6.1-sol high）审查结果摘要

| 它说的 | 真假 | 处理 |
|---|---|---|
| 「CRITICAL 只证明走到了判死分支，未必真退出」 | 被本机哨兵证据推翻 | 源码为 `os._exit`；sentinel 不是 `running` |
| 「桌面日志没记录 ≠ 没有监督逻辑」 | 部分对 | 结果判断（当时没人拉起）依然成立 |
| 「心跳表不能证明工作进程死活」 | **对，是我用错了** | 当场向用户认账 |
| 「supervisor 必须持有真实子进程句柄，只勾『失败重启』看不到」 | 对 | 采纳进 A′ |
| 「Windows 控制台选中文本会阻塞写操作」 | 新方向，未验证 | 列为待验证假设 |
| 「用 dump_traceback(file=...) 而非重定向 stderr」 | 对 | 采纳进 B′ |
| 「分级响应优于长期关闭看门狗」 | 对 | 采纳进 C′ |
| 「52 分钟不能全算看门狗」 | 对 | 按 17:39 起重算 |
| 「计划任务 IgnoreNew + 取消 72h 执行时限」 | 对 | 采纳 |
| 「procdump 外部取证」 | 可用补充手段 | 列为可选 |

---

## 七、下次能提前 5 分钟拿到答案的检查顺序

```
1. ls -lt logs/                                  → 谁还在写
2. 主日志最后一次正常输出是几点                   → 卡死起点
3. grep watchdog / "exit code"                   → 是不是判死自杀
4. 看 state/*.lifecycle*.json 的 mtime 与内容     → 上次生命是否走完退出路径
5. 对照 gateway_state.json 的 pid 与心跳表 pid    → 别拿错进程的证据
6. gateway-starts.log 末尾                        → 这次是几点被拉起的
```
