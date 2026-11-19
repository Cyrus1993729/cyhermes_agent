# 暂存补丁验收实测：Dayflow 73 号提醒补丁（2026-11-18，A2A）

场景：正式站已发布 Sites43；本机 `scripts/dayflow/` 下已存在 73 号提醒补丁的暂存物。
对端要求「只跑已有测试 + py_compile、设 dry、禁止真实投递、只读 GET 新 due 路由、回测试结果 /
两个文件 SHA256 / 备份是否可用、未完成单列」。**未改任何文件、cron、收件人。**

## 现场清单

| 路径 | 说明 |
|:--|:--|
| `%LOCALAPPDATA%/hermes/scripts/dayflow/tests73/test_df73.py` | 38 项离线验收（假通道 + 临时状态目录） |
| `…/dayflow/tests73/due73_fictional.json` | 8 条纯虚构候选夹具 |
| `…/dayflow/df_reminders73.py` / `df_watch73.py` | 新增脚本（未替换线上） |
| `…/dayflow/HASHES_73.txt` | 9 条 sha256（暂存物 + 线上 `df_watch.py`/`df_common.py` + 两份备份） |
| `…/dayflow/backup_73/df_{watch,common}.py.bak_20261118_1534` | 仅备份会被改的两个原文件 |

## 实测结果

- `python -m py_compile df_watch73.py df_reminders73.py tests73/test_df73.py` → OK。
- `DAYFLOW_DRY=1 python tests73/test_df73.py` → **PASS 38 / FAIL 0**，退出码 0；分块 A4/B10/C7/D9/E2/F3/G3。
- `sha256sum -c HASHES_73.txt` → 9/9 OK：
  - `df_watch73.py` `33eb3cf2…574c8`
  - `df_reminders73.py` `1b920846…beee21`
  - 线上 `df_watch.py` `913967d0…f9ae3e` == `backup_73/df_watch.py.bak_…`
  - 线上 `df_common.py` `0041fe7c…b6ec8` == `backup_73/df_common.py.bak_…`
- 备份复制到 `%TEMP%` 后 `py_compile` 通过 ⇒ 可直接覆盖回滚。
- 线上源文件 mtime 仍是 10-21（补丁前），测试后未变。
- `cron/jobs.json`：心跳 `1b3cca2ebcd9` 仍 `dayflow/df_watch.py`、每 5 分钟、`deliver=local` ⇒ 未切换。

## 只读 GET（关键）

`GET https://dayflow-personal-planner.yucui3516.chatgpt.site/api/v1/reminders/due?calendarChanges=1&lead=18`

| 写法 | status | body |
|:--|:--|:--|
| 无参 | 200 | `[]`（2 字节） |
| `calendarChanges=1&lead=18` | 200 | `[]` |

裸 `fetch` 打同一 URL → `403 text/html` Cloudflare；改用部署自带 `runtime/scripts/http-request.mjs`
（win32 spawn pwsh）+ `tools/pwsh7` 前置 PATH + `HTTP_PROXY=127.0.0.1:10808` → 200。
（凭据只从 `runtime/.local/hermes-cloud-connection.json` 读，只打印 status/形状/字段名。）

## 三条阻塞项（当时判定，不是结论）

1. **空数组歧义**：补丁里 `TREAT_EMPTY_AS_UNAVAILABLE = True`，`[]` 一律判「未就绪」→ 钉钉会前提醒整轮
   失败关闭。Sites43 在「确实没有候选」时也回 `[]`，与旧形态同形 ⇒ 上线前必须先解决判定，
   或等有候选的时间窗再探测。
2. **本地客户端丢参数**：`runtime/scripts/hermes-client.mjs` 里 `due:['GET','reminders/due']`，
   URL 由 mapping 拼成、`args` 不参与 ⇒ `client due --query calendarChanges=1&lead=18` 实际不带参数；
   本地 bundle 仍 `sites29-afdf902-home1`，未随 Sites43 更新。
3. **cron 未切换**：`df_watch.py` → `df_watch73.py` 是 README 里「等确认」的那一步，未动。

## 报告顺序（对方认可的形状）

测试（PASS/FAIL + 分块 + 退出码）→ 两个文件 SHA256 原文 → 备份（相等 + 可编译 + 范围）→
只读 GET（status/形状/条数）→ **未完成单列**（每条带阻塞原因）→ 一句「未改文件/cron/收件人、零真实投递」。
