绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。
§
长prompt用stdin重定向<file(勿用引号disallowedTools+$(cat f)组合→Permission deny rule崩)
§
delegate_task不支持per-call provider，子代理继承父模型。L1审查走execute_code直连qwen-bailian API。审查脚本: scripts/qwen_review.py，skill: l1-review+sprint-contract。memory: MEMORY.md/USER.md，§分隔。
§
引用:references/;yiweijun_kb/articles/;API key→Desktop/各类api key/;归档:YYYY-MM-DD_主题.md
§
MoA=Opus前置筛选器,不确定先探路。/moa用完回DeepSeek。
§
矛盾检测:发现与memory矛盾主动问用户是否更新,不默默忽略不自作主张改。
§
备份:Cyrus1993729/cyhermes_agent(私有),恢复=clone+hermes auth+改代理。
§
×hs→xiaohongshu-analysis skill(链接域xhslink.com/.cn同法;未登录站内搜索空searchFeedsWrapper=None+搜索引擎不收录,找帖只能靠分享链接)。
§
TG池耗尽:_drain_send_connections清_request[1],pool timeout自动触发无需重启。
§
用户画像：33岁男无子女，税后¥20万/年日常¥8万，工作日定投纳指(20-30年)。技术小白懂概念。中文沟通，英文阅读弱(外文需翻译)。故障先诊断根因不绕过。技术方案先问Opus。主动汇报进展不沉默。交付只发成品不裹多余说明。
§
5步闭环:①契约(Opus审)→②闸门→③执行→④审查(L1+Opus)→⑤复盘。审查全自动≤3轮修复。用户只在契约确认+交付时介入。投资分析须Opus sign-off。
§
Tavily已配为Hermes搜索后端(web.backend=tavily)。Key在Desktop/各类api key/Tavily API key.txt。后备:Bing直连curl --noproxy '*'。
§
高德MCP已配(amap-maps-mcp-server)，Key在Desktop/各类api key/amap api key.txt。静态地图API参数是location非center。
§
复盘vs memory分开：关键经验精简进memory，完整过程写复盘文件到D:\Workspace\Projects\Hermes运维\。用户不要skill，复盘写文件即可。桌面：日常脚本保留桌面，项目文件按主题归D:\Workspace\。
§
两台电脑:高配=WorkBuddy(A2A)+Codex;本机=Hermes+ClaudeCode+Codex。EigenFlux CLI装D:\eigenflux(邮箱335751596@qq.com),只DM不订阅广播;CLI用PowerShell包装防guard误判。多agent愿景:同步讨论非文件接力,Claude/Codex啃难+Hermes啃易;成本敏感按需勿常驻;三agent暂缓。
§
TrendRadar双日报(跨境16:00+5类9:30 hot-only)→TG。管线:crossborder_fetcher+fetch_summaries+prepare_candidates(--crossborder-only/--hot-only,url防重复)。关键词v1.1。子进程unset PYTHONPATH。调度:采集=Windows计划任务TrendRadarHourly/TrendRadarCrossborder跑bat,Hermes cron只读库编辑。坑(08-08):bat必须ASCII+mkdir,UTF-8中文注释被cmd GBK误解析致任务全失败;watchdog run.log缺失曾静默→已改告警+触发。详见复盘2026-08-07
§
用户常要"助手答一次+Opus答一次"双方案对比后拍板；先实测给数据再答复。多帖分析后的"如何应用"思考→逐帖独立Opus prompt并行，不打包成大prompt(08-08纠正)。
§
深度分析交付：逐帖独立思考（每帖一个Opus prompt并行跑），不搞多帖大杂烩（用户原话：挨个思考，不要一股脑塞给opus）。