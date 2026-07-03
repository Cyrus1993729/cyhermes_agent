绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
用户习惯：遇到故障先诊断根因（如Claude联网失败必须查原因不能绕过）。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。Claude Code→Opus(CLI非Nous API)，Sonnet筛选。每命令必设代理禁直连。
§
产业链早信号框架（6-25）：涟漪三问+确认器三层交叉(设备/环评/下游)+时间序列自洽。alpha=抓取难度，环评/备案爬虫ROI最高。雷达层已放弃。详见references/
§
微信:Agent一次回复=网关一次投递,无法逐条控节奏。超长分段方案:一条回复只发一段,结论放第一条,不自检不塞额外,MEDIA单独发,丢失即重发。三需求超单条容量时物理死结→task-wrapup skill。
§
用户33岁男性，无生育计划。税后年收入¥20万，日常¥8万，保险¥3万，年结余¥9万。手头¥5万应急金。房交付4年，车买2年。投资：仅工作日（250天/年）定投纳指场外基金，20-30年长期。分析偏好：要求权威来源+可拆分口径，不接受不同标准混比；坚持从第一性原理推导，不接受预设立场结论；被质疑时要求重新验证而非辩解。沟通：对所有输出和报告统一用中文。
§
Opus调用=Claude Code CLI(`claude -p --model opus`)+代理127.0.0.1:7897。禁delegate_task调Opus。调前smoke test。代理export必做。
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