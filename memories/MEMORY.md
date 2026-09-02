绝对禁止taskkill /F /IM python.exe(杀Agent自身);杀进程须taskkill /PID <pid>;MSYS下TASKKILL.EXE /PID <pid> /F(//PID双斜杠报错,cmd //c开交互),排查用ps aux。
§
网络:代理127.0.0.1:7897通X+Startpage;Google需CAPTCHA;Bing直连。
§
长prompt用stdin重定向<file(勿用disallowedTools+$(cat f)组合)。delegate_task无per-call provider,子代理继承父模型;L1审查=qwen3.7-max经OpenCode网关(qwen_review.py读config qwen-bailian段09-01起指向opencode,需UA:curl/8.0.0),详见skill l1-review+sprint-contract。
§
路径:引用references/;API key→Desktop/各类api key/;归档YYYY-MM-DD_主题.md;项目归D:\Workspace\。复盘写Hermes运维\(用户不要skill,写文件),关键经验才进memory。
§
外部服务:Tavily=搜索后端,后备Bing直连curl --noproxy '*';高德MCP已配,静态地图参数用location非center。key均在API key目录。
§
备份:Cyrus1993729/cyhermes_agent(私有);恢复=clone+hermes auth+改代理。
§
小红书→skill xiaohongshu-analysis(链接域xhslink同法)。坑:站内搜索空+引擎不收录,找帖只能靠分享链接。
§
TG投递:池耗尽清_request[1];cron assume-delivered静默丢;超长拆条+双投递(去重bug未修);长文优先发消息。
§
日报体系:5类8:00/跨境20:30生成+20:40重试+20:45投递+21:00检查/黄金周报周一12:30,生成投递分离+mtime幂等+去重。详见skill trendradar-operations。
§
投资分析/技术方案须外部大模型sign-off:GPT-5.6主导(Opus冻结不恢复,判别见claude-code-troubleshooting);GPT-5.6撞5h限额→deepseek-v4-pro直连opencode审契约(9/1拍板),姿势见hermes-china-providers;审查全自动≤3轮,用户只在契约确认+交付时介入。
§
MSYS bash下原生Windows程序(curl/python)不认~/路径参数:curl -o ~/...报exit 23, python ~/script.py报"C:\c\..."路径错。先cd到目标目录用相对路径,或传Windows绝对路径。
§
OpenCode直连坑:urllib默认UA被403拦截,须带User-Agent:curl/8.0.0。gateway重启必须用户手动(会话内sleep/schtasks均被拦;schtasks /end装睡;桌面重启≠gateway;最可靠=重启电脑或杀PID后schtasks /run)。
§
API故障处理策略(用户2026-08-16定调):遇故障先排查+自动重试(cron双触发20:30/20:40+幂等SILENT),fallback是最后手段(按量付费增费用)勿轻易触发。fallback链已配:deepseek官方(独立,内联key)→opencode-go-anthropic(同源兜底),主链路仍全走Go订阅。
§
模型分层(9/1):GPT-5.6(Codex)=大脑,深度/审查/sign-off每周几次(Plus周限额隐性墙);OpenCode=主力90%(8/31实测月18.2%/Flash$30配17.9%/qwen3.7-max$60配0.2%,余量大);Claude释放$20/月先留用。交互/生成deepseek-v4-flash,MoA聚合deepseek-v4-pro,端点opencode.ai/zen/go/v1;峰谷×2(北京9-12/14-18)错峰;定价fresh curl;cron日报api_probe体检;daily_report_review=GPT5.6;投递铁律=最终回复完整日报;金价认上海金。
§
Clash卡死=全网断(8/29-30 44h):TG/模型API/newsnow采集全走代理,告警随TG失明;诊断先问用户屏幕/重启状态。
§
Hermes升级(本机10年双核v0.19.1):计划升v0.21 Pantheon(新增hermes peer官方跨机A2A,v0.19无peer);路线=新机先装v0.21验证peer→老机再升→冻结;升级提速=停gateway+pip镜像+Defender排除+超时≥600s;交接包D:\Workspace\Projects\Hermes运维\2026-08-31_升级交接_GPT接手.md