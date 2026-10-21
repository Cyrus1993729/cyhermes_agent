# 只读回读某条 ID，证明跨端可见（脱敏证据式回执）

场景：对端（妈妈机 / 任一 peer）在自己的机器上通过**直连云端 API** 改了某个测试项，然后要求本机用**本地客户端**回读同一 ID，证明两端读写的是同一云端库；同时要求「不修改任何事项、不回传原真实日程」。

## 1. 找对可执行入口（先看装在哪）

云客户端项目实际布局（2026-10-21 实测）：`~/AppData/Local/<项目>/` 根下有 `deployment/` 与 `runtime/`，**但根 `runtime/.local/` 是空的**（没有 `hermes-cloud-connection.json`），从根跑 `client` 直接报「连接尚未初始化」。活动 `.local`（连接文件、观测脚本、观测 JSON、锁文件）在 **`releases/<release>/runtime/.local/`**。所以在 **release 目录**下执行：

```bash
find ~/AppData/Local -maxdepth 8 -name 'home.mjs' -not -path '*/node_modules/*'
cd "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1"
"C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe" deployment/home.mjs client items
```

（`search_files` 在无 ripgrep 的宽目录会拒跑，用 `find -maxdepth` 限定范围。调用链：`home.mjs client` → `hermes-cloud.mjs` → `hermes-local.mjs` 读连接文件并注入 DAYFLOW_URL/KEY/SITE_TOKEN → `hermes-client.mjs` 打印响应体；`items`/`state`/`due` 是 GET，无需 stdin、无需手写 URL 或密钥。）

## 2. 读回而不泄露全量数据

```bash
OUT="$LOCALAPPDATA/Temp/items-read-$$.json"
echo "START $(date -u +%Y-%m-%dT%H:%M:%SZ)"
".../node24/node.exe" deployment/home.mjs client items > "$OUT" 2> "$OUT.err"
echo "EXIT=$?"; echo "END $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

只解析目标 ID（本机没有 `python3`，用 `python`；响应体可能带 BOM → `encoding='utf-8-sig'`）：

```python
import json
d = json.loads(open(out, encoding='utf-8-sig').read())
items = d.get('items') if isinstance(d, dict) else d      # 实测直接是 list
it = [x for x in items if x.get('id') == target_id][0]
mark = '[对端标记]'
print(len(items), it['status'], it['version'], mark in (it.get('notes') or ''))
```

事项对象字段（实测）：`id, title, date, originalDate, start, end, mode, category, status, version, notes, source, goalId, backlog, plannedMinutes, actualMinutes, executions`。

核验后 `rm -f "$OUT" "$OUT.err"` —— 临时文件里是全部真实日程，不能留盘。

## 3. 回执模板（只给证据）

```
- 查询方式：releases/<release>/deployment/home.mjs client items（GET，exit=0）
- 查询成功时间：<UTC 起>→<UTC 止>（北京时间 <起>-<止>）
- 条目总数 N；目标 ID <id> 命中 1 条
- notes 是否含「<标记>」：是/否（可给标记前后 ~20 字上下文，其余内容不回传）
- version = X（对端声称 Y → 一致/不一致）
- status = Z（对端声称 … → 一致/不一致）
- 未修改任何事项／未触发同步／未注册任务／未发 Telegram／未重启电脑·网关·代理／临时文件已删
```

## 4. 观测/回执文件的判读

- 先确认用的是**修正版** `natural-two-cycles.json`；`natural-two-cycles.invalid-first.json` 是作废首跑，永不使用。
- 顺序：`baselineVerified === true` → `excludedLocalRunIds.calendar/mail` 等于本机被排除的两个 runId → `passed` / `timedOut` → 每轮 `complete` / `commands`。`passed:false` 时照实说原因，不美化。
- 存活判定 = **文件 mtime（周期性刷新，约 30s）+ 进程都在**：

```bash
stat -c '%n %y' runtime/.local/natural-two-cycles.json
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Select-Object ProcessId,CreationDate,CommandLine | Format-List"
```

找 CommandLine 含观测脚本名的项，报 PID + 启动时间；只报「文件存在」会把已死进程当活的。
- 脱敏：key/token/连接文件内容一律不出现在回执；hostId 这类非凭据标识可原样给。
