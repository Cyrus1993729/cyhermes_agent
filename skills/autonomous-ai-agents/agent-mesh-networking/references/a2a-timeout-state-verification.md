# A2A 超时后的只读状态核对协议

来源：2026-10-21 实案。对端（妈妈机 pc-a）派来 task-069c8df2…，A2A 层返回
`TASK_STATE_FAILED: [agent did not reply in time]`，对端要求「只核对当前真实状态，60 秒内给精简结果，
不重新导入、不重新发起登录、不安装或注册任务」。

结论：超时 ≠ 未执行。核对后发现配置已落盘、授权进程仍活着在轮询，只是等人工扫码——
**任何重做都会覆盖已完成成果或开出第二条并行授权会话。**

## 一、动作边界（对端给了范围就严格照范围）

| 允许 | 禁止 |
|:---|:---|
| 判存在性、读进程列表、解析自家私有日志的状态字段 | 重跑导入 / 重登 / 重装 / 重新注册任务 |
| 进程内读配置后发一次 GET（只回状态码+计数） | 把配置内容、state 全文、日志全文读进模型或输出 |
| 只报失败**类型** | 顺手修复、顺手重试、顺手发 Telegram |

「范围仅 <某目录> 及本任务启动的相关进程」= 不许扫全盘。先定位根目录（本次 `%LOCALAPPDATA%\DayflowHome`，
不在 `D:\Workspace`、不在桌面），再按 `releases/<site>/runtime/.local` 逐层 `ls`，别一上来 `find /`。

## 二、核对清单（按对端条号回答）

1. **配置存在性**：`ls -l` 取 size + mtime 即可，**不要 `cat`**。回「存在（182 B，mtime 07:19:12）」。
2. **一次性会话文件**：`connection-request.json`、`connection-request-private.pem`。
   - 存在 = 握手未完成；**不存在 = 已被消费**，若配置已存在则属正常收尾形态（本次即如此）。
   - 别急着报缺失：先 `find . -maxdepth 4` 排除嵌套副本。
3. **进程**：只回 `PID | 启动时间 | 可执行名`。
   ```powershell
   Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'Authorize-DingTalk|dws.*auth' } |
     ForEach-Object { '{0}|{1}|{2}' -f $_.ProcessId, $_.CreationDate, $_.Name }
   ```
   ⚠️ 匹配串本身就在你自己这条命令行里，结果必带**假阳性**（本次 2 真 + 3 个 `bash.exe` + 1 个 `powershell.exe`）。
   收窄：加 `-and $_.Name -in @('dws.exe','pwsh.exe')`，或排除自身 PID 与父进程树。
   **对外永远只给 PID + 时间 + Name，不给命令行**（命令行常含 token/路径/账号）。
4. **私有日志**：只提取状态位，不贴全文。
   ```bash
   grep -oE 'https?://[A-Za-z0-9./?=&_%:-]*' "$LOG" | sort -u
   grep -oiE '(user_code|usercode)[^A-Za-z0-9]{0,3}[A-Z0-9-]{4,12}' "$LOG"
   grep -oiE 'success|failed|error|expired|pending|approved|denied|等待|成功|失败|过期' "$LOG" | sort | uniq -c
   ```
   轮询型登录：`等待` 计数很高 + 无 success/failed = **仍在等人工确认**，不是失败。
5. **state 探针**：进程内读配置（`fs.readFileSync`，不 print），拼 `GET <base>/api/v1/state`，
   只输出 `HTTP_STATUS`、body 字节数、顶层 shape、事项数。鉴权头依次试 `Authorization: Bearer`、
   `x-api-key`、query；**全部 403 + `content-type: text/html` = 边缘 WAF 拦，不是鉴权参数错**——只报类型，别改配置去「修」。

> 若项目自带的 `http-request.mjs` 在子进程报 `PowerShell 7 is required for Windows HTTP requests`：
> 它用裸名 `spawn('pwsh', …)`，子进程 PATH 里没 pwsh 就失败。修法二选一——给子进程 PATH 加 pwsh 目录，
> 或探针脚本里直接用 Node `fetch`（本机挂 v2rayN 代理，内网/本地地址需绕过代理）。

## 三、钉钉设备授权流事实（dws auth login，实测）

- 真实 URL 是 **`https://login.dingtalk.com/oauth2/device/verify.htm?caller=dws&callerUmt=…&user_code=XXXX-XXXX`**，
  不是 `…/oauth2/device/authorize.htm`（常见的错写法，照它 grep 会一无所获）。
- 授权码形如 `NSXG-WHXK`（两组 4 位大写字母/数字），**TTL 900 秒**，客户端每 **5 秒**轮询。
- 授权码打在 **stderr**（stdout 常为 0 字节），首行附近有「授权码将在 900 秒后过期」。
- 未扫码时日志只有 `等待…` + `(每 5 秒轮询一次)`；过期后进程退出，不会自己重发码。
- 报状态时把「下发时刻 + 900s = 失效时刻」算给对端，比只说「还在等」有用。
- 进程形态：`launch-authorize.ps1` → `pwsh.exe` + `dws.exe` 两个进程，几乎同时启动（差 1~2 秒），
  报「仍在运行」要同时给两者。

## 四、回复形态

按条号 1..N 逐条一句，最后一句给结论（例：「配置已落盘，登录进程仍在有效期内等人工确认；超时只是 A2A 层等待超时」）。
不写「下一步建议」，除非对端问。
