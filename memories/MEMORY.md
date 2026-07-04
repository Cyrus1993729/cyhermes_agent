绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
用户习惯：遇到故障先诊断根因（如Claude联网失败必须查原因不能绕过）。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。Claude Code→Opus(CLI非Nous API)，Sonnet筛选。每命令必设代理禁直连。
§
微信交付见task-wrapup skill，>1500字拆段。
§
用户33岁男，无子女。税后年入¥20万，日常¥8万，年结余¥9万+应急金¥5万。投资：工作日定投纳指(20-30年)。分析：权威来源+可拆分口径+第一性原理。中文沟通。
§
Opus=Claude Code CLI(`claude -p --model opus`,默认claude-opus-4-20250514/4.8)+代理127.0.0.1:7897。禁delegate_task。调前smoke test。pitfall:prompt长→hit max-turns,--bare需ANTHROPIC_API_KEY(不可用),OAuth token会过期(Google Play订阅)。
§
delegate_task不支持per-call provider，子代理继承父模型。L1审查走execute_code直连qwen-bailian API。审查脚本: scripts/qwen_review.py，skill: l1-review+sprint-contract。memory: MEMORY.md/USER.md，§分隔。
§
引用索引：references/(26文件+工作方法论+个人偏好+美股投资+产业链框架+Scrapling)；yiweijun_kb/articles/(15篇一味君)；API key→Desktop/各类api key/；归档规则:YYYY-MM-DD_主题.md
§
MoA定位：Opus的前置筛选器（非共识/分歧判定器）。当Agent或用户不确定一个问题值不值得找Opus时，先用MoA探路。不看参考模型是否一致来决定升级——参考模型看不到完整上下文，一致性不可靠。看完MoA结果后由用户决定是否升Opus。日常对话不用MoA，/moa一次性调用，用完自动回DeepSeek。
§
矛盾检测规则：当 Agent 在任务中遇到与 memory 里某条记录明显矛盾的事实（比如 memory 说某服务已关闭但实际在运行，或记录的工具版本与当前不符），必须主动告知用户"我发现一条记忆跟现实不符：[矛盾内容]。要更新吗？"——不要默默忽略，也不要自作主张直接改。
§
L1审查触发：交付物收尾→contract→qwen_review.py→呈报。FAIL/CONDITIONAL≥3停报。阶段切换先post-task-review(→lessons.md)再l1-review。禁止跳过。
§
备份恢复：Cyrus1993729/cyhermes_agent(私有)，恢复=clone+hermes auth+改代理。
§
架构:务实最小化,先跑通再加复杂度。task-wrapup(收尾自检:步骤/来源/审查/存档/分段,短路质量门不过不进投递,自检摘要不发微信)。×hs视频帖四步→xiaohongshu-analysis skill。
§
主动汇报：任务进行中和完成时都必须主动告诉用户进展或结果，不能沉默等用户问。
§
流程触发词："走流程"=5步闭环(sprint-contract→decision-gate→执行→task-wrapup→post-task-review)，自动建workflow追踪文件；"看文档走完"=读追踪文件从未勾步骤继续。涌现型任务诊断完触发。
§
微信 iLink 限制真相：context_token 每轮仅 10 条回复额度（非速率限流），超过全丢。用户发新消息刷新 token。weixin.py 已有退避重试+3s发送间隔，但不能突破 10 条硬限。修复在 context_compressor.py 等待重启。
§
用户偏好：技术方案选择时先问 Opus（Claude）获取建议，不自己做架构决策。技术小白但理解概念。
§
Telegram 已是主通信平台(token:8839546337:***)，替代微信(iLink限10条)。hermes-backup+x-monitor cron已迁至telegram。
§
Telegram Bot API(api.telegram.org)被墙证实(curl直连超时/代理2.5s通)。Hermes网关收发TG必须走代理。手机端TG App也需代理。.env的NO_PROXY禁止含api.telegram.org。
§
网络诊断铁律：禁止凭'常识'断言国内网络可达性。做任何网络配置改动前，先curl直连+代理对比测试确认。