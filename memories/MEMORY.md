绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。Claude Code→Opus(CLI非Nous API)，Sonnet筛选。每命令必设代理禁直连。
§
Opus=Claude Code CLI(claude -p --model opus)+代理7897。禁delegate_task。调前smoke test。prompt长→hit max-turns。
§
delegate_task不支持per-call provider，子代理继承父模型。delegation已切qwen3.7-max(custom:qwen-bailian)，比kimi便宜+快(107s vs 570s,15call vs 50call)。L1审查走execute_code直连qwen-bailian API。
§
MoA=Opus前置筛选器。不确定是否值找Opus时先用MoA探路。参考模型一致性不可靠(无完整上下文)。看结果由用户决定升Opus。/moa一次性用完回DeepSeek。
§
矛盾检测规则：当 Agent 在任务中遇到与 memory 里某条记录明显矛盾的事实（比如 memory 说某服务已关闭但实际在运行，或记录的工具版本与当前不符），必须主动告知用户"我发现一条记忆跟现实不符：[矛盾内容]。要更新吗？"——不要默默忽略，也不要自作主张直接改。
§
备份:Cyrus1993729/cyhermes_agent(私有)，clone+hermes auth+改代理。
§
架构:务实最小化。task-wrapup→收尾自检。×hs→xiaohongshu-analysis skill。
§
TG已配(token:Desktop/各类api key/telegram bot token.txt)。API走代理7897，NO_PROXY禁api.telegram.org。
§
33岁男无子女，税后20万/年日常8万，工作日定投纳指。技术小白。技术方案先问Opus。故障先诊断根因。
§
5步:①契约(三问缝合测试,按层拆)→②闸门→③执行(检索可并行delegate_task+综合单模型)→④L1+L2异构审查≤3轮→⑤复盘。workflow_check.py自动打勾+插件修复生效。
§
高德MCP已配置(amap-maps-mcp-server, npm包@amap/amap-maps-mcp-server), API Key: 0e0e...b4, 存储: Desktop/各类api key/amap api key.txt。静态地图API参数名是location不是center——曾因用错参数名误以为权限不足。Python staticmap库(OSM瓦片)被墙不可用，fallback方案: Pillow手绘示意图 或 高德静态地图API直接生成PNG。
§
模型:主=deepseek-v4-pro,delegation=qwen3.7-max(custom:qwen-bailian)。kimi已弃用(贵+慢+易欠费)。
§
DS不支持Vision:image_url→400。×hs图文帖→正文密集基于desc，稀疏用Qwen替代。
§
核心决策(Opus共识):①先判可拆性——缝合代价>切分收益不拆，整块交一个脑子。②流程抬地板非天花板——怕翻车用流程，求惊艳直干Opus。③handoff有损压缩传what丢why，损耗超线性。④审查深度<执行深度，Opus别只当终审——核心难题Opus主导执行。⑤迭代有值前提:新信息注入。
§
流程边界:①连贯判断密集需全局一致→Opus直干。②可干净切分规格明确→Kanban+流程。③探索性边界不清→先Opus再流程化。④拆前问:缝合<切分?
§
审查短板(2026.7.24):L1只查形式不查质量。需增L2实质审查(异构模型查逻辑/证据链/盲区/推理深度)。更新l1-review或新建l2-review skill。
§
用户理解偏好:需要全局视角才安心——喜欢在动手前看到完整流程图或结构化总览。对复杂系统先问"整体是什么样的"再深入细节。流程设计类讨论必请Opus给第二意见。
§
纳指定投渠道：人民币QDII基金（非美元直投QQQ）。QDII有限购/溢价/折价，分析纳指时须含QDII特有因素。
§
并行检索:delegate_task 3路扇出+综合单模型。kimi-k3 50+calls/agent易欠费。估计值方向可能全反(PPI估-2%实+4.1%)。直接抓官网(stats.gov.cn/pbc.gov.cn)>搜Bing。子代理HTML是二次宝藏。