---
name: local-service-deployment
description: "用<本地部署第三方工具>时触发：开源Python项目跑上本机Windows长期自动运行，含自启+看门狗+备份。"
version: 1.0.0
category: devops
tags: [deployment, self-hosted, windows, scheduler, watchdog, python]
---

# Local Service Deployment — 本机部署第三方工具/服务

## When to Use
- 用户要把某个 GitHub 开源项目（Python 工具/服务，如定时抓取+推送类）部署到本机 Windows 长期运行
- 触发词："部署这个项目"、"本地部署"、"帮我跑起来"、"迁移到本地"
- 特征：有定时任务、有推送/通知、需要 7×24 自动运行

## 核心架构模式：采集器 + Hermes 智能层（用户认可，2026-08 实案）
当外部工具的去重/筛选/推送质量不满足用户需求（如"只推增量不重复"但官方只做当天内精确去重）时，优先考虑：
**外部项目 = 纯采集器（关推送/关AI，只入库），Hermes = 智能层（cron 定时读库 → 语义去重 → 按用户兴趣精选 → 推送）**。
- 优点：零上游代码改动（守住"不改第三方源码"边界）、去重可做语义级（跨平台/改标题合并，优于逐字比对）、可个性化、可写点评
- 实现要点：关外部项目推送/AI 开关（config 总开关）；选一个无参数脚本按当前时间自动判断窗口（cron script 不支持参数）；SQLite 按天分库时注意库内时间格式（可能只有 HH-MM，日期在文件名里，需拼接后比较）；用 pushed_titles.json 之类本地清单做跨会话去重（LLM 精选后 append）
- 改代码方案（改 2 处上游函数实现跨天增量）作为备选，需用户明确授权

## 核心流程（10 步，顺序执行）

0. **前置选型**：Docker vs 本地 uv vs 云服务器——结合机器配置（老笔记本跑 Docker Desktop 的 WSL2 虚拟机很吃力）、网络（国内机器走本地代理 vs 云服务器需额外配代理）、常驻情况（电脑是否 24h 开机）判断。出契约（sprint-contract）+ 用户确认（decision-gate）；部署类任务用户可简化流程（跳过 L1/复盘，契约 + GPT-5.6 Sol 审查仍要）
1. **环境检查**：`docker/uv/git/python` 版本实测（禁凭常识断言）
2. **代码源确认**：clone 前先 GitHub API 查用户仓库列表——确认是"正在用的仓库"还是刚 fork 的空模板（空模板 = 关注词/密钥全无，配置从零配；用户可能删过旧仓库）
3. **依赖安装**：`uv sync`（国内用清华镜像 `UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple`，秒级提速）
4. **运行模式确认**：读项目 CLI 入口（argparse/`__main__.py`）确认"一次运行即退出" vs "常驻进程"——**决定自启方式**：一次型 → 计划任务定时触发；常驻型 → 登录/开机启动 + 崩溃重启
5. **密钥策略（零明文）**：config 留空 + 环境变量注入（项目 loader 通常支持 env 优先于 config，`grep _get_env_str / os.environ` 确认变量名）+ 单独 `run_secrets.bat` + `.gitignore` 忽略 + `git remote remove origin`（物理防误推）
6. **配置适配**：代理分流（外网 API 走 7897 / 国内 API 直连，实测为准）；数据源连通性（见 Pitfalls UA 403）；超时参数（见 Pitfalls 推理模型超时）
7. **全链路验证**：项目自带体检命令（`--doctor` 类）→ 测试通知（`--test-notification` 类）→ 一次真实完整运行（观察真实产物：推送消息、报告文件、日志）
8. **开机自启**：Windows 计划任务 `cmd.exe /c 'schtasks /Create /F /TN <名> /TR "<bat路径>" /SC HOURLY /MO 1'`；一次型工具建议双任务：`/SC HOURLY`（定时）+ `/SC ONLOGON`（登录补跑，重启后不等整点）；bat 用隐藏窗口运行
9. **看门狗**：Hermes cron + no_agent 脚本检查日志新鲜度（见 scripts/log_freshness_watchdog.py）——正常静默、陈旧自动触发、**连续两次陈旧才告警**（状态标记文件），符合用户"事件驱动、平时静默"偏好
10. **数据维护 + 手册**：过期文件清理（90 天）+ 定期备份 zip（每周 cron）；用户手册放桌面（改配置怎么生效/常见问题自查/一键回退方案）

## Pitfalls（全部实踩，2026-08 TrendRadar 部署）

- 🔴 **PYTHONPATH 污染**：Hermes 进程注入 `PYTHONPATH` 指向 Hermes 自身 venv → 子进程（`uv run`）从 Hermes venv 导包 → pydantic_core 二进制不匹配 `ModuleNotFoundError`。**运行任何第三方 Python 项目前必须 `unset PYTHONPATH`**（bat 里 `set PYTHONPATH=`）
- **Hermes cron script 参数**：script 必须放 `~/AppData/Local/hermes/scripts/` 用相对路径（绝对路径被拒）；`schedule="30m"` 是 one-shot（30 分钟后跑一次），**循环必须用 cron 表达式** `*/30 * * * *` 或 `every 30m`，且 repeat 显式传 0（forever）
- **免费公共 API 403**：403 不一定是墙——先测三组合：默认 UA / 浏览器 UA / 走代理。实案：newsnow API 默认 curl UA=403、带 Chrome UA 直连=200、走代理=403（反爬放行浏览器 UA）
- **推理模型超时**：DeepSeek v4-flash 等带 reasoning 的模型处理大批量分析，LiteLLM 默认 timeout 120s 不够（返回"空响应"）→ 调到 300s+、num_retries 2。诊断：同模型小请求 curl 直测成功 = key/模型没问题，问题在超时
- **schtasks 中文输出 GBK 乱码属正常**；从 git-bash 调用必须 `cmd.exe /c 'schtasks ...'` 包裹
- 🔴 **计划任务"上次结果=1"排查（2026-08-08 实踩，停摆 24h）**：任务显示"就绪"≠ 正常——"上次结果=1"= bat 被调用但失败。查详情：`MSYS_NO_PATHCONV=1 schtasks /query /tn <任务名> /v /fo LIST | iconv -f GBK -t UTF-8`。**验证/触发一律用 `MSYS_NO_PATHCONV=1 schtasks /run /tn <任务名>`**（等价生产环境，绕开 bash→cmd 路径转换），不要用 `cmd /c "D:\...\xxx.bat"` 复现——其报错与生产环境可能不同（如 `The system cannot find the path specified` 常是重定向目录缺失而非 bat 真失败）
- 🔴 **bat 编码坑 + 重定向目录坑（同次实踩）**：① bat 文件 UTF-8 无 BOM + 中文注释 → cmd 按 GBK 解析乱码 → 把相邻 ASCII 吞掉当命令执行（`'ndRadar' 不是命令`）——**bat 必须全英文**；② bat 里 `>> output\logs\xxx.log` 重定向前**必须先 `if not exist "output\logs" mkdir "output\logs"`**，否则报 `The system cannot find the path specified`。两个坑叠加时，编码坑修好才会暴露重定向坑
- 🔴 **看门狗"日志从未生成"必须告警**：日志新鲜度看门狗若 `if not os.path.exists(LOG): return`（把无日志当部署初期），bat 挂掉时日志永远不存在 → 看门狗永久静默。正确：无日志 + 无触发标记 → 触发一次重启；无日志 + 已有标记 → 告警（说明 bat/计划任务层故障）。看门狗"ok"不代表系统健康——排查先查数据/日志时间戳
- **GPT-5.6 Sol 契约审查**：`codex exec -c 'model="gpt-5.6-sol"' --skip-git-repo-check --sandbox read-only` 加 `--tools ""` 禁用工具，否则 审查模型把 max-turns 耗在工具调用上返回 "Reached max turns" 无输出；max-turns 给 8
- **验证改动**：写完脚本/配置跑 ad-hoc 验证脚本（tempfile 路径 + `hermes-verify-` 前缀，跑完删除），输出逐项 PASS/FAIL，明确标注"ad-hoc 验证，非测试套件"
- **增量/去重基准陷阱**：增量模式常是"当天内"去重（存储按天分库）——跨天第一次运行会把昨天推过的内容全当"新增"再推一遍（重复！）。实现跨天增量需改两处：①查重范围扩展为"昨天+今天"合并 ②"当天第一次"分支不能直接全量，也要走新增检测（详见 references/trendradar-deployment-2026-08.md 推送模式小节）
- **看门狗阈值 vs 推送频率**：阈值必须适配推送间隔——每小时推送用 4h 阈值没问题；改成每天 2 次（间隔 9-15h）后必须调大到 ~16h，否则两次推送之间必误报"疑似故障"
- 🔴 **密钥禁止从截断输出猜测**：从 `head -c`、打码（`***`）等截断输出拼密钥写入配置 = 严重错误（2026-08-06 实踩：拼错 DeepSeek key 写入 run_secrets.bat，验证时才发现）。必须完整读取源文件，写入后做格式断言（如 `sk-` 前缀 + 长度）

## 第三方「安装包」型部署（他人/协调端给的 installer zip，2026-10-20 实案）

场景：不是 clone 开源仓库，而是另一台机/协调端发来一个 zip：`README.md` + `deployment/*.ps1`/`*.mjs` + `runtime/`，用其自带脚本做 verify/smoke/init/握手。与上面「clone + uv sync + 计划任务」是另一条路径，共同点是「先校验再用、不覆盖既有环境」。

执行顺序：
1. **下载直连**：LAN URL 必须 `curl --noproxy '*'`（本机常驻 `HTTP_PROXY=http://127.0.0.1:10808`，curl 默认读 env → 走代理打 LAN 必失败）；`-w 'HTTP:%{http_code} SIZE:%{size_download} IP:%{remote_ip}'` 一次拿到状态码/字节数/`remote_ip`（IP 字段=真直连的证据，比「没报错」可靠）。
2. **双重校验**：sha256 与给定值逐字比对 + 字节数一致（本次 130878 B）。
3. **先只解 README.md**：`unzip -o pkg.zip README.md -d .` → 读完再解全包，别先铺 50 个文件再猜用法。
4. **解压前查冲突**：`unzip -l` 清单对照现有目录；已有同名但内容不同 → **保留并报告**，不要 `-o` 盖掉。
5. **依赖自检后才决定装不装**：包里的 `Install-Tools.ps1` 是「缺才装」。本次 Node v24.22.0(≥24.14.0) / pwsh 7.6.7 / dws v1.0.63 全已在，**跳过安装脚本**复用已校验官方包——顺带避免覆盖 Hermes 自带 Node v22.22.3。
6. **verify → init → smoke → 握手**，每步读回执字段（`verified/bundleId/sourceCommit/files`、`prepared/installation/active`、`importsComplete/noNetwork`）。
7. **给 native 程序只传绝对路径**：node/pwsh 是 native，MSYS 不转换路径 → 在 shell 里写 `./tools/node24/node.exe` 会 `No such file or directory`（exit 127）；一律 `C:/...` 正斜杠绝对路径。

Pitfalls：
- 🔴 **版本化安装会把工作目录挪走**：installer 默认 `InstallRoot=%LOCALAPPDATA%\<App>\releases\<bundleId>`，而 **`tools/` 仍在解压根**→ 装完必须确认「实际安装目录」（读 `prepared` 回执 + 看目录结构），后续命令都在 release 目录跑、工具用绝对路径。本次即在 release 目录里 `./tools/node24/node.exe` 先失败一次才暴露。
- **幂等靠 manifest hash**：目标已存在且 manifest 不同 → 脚本拒绝并保留旧版（正确行为）；自己别手工 `-o` 覆盖。
- **代理参数只落程序配置**：`-HttpProxy http://127.0.0.1:10808` 只写进该程序自己的 json，系统代理不动；脚本会校验「仅 loopback + 无凭据」。
- **握手类接口的私钥只在本地**：`*-private.pem` 同级 `.local`（ACL 已收紧为 SYSTEM + 当前用户）；报告只给路径与权限面，不给内容；`grep PRIVATE` 自证对外 JSON 干净。
- 完整命令/输出：见 skill `agent-mesh-networking` 的 `references/deployment-handoff-execution-2026-10-20.md`。

## 接续核查（断点续作：全只读 + 过期请求刷新，2026-10-21 实案）

场景：上一轮部署被中断（协调端模型额度耗尽/会话断），对方发来"继续任务包N，已知安装目录/homeId/ZIP 哈希"，要求**只核查不重做**。

铁律（对方写进任务书，违反即返工）：
- 不重复安装、不注册计划任务、不启停正式同步、不覆盖配置、不改本机 Hermes/A2A 配置
- 先跑包自带 `verify` + `smoke`（纯本地无网络）拿到回执，再谈其他检查
- 凭证文件（`*-cloud-connection.json`、`*-private.pem`）**只报存在性/权限面，不读内容、不进上下文**；对外 JSON 用 `grep -c PRIVATE` 自证干净
- 第三方 CLI 授权状态只报布尔（`authenticated`、有无 corp_id），不打印 ID 与 token，stderr 同样正则脱敏

四项状态一次查全（`find <已知根> -maxdepth 4 -name ...`，**禁止全盘扫描**）：
| 项 | 判据 |
|---|---|
| 后台连接配置 | `<release>/runtime/.local/hermes-cloud-connection.json` 不存在 = 未配置 |
| 同步激活标记 | 同目录 `home-enabled.json` 不存在 = 未激活（`pause` 会改名 `home-disabled-<ts>.json`） |
| 计划任务 | `schtasks /Query /FO CSV \| grep -i <任务名>`，无输出 = 未注册 |
| 运行锁 | 同目录 `work-sync.lock` |

坑：
- 🔴 **过期公钥请求直接重跑 `connection-request`，别手工删文件**：该 op 幂等——请求件仍有效则原样返回旧的，过期才新生成密钥对并覆盖 `connection-request-private.pem`。本次旧件 `2026-10-20T14:52:42Z` 已过期，重跑即得新件（30 分钟有效期）。
- **时间基准**：请求 JSON 的 `expiresAt` 是 UTC（`Z`），本机 `date` 是 `+0800` → 比较一律走 epoch（`Date.parse`），汇报同时给两种写法（本次 `23:45:37Z` = 次日 `07:45:37 +08:00`）。
- 🔴 **任务存在性别信 `/TN` 的文案**：`schtasks /Query /TN <不存在>` 返回 GBK 乱码"系统找不到指定的文件"，文案与退出码都不可靠 → 用全表 grep。（本次据此确认 `Dayflow-Work-Sync` 未注册，正好符合"不要重复注册任务"。）
- **第三方 CLI 状态探针**（只读、不落配置）：`node -e` 读该程序自己的 config 拿 exe 路径 + config dir → `spawnSync(exe,['auth','status','--format','json'],{env:{...process.env,<APP>_CONFIG_DIR:...},windowsHide:true})` → 只 `console.log` 布尔字段，stderr 走 `.replace(/[A-Za-z0-9_-]{20,}/g,'<redacted>')`。
- **归档哈希必须实测 + 交叉验证**，不能引用上次结论：`sha256sum <归档>` 与随包 `SHASUMS256.txt` / `download_manifest.json` 逐字比对，URL 从下载清单取；归档已不在已知目录就如实说找不到，**不编造**。
- **顺序不可颠倒**：`connection-import`（加密回填）→ 钉钉扫码授权 → `preflight`（要求 DWS 已授权且身份与云端已选数据源匹配）→ `activate`（需 30 分钟内成功的 preflight + 签名 permit）→ 判据齐了才注册计划任务。

汇报形态（对方按 GetTask 读回执，结构比措辞重要）：verify/smoke 原始 JSON → 状态表格（存在/不存在）→ 待回填的公钥请求整块 JSON（可直接复制）→ 哈希表（实测值 + 官方 URL + 与校验源一致）→ 末尾一句"下一步谁先谁后"。

## 加密凭据回填 + 设备码授权（2026-10-21 实案，接续核查的下一步）

**回填前先核三字段**（30 秒，省一轮返工）：读 `<release>/runtime/.local/connection-request.json`，把 `homeId` / `nonce` / `expiresAt` 与来件逐字比对；不一致或已过期就别回填（`import` 会自己拒，但越早发现越省事）。

- **回填姿势**：信封写 `<release>/runtime/.local/<tmp>.json`（UTF-8）→ `subprocess.run([node,'deployment/home.mjs','connection-import'], cwd=release, stdin=open(tmp,'rb'), capture_output=True)`。成功回执固定 `{"configured":true,"credentialsPrinted":false}`；程序成功后自己删 `connection-request.json` 与 `-private.pem`，临时信封自己再删。**信封绝不当命令行参数**（会进 ps/历史），解密结果绝不打出来自证。
- **发起授权**：`deployment/Authorize-DingTalk.ps1` 从 release 目录跑；`Start-Process -WindowStyle Hidden`，`-RedirectStandardOutput` 与 `-RedirectStandardError` 必须是**两个不同文件**（同文件 Start-Process 直接报错），日志落 `runtime/.local/`。
- 🔴 **隐藏进程已启动，调用方却卡死到超时**：启动那一步用了 `capture_output=True`，孙子进程占住管道句柄 → `communicate()` 永远等不到 EOF（本次卡满 300 s 被内核杀、变量全丢，但目标进程其实已正常在跑）。修法：启动调用改 `stdout/stderr/stdin=subprocess.DEVNULL`。**超时后的第一动作是查进程 + 查日志，不是重跑**（重跑=第二个轮询进程 + 第二套设备码）。
- 🔴 **CLI 授权提示走 stderr 不走 stdout**：`dws auth login --device --no-browser` 的授权码/链接/轮询全在 `.stderr.log`，`.stdout.log` 恒 0 B。解析本次新生成的码读 stderr，别因 stdout 空就以为没启动。
- **码有效期 900 s**，从日志 `Step 1 请求设备授权码` 时刻起算 → 汇报给「生成时间 + 过期时刻 + 剩余分钟」，并说明超时后 dws 以非零退出、需重跑取新码。实际页是 `device/**verify**.htm?…&user_code=…`（不是 `authorize.htm`）。
- **存活证据要两个 PID**：`Get-CimInstance Win32_Process` 过滤 `dws.exe` 与 `pwsh ... Authorize-DingTalk*`，外层 pwsh PID + 内层 dws PID + 各自 `CreationDate`，只报一个不算核对。
- **权限面看 icacls 不看 `ls -l`**：Node `{mode:0o600}` 在 NTFS 是空操作（MSYS 显 `-rw-rw-rw-`）；只剩 `SYSTEM` + 当前用户（`(I)` 继承）才是真收紧。另：`Local Settings\X` 就是 `AppData\Local\X`（junction），两条路径别当两份安装。
- 🔴 **从 MSYS bash 启动同一个隐藏进程，是同一个坑的 bash 版**：`pwsh -File launch-*.ps1 2>&1` 会把 bash 的管道句柄交给孙子进程 → 调用方等 EOF 卡到超时（本次 180 s），而 `Start-Process` 早已返回、dws 已在轮询。修法：启动调用**不接管道**（单独调用、不 `2>&1`），随后另起一次调用查日志尾 + `tasklist | grep -iE "pwsh|dws"` 确认存活。超时后第一动作是查进程/日志，不是重跑。
- **过期码实例多半不用自己 kill**：900 s 到期后 dws 自己返回 `{"error":{"category":"auth","code":2,"message":"device authorization failed: 设备授权码已过期（900 秒），请重试"}}`，pwsh 抛 `Official authorization incomplete` 退出（stderr 末尾即此，stdout 恒 0 B）。所以「结束旧实例」通常只需 `tasklist` 确认无残留；仍在跑才按 PID 杀。
- **别复用带写死时间戳的 launcher**：上一轮的 `launch-authorize-<ts>.ps1` 里两个 log 路径是硬编码的，直接重跑会**覆盖旧证据**（旧码/旧报错）。重发前新建 `launch-authorize-<新ts>.ps1`（只改两个 log 路径），旧 stderr 留档。
- **先只读 status 再决定要不要发新码**：`DWS_CONFIG_DIR=<release>/runtime/.local/dws-config dws.exe auth status` → `{"success":true,"authenticated":false,"message":"未登录"}`；只报布尔，不打印其他字段。已授权则停止，不重复登录。
- **新码生成后立刻投递本人**：取 stderr 里「授权链接（已填入授权码）」那行的 `device/**verify**.htm` 整行（不改路径、不改参数），发给用户本人既有 Home 会话；投递纪律见 skill `hermes-telegram-delivery` 与 `agent-mesh-networking` 的「敏感凭据类通知」小节。
- 完整启动模板/解析片段/汇报形态：`references/hidden-process-and-device-auth-2026-10-21.md`。

## 运行期核查（启用后：任务 + 状态只读审计，2026-10-21 实案）

场景：对方/用户说「启用动作的回复超时了，但执行可能已经发生」，要求**只做一次真实只读核查并立即回执**。
**不接受「超时 = 没执行」的推断** —— 一条 `status` + 计划任务 info 就能定论，且绝不能靠重跑安装来「验证」。

判定顺序（一次抓全，四项都拿到再下结论）：
1. **激活标记** `<release>/runtime/.local/home-enabled.json` 存在，`homeId`/`bundleId` 与 `home-deployment.json`、`manifest.json` 三处一致，`oldWriterStopped:true`。
2. **计划任务** 用 PowerShell `Get-ScheduledTask` + `Get-ScheduledTaskInfo`（比 `schtasks /Query` 稳：直接给 `State/Enabled/LastRunTime/LastTaskResult/NextRunTime/NumberOfMissedRuns`，且无 GBK 乱码）。`LastTaskResult=0` 才叫真跑成功，「Ready」只说明没卡住。
3. **`node deployment/home.mjs status`**（node 用绝对路径、cwd=release）→ `enabled/runnerLockPresent/lastCalendar/lastMail/observations`。
4. **进程面** `Get-CimInstance Win32_Process | ?{$_.CommandLine -match 'Install-|work-runner|activate'}` —— 无命中即安装器已退出；顺带能发现别的会话在并发跑只读 `client state`（照实说明「非本核查发起」）。

坑：
- 🔴 **从 bash 里跑 PowerShell 内联 `-Command` 会被 `$` 展开吃掉**：`powershell -Command "$t=Get-ScheduledTask ..."` 传进去变成 `if(-not ){...}` 语法错 + 中文乱码，不是 PowerShell 坏了。修法：`write_file` 落 `.ps1`（放 `$LOCALAPPDATA/Temp/`），再 `powershell -NoProfile -ExecutionPolicy Bypass -File '<abs>/x.ps1'`。
- 🔴 **`work-automation-status.json` 不带 `calendar.complete/mail.complete/backup.status/drill.complete`**：它只是**本轮**状态 `{startedAt,hostId,calendar,commands,error,finishedAt}`。要那几项必须读 `work-automation-observation.jsonl`（每轮一行，挑带 `mail`/`backup` 的那条）和 `work-host.json`（`lastCalendar/lastMail/lastBackup/backupAttemptAt`）。回执必须写明字段出处，别把「该文件没有这字段」讲成「这项没完成」。
- **短周期 observation 空转是节流，不是故障**：`work-runner.mjs` 里 `calendar/mail` 需距上次 ≥15 min、`backup` 每日一次（`lastBackup==今天` 且距 `backupAttemptAt` >15 min）。连续几条 `calendar:null`、无 mail/backup 字段、`error:null` = 正常空转；判「成功」看首条完整 observation。拿不准就 `grep -n 'lastCalendar\|lastMail\|lastBackup' runtime/scripts/work-runner.mjs` 对代码，别猜。
- **`home-enabled.json` 里带过来的 `expiresAt` 过期不阻断运行**：`home.mjs run` 守卫只校验 `homeId/bundleId/oldWriterStopped`（`activate` 才要 30 min 内的 permit）。别把过期当成故障去重新 activate。
- **1 分钟重复的任务 State 会在 Ready/Running 间跳**：抓到 Ready ≠ 没在跑，以 `LastRunTime` + `LastTaskResult` 为准；同时报 `NextRunTime` 与 `MissedRuns`。
- **回执脱敏**：报 homeId/bundleId、执行程序与 Arguments 路径、触发器（`PT1M` + `AtLogOn`）、首次完整运行的各段**计数**（mail observed 16、bodyFailures 0、backup bytes/items）、最近 N 条状态摘要；**不回** signature、回填密钥、邮件标题全文、连接秘密。
- **发现字段缺失先分类**：是「这文件本来不装这字段」还是「真失败」——报告缺失 + 安装进程状况，把下一步交回对方，不自行恢复旧端、不重跑安装。
- 完整脚本与输出映射：`references/runtime-audit-2026-10-21.md`。

## 受控写入验收：幂等双发 + 基线 diff（2026-10-21 实案，Dayflow HD.4）

场景：部署完成后协调端（含 A2A peer）要求「只测客户端写入通道」——建一条明确标记、可撤销的测试项 → 同 request-id 重发证明幂等 → 置 cancelled → 证明真实数据零变化。

铁律：
- 只建**未来日期 + 标题带任务号 + notes 写明「验收后取消」** 的测试项；不改任何真实事项，不新增复盘/成果/执行分钟。
- 第一条动作就是**基线快照**：`client state > runtime/.local/<task>-state-before.json`，另生成 `<task>-baseline-manifest.json`（每条的 id/version/status/category/source + **title 的 sha256 前 12 位**）。标题只存哈希，回执里就没有真实日程全文可泄。
- **幂等靠 request-id 映射到 `Idempotency-Key` 头**：重发必须逐字同正文 + 同 UUID，回执 `result.id` 相同即通过。**绝不换 UUID 重试**（那就是重复写入）。
- 写后**回读** items 与 state 两份，再跑 diff：原始条目 missing=0 / changed=0、goals 数量与 version 不变、reviews 不变、executions 总数与 actualMinutes 合计不变、revision 前进而 items 只 +1。可直接用 `scripts/state-baseline-diff.js`。
- 分类取 state 里**已存在**的分类，不新建；无固定钟点事项用 `start:""`/`end:""`（空串，别传 null）。
- 状态改动用 `patch` 且必须带**最新 version**；`status:"cancelled"` 只置状态，**不声称物理删除/清空历史**。同正文同 request-id 重发 patch → 同 id 且 version 不再自增（幂等落在 version 上）。
- 回执口径：测试 ID、幂等布尔、cancelled 状态、原数据保持布尔、前后计数、成功时间（UTC + 北京双写）、落盘文件清单；不出现密钥，也不出现真实标题。
- 落盘统一 `runtime/.local/` + `icacls` 核权限面（MSYS `chmod` 对 NTFS 无效）。

坑：`client <op> --help` **不是**有效用法（回 `{"error":"请求必须是 JSON"}`），别据此判定写入通道坏。参数解析在 `runtime/scripts/hermes-local.mjs`（`--json-file` / `--request-id`），无参数 `client` 才打印子命令清单；`home.mjs client …` → `hermes-cloud.mjs` → `hermes-local.mjs` → `hermes-client.mjs` 四层委派。

完整命令与回执原文：`references/controlled-write-idempotency-2026-10-21.md`。

## 自然轮次观察器：安装 / 修正 / 启动与自检（2026-10-21 实案，Dayflow 61号）

场景：协调端（常是 A2A peer）要求「**排除安装首轮，只统计后面两轮自然 calendar+mail，间隔 ≥14.5 min**」的自动验收，落地为一个有限时长（≤40 min）、只读的 Node 观察器：每 30 s 刷新一个脱敏 receipt。

铁律：
- 观察器**只读** `work-automation-observation.jsonl`，只写 `<release>/runtime/.local/natural-two-cycles.json`（`.tmp` + rename 原子替换）；无网络、无 spawn、不改生产配置/同步，40 min 到点自退。
- 🔴 **本地 runId ≠ 云端 WorkRecord.id**：两者是不同命名空间。排除表必须填**本地首次轮**的 calendar/mail runId（本次 `6cdc7774…` / `7f54e822…`）；误填云端 record id → 安装首轮被当成第 1 个自然轮 → `passed:true` **假通过**（本次即此 bug，旧 receipt 的 `calendar[0]` 正是 `6cdc7774…`，一眼可证）。
- 必须有 `baselineVerified`：日志里存在「该本地 runId 且 `backup.status==='complete'`」的安装基线行，否则**不判通过**（`exit 3` 直接拒绝）。「找不到基线」≠ 通过。
- 修完先**保全旧证据**：`cp -p natural-two-cycles.json natural-two-cycles.invalid-first.json`（`-p` 保 mtime）。别直接覆盖，旧 receipt 就是误判证据。
- 启动前**必须核对无同名进程**，且核对方式要对（见下）。
- 不手动触发同步冒充自然轮；不跑 work-runner、不 Install-HomeTask、不动同步时间戳、不发 Telegram/不新增长期计划任务。用户明确说过「牛来端不便重启」→ 不重启电脑/gateway/代理、不改电源。

启动姿势（隐藏 + 两级 PID）：

```powershell
$p = Start-Process -FilePath 'C:\Windows\System32\wscript.exe' `
  -ArgumentList '/B','/NoLogo', '<release>\runtime\scripts\run-node-hidden.vbs',
                '<tools>\node24\node.exe', '<abs>\observe-home-natural-cycles.mjs', '<abs cwd>' `
  -WindowStyle Hidden -PassThru
```
- `run-node-hidden.vbs` 收 **3 个参数**（node.exe / script / 工作目录），内部 `shell.Run(cmd, 0, True)` **阻塞到 node 退出** → 必须 `Start-Process` 异步起；前台等会把调用方挂满 40 min。
- PID 要两级：wscript PID（`$p.Id` + `StartTime`）+ 子进程 `node.exe` PID（`ParentProcessId -eq <wscriptPID>`，带 `CreationDate`）。只报一个不算核对。

🔴 **进程去重检查的假阳性**：`Get-CimInstance Win32_Process | ?{$_.CommandLine -match 'observe-…'}` 会命中**自己这条 PowerShell 命令**和 bash 包装层（本次数出 4，实际 0）。必须加 exe 名限定：
`?{$_.Name -eq 'node.exe' -and $_.CommandLine -like '*observe-home-natural-cycles.mjs*'}`；列 `ProcessId/ParentProcessId/CreationDate/CommandLine` 四项。

- 从 bash 调内联 `powershell -Command`：简单单行用 `\$` 转义 `$_`/`$p` 可跑（本次全程如此）；一旦要变量+循环+多语句，仍退回 `.ps1` + `-File`。
- 判读：receipt 首轮常是 `passed:false` —— 那是**正确**结果（基线被排除后只剩 1 个自然轮），别当失败。从最后一个自然轮 `startedAt` +14.5 min 起才有资格翻 `true`；40 min ≈ 2 个 15 min 节流周期，够覆盖。到点 `timedOut:true` + exit 2。
- 覆盖共享 runtime 目录里别的会话写过的文件时，`write_file` 可能报 sibling-agent 警告；覆盖前先用 read 类调用确认内容，避免盖掉别人的改动。
- 汇报形态：审读结论（只读什么/只写什么）→ 证据保全文件 → 覆盖后 md5/字节数/关键 ID 断言 → 启动前进程计数 0 → wscript/node 两级 PID + 启动时间 → **当前 receipt 全文或关键字段** → 一句「下一步等第 2 个自然轮，我不手动触发」。

完整观察器源码、启动/核对命令、首轮 receipt 原文：`references/natural-cycle-observer-2026-10-21.md`。

## 授权完成后的只读验收（用户说「显示授权成功，你试试」）

**别只看 `authenticated: true` 就报成功 —— 要真读一次日历和邮件，把「可读」证明出来**：

```bash
$DWS auth status          # 布尔 + 到期时间，不打印 token
$DWS doctor               # 五项体检，授权后应为 4 pass·1 warn·0 fail
$DWS calendar +book-list  # 日历本列表
$DWS calendar +agenda     # 今天日程（不传时间默认今天）
$DWS mail +recent-mail / +unread-mail
```

脱敏口径：对外/对 A2A peer 只报**可读布尔 + 数量**（日历本 N 个 / 今日 N 条 / 未读 N 封 / doctor X pass）；不报邮箱地址、组织 ID、userId、token。

坑：`doctor` 首跑报 `Runtime context unavailable` 是**预热**，第二次即 ready，别据此重装；`+agenda` 的 `count:0` 要结合 `ok:true` 判读（真没日程 vs 读失败）；协调端锁定的版本不因「有新版本」提示而去 `upgrade`。

另一个维度：`client items` 返回**裸 JSON 数组**（不是 `{"items":[…]}`），解析要 `items = d if isinstance(d, list) else d.get('items', [])`；`client state` 才是对象。查某天用全量后本地按 `date` 过滤，并**排除 `cancelled`**。

详见：`references/dws-auth-readonly-verify-2026-10-21.md`。

## 交付物清单（本类任务的验收）
- D1 代码+依赖跑通（具体命令 + 退出码 0）
- D2 密钥安全（config 无明文；密钥独立文件被 gitignore）
- D3 全链路真实验证（真实推送/报告产物，不是"看起来能跑"）
- D4 自启（计划任务 /Query 存在且就绪；重启实测可选但推荐）
- D5 看门狗（kill 后自动恢复实测 或 脚本逻辑三态验证：新鲜静默/陈旧触发/连续陈旧告警）
- D6 数据维护（备份文件实际生成）
- D7 用户手册（桌面，含"改完怎么生效"）

## Support Files
- `references/trendradar-deployment-2026-08.md` — TrendRadar 部署实录（项目特定细节、命令、配置值）
- `references/installer-continuation-check-2026-10-21.md` — 安装包型部署的断点续作核查实录（目录/homeId/只读探针/哈希/后续顺序）
- `references/hidden-process-and-device-auth-2026-10-21.md` — 加密信封回填（stdin）+ 隐藏启动设备授权进程 + 从 stderr 解析官方链接/设备码的完整实操
- `references/controlled-write-idempotency-2026-10-21.md` — 受控写入验收（测试项创建/幂等双发/patch 取消/基线 diff）完整实操与回执原文
- `references/dws-auth-readonly-verify-2026-10-21.md` — 第三方 CLI 授权后的只读验收：dws 六连探针、doctor 预热坑、`client items` 裸数组解析
- `scripts/state-baseline-diff.js` — 通用基线比对：两份 state JSON → 计数/新增/缺失/变更（标题只输出哈希）
- `references/runtime-audit-2026-10-21.md` — 启用后的运行期只读审计：计划任务 PowerShell 脚本、status/observation/work-host 三份文件的字段映射与判定阈值
- `references/natural-cycle-observer-2026-10-21.md` — 自然轮次观察器：只读 observation.jsonl 的验收脚本源码、隐藏启动 + 两级 PID、进程假阳性排查、首轮 receipt 判读
- `scripts/log_freshness_watchdog.py` — 通用日志新鲜度看门狗模板（参数化，复制改 BASE/LOG/START_CMD 即可）
- `templates/start_service.bat` — 启动脚本模板（PYTHONPATH 清理 + 密钥加载 + 日志重定向）

## See Also
- `china-dev-proxy-setup` — 双网络环境代理配置（部署中代理分流的基础）
- `sprint-contract` / `decision-gate` — 部署类任务仍走契约+闸门（用户可简化后续流程）
- `claude-code-workflow` — GPT-5.6 Sol 审查调用规则（代理红线、smoke test）
