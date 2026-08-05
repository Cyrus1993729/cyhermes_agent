绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。Claude Code→Opus(CLI非Nous API)，Sonnet筛选。每命令必设代理禁直连。
§
Opus=Claude Code CLI(claude -p --model opus)+代理7897。OAuth过期→`claude auth login`(非`claude login`),需background+pty保本地服务器收回调。PS找不到npm全局命令用CMD/git-bash。WinStore Desktop覆盖CLI→npm重装。
§
delegate_task不支持per-call provider，子代理继承父模型。L1审查走execute_code直连qwen-bailian API。审查脚本: scripts/qwen_review.py，skill: l1-review+sprint-contract。memory: MEMORY.md/USER.md，§分隔。
§
引用索引：references/(26文件+工作方法论+个人偏好+美股投资+产业链框架+Scrapling)；yiweijun_kb/articles/(15篇一味君)；API key→Desktop/各类api key/；归档规则:YYYY-MM-DD_主题.md
§
MoA=Opus前置筛选器。不确定值不值得找Opus时先用MoA探路。不看参考模型一致性(无完整上下文)。/moa一次性用完回DeepSeek。
§
矛盾检测规则：当 Agent 在任务中遇到与 memory 里某条记录明显矛盾的事实（比如 memory 说某服务已关闭但实际在运行，或记录的工具版本与当前不符），必须主动告知用户"我发现一条记忆跟现实不符：[矛盾内容]。要更新吗？"——不要默默忽略，也不要自作主张直接改。
§
备份恢复：Cyrus1993729/cyhermes_agent(私有)，恢复=clone+hermes auth+改代理。
§
架构:务实最小化,先跑通再加复杂度。task-wrapup(收尾自检:步骤/来源/审查/存档/分段,短路质量门不过不进投递,自检摘要不发微信)。×hs视频帖四步→xiaohongshu-analysis skill。
§
Telegram主平台(token:8839546337:***)，微信已弃(iLink限10条)。TG Bot API被墙须走代理，NO_PROXY禁含api.telegram.org。备份+x-monitor cron已迁TG。网络诊断：先curl直连+代理对比，禁凭常识断言可达性。TG池耗尽修复：_drain_send_connections清_request[1]，pool timeout时自动触发不再需重启。
§
用户画像：33岁男无子女，税后¥20万/年日常¥8万，工作日定投纳指(20-30年)。技术小白懂概念。中文沟通。故障先诊断根因不绕过。技术方案先问Opus。主动汇报进展不沉默。
§
5步闭环:①契约(Opus审)→②闸门→③执行→④审查(L1+Opus)→⑤复盘。审查全自动≤3轮修复。用户只在契约确认+交付时介入。投资分析须Opus sign-off。
§
Tavily已配为Hermes搜索后端(web.backend=tavily, web.search_backend=tavily)。Key在Desktop/各类api key/Tavily API key.txt。需网关重启后web_search工具才出现。后备:Bing直连(curl --noproxy '*')+grep。
§
高德MCP已配置(amap-maps-mcp-server, npm包@amap/amap-maps-mcp-server), API Key: 0e0e...b4, 存储: Desktop/各类api key/amap api key.txt。静态地图API参数名是location不是center——曾因用错参数名误以为权限不足。Python staticmap库(OSM瓦片)被墙不可用，fallback方案: Pillow手绘示意图 或 高德静态地图API直接生成PNG。
§
向日葵(AweSun)路径: /c/Program Files/Oray/AweSun/AweSun.exe。启动: background=true 运行该exe即可。
§
复盘vs memory分开：关键经验精简进memory，完整过程写复盘文件到D:\Workspace\Projects\Hermes运维\。桌面：日常脚本保留桌面，项目文件按主题归D:\Workspace\。