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

0. **前置选型**：Docker vs 本地 uv vs 云服务器——结合机器配置（老笔记本跑 Docker Desktop 的 WSL2 虚拟机很吃力）、网络（国内机器走本地代理 vs 云服务器需额外配代理）、常驻情况（电脑是否 24h 开机）判断。出契约（sprint-contract）+ 用户确认（decision-gate）；部署类任务用户可简化流程（跳过 L1/复盘，契约 + Opus 审查仍要）
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
- **Opus 契约审查**：`claude -p --model opus` 加 `--tools ""` 禁用工具，否则 Opus 把 max-turns 耗在工具调用上返回 "Reached max turns" 无输出；max-turns 给 8
- **验证改动**：写完脚本/配置跑 ad-hoc 验证脚本（tempfile 路径 + `hermes-verify-` 前缀，跑完删除），输出逐项 PASS/FAIL，明确标注"ad-hoc 验证，非测试套件"
- **增量/去重基准陷阱**：增量模式常是"当天内"去重（存储按天分库）——跨天第一次运行会把昨天推过的内容全当"新增"再推一遍（重复！）。实现跨天增量需改两处：①查重范围扩展为"昨天+今天"合并 ②"当天第一次"分支不能直接全量，也要走新增检测（详见 references/trendradar-deployment-2026-08.md 推送模式小节）
- **看门狗阈值 vs 推送频率**：阈值必须适配推送间隔——每小时推送用 4h 阈值没问题；改成每天 2 次（间隔 9-15h）后必须调大到 ~16h，否则两次推送之间必误报"疑似故障"
- 🔴 **密钥禁止从截断输出猜测**：从 `head -c`、打码（`***`）等截断输出拼密钥写入配置 = 严重错误（2026-08-06 实踩：拼错 DeepSeek key 写入 run_secrets.bat，验证时才发现）。必须完整读取源文件，写入后做格式断言（如 `sk-` 前缀 + 长度）

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
- `scripts/log_freshness_watchdog.py` — 通用日志新鲜度看门狗模板（参数化，复制改 BASE/LOG/START_CMD 即可）
- `templates/start_service.bat` — 启动脚本模板（PYTHONPATH 清理 + 密钥加载 + 日志重定向）

## See Also
- `china-dev-proxy-setup` — 双网络环境代理配置（部署中代理分流的基础）
- `sprint-contract` / `decision-gate` — 部署类任务仍走契约+闸门（用户可简化后续流程）
- `claude-code-workflow` — Opus 审查调用规则（代理红线、smoke test）
