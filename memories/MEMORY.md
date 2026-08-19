绝对禁止 taskkill /F /IM python.exe → 杀Agent自身！杀进程必须 taskkill /PID <pid>，排查用 ps aux/任务管理器。
§
网络:代理127.0.0.1:7897通X+Startpage;Google需CAPTCHA;Bing直连。
§
长prompt用stdin重定向<file(勿用disallowedTools+$(cat f)组合)。delegate_task无per-call provider,子代理继承父模型;L1审查走execute_code直连qwen-bailian API(scripts/qwen_review.py),详见skill l1-review+sprint-contract。
§
路径:引用references/;API key→Desktop/各类api key/;归档YYYY-MM-DD_主题.md;日常脚本放桌面,项目归D:\Workspace\。复盘完整过程写D:\Workspace\Projects\Hermes运维\(用户不要skill,写文件),仅关键经验进memory。
§
外部服务:Tavily=搜索后端,后备Bing直连curl --noproxy '*';高德MCP已配,静态地图参数用location非center。key均在API key目录。
§
MoA=Opus前置筛选器,不确定先探路;/moa用完回DeepSeek。
§
备份:Cyrus1993729/cyhermes_agent(私有);恢复=clone+hermes auth+改代理。
§
小红书→skill xiaohongshu-analysis(链接域xhslink.com/.cn同法)。坑:未登录站内搜索空(searchFeedsWrapper=None)+搜索引擎不收录,找帖只能靠分享链接。
§
TG投递:池耗尽清_request[1];Clash节点111-OVH;cron assume-delivered会静默丢;DM超长(>4096)双投递=TG流式+拆条,去重bug未修;长文仍优先发消息不发文件。
§
TrendRadar双日报→TG:5类8:00+跨境20:30生成/20:40重试/20:45投递/21:00检查(方案C+D分离:Job A写_draft_cb不投递,Job B no_agent deliver_cb.py读文件投递,mtime幂等)。详见skill trendradar-operations。
§
5类8:00+黄金周报周一12:30已定(8/17改,均避峰谷),互不并发
§
投资分析/技术方案须外部大模型sign-off:Opus优先,停订阅则降级GPT5.6/千问3.7Max,不得跳过。审查全自动≤3轮修复,用户只在契约确认+交付时介入。
§
MSYS bash下原生Windows程序(curl/python)不认~/路径参数:curl -o ~/...报exit 23, python ~/script.py报"C:\c\..."路径错。先cd到目标目录用相对路径,或传Windows绝对路径。
§
OpenCode Go直连坑:urllib默认UA被403拦截,必须带User-Agent: curl/8.0.0(requests库不受影响,脚本已加)。gateway重启必须用户手动:会话内任何方式(sleep/schtasks包装)都被安全拦截;schtasks /end显示成功但不杀进程;桌面客户端重启≠gateway;最可靠=重启电脑,或用户双击杀PID脚本后schtasks /run。
§
API故障处理策略(用户2026-08-16定调):遇故障先排查+自动重试(cron双触发20:30/20:40+幂等SILENT),fallback是最后手段(按量付费增费用)勿轻易触发。fallback链已配:deepseek官方(独立,内联key)→opencode-go-anthropic(同源兜底),主链路仍全走Go订阅。
§
模型分层:交互/生成deepseek-v4-flash,MoA聚合deepseek-v4-pro,qwen仅拥堵应急。主链路全走OpenCode Go订阅(opencode-go provider,端点opencode.ai/zen/go/v1;qwen走opencode-go-anthropic;官方key留回滚)。8/18 Flash:月档$30、5h 7,600(8/17涨价缩水$15→8/18廉价搜索行动回升),峰谷价×2(Peak北京9-12/14-18),月占用31-63%宽裕;核实定价须fresh curl(web_extract缓存旧版坑)。cron日报双次api_probe体检;审查daily_report_review.py(GPT5.6);投递铁律=最终回复完整日报;金价认上海金。