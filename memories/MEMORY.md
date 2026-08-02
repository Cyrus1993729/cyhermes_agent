绝对禁止 taskkill /F /IM python.exe → 杀死Agent自身！杀进程必须 taskkill /PID <pid>。资源排查用 ps aux 或任务管理器。
§
行为红线：未经同意禁止①换模型②改文件/skill/配置。流程：出方案→确认→执行。
§
网络：代理127.0.0.1:7897通X+Startpage；Google需CAPTCHA。Bing直连。Claude Code→Opus(CLI非Nous API)，Sonnet筛选。每命令必设代理禁直连。
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
高德MCP已配置(amap-maps-mcp-server, npm包@amap/amap-maps-mcp-server), API Key: 0e0e...b4, 存储: Desktop/各类api key/amap api key.txt。静态地图API参数名是location不是center——曾因用错参数名误以为权限不足。Python staticmap库(OSM瓦片)被墙不可用，fallback方案: Pillow手绘示意图 或 高德静态地图API直接生成PNG。
§
DS不支持Vision:image_url→400。×hs图文帖→正文密集基于desc，稀疏用Qwen替代。
§
流程边界:①连贯判断密集需全局一致→Opus直干。②可干净切分规格明确→Kanban+流程。③探索性边界不清→先Opus再流程化。④拆前问:缝合<切分?
§
用户理解偏好:需要全局视角才安心——喜欢在动手前看到完整流程图或结构化总览。对复杂系统先问"整体是什么样的"再深入细节。流程设计类讨论必请Opus给第二意见。
§
纳指定投渠道：人民币QDII基金（非美元直投QQQ）。QDII有限购/溢价/折价，分析纳指时须含QDII特有因素。
§
并行检索:delegate_task 3路扇出+综合单模型。kimi-k3 50+calls/agent易欠费。估计值方向可能全反(PPI估-2%实+4.1%)。直接抓官网(stats.gov.cn/pbc.gov.cn)>搜Bing。子代理HTML是二次宝藏。
§
流程改进必须Opus审(2026.7.27确立):任何5步流程/skill/架构级别的改进方案，出方案后必须先发Opus审查再落地。包括但不限于:流程重构、审查规则变更、闸门设计、skill拆分合并。复盘后的修改方案也要Opus审。
§
审查架构v3.2:同6维异站位→接地三模式→路由(fact/value+fail-safe)→补证据→千问盲审(证据持平决胜)→≤2轮修复(双模震荡)→通过门禁。影子→软闸→硬闸。千问=L1退场转盲审。契约深度=报告天花板。
§
Opus:-p模式+代理7897+stdin/dev/null。Codex:exec禁用pty(已修)+sandbox danger-full-access+代理7897。Claude+GPT均$20/月成本对等。主模型=ds-v4-pro,审查=Codex+Opus,千问=盲审决胜,delegation=qwen3.7-max。Opus沙箱隔离审查必须内联全文。契约审max-turns 3,报告审5-10。
§
新5步流程:触发"走新5步流程"。dual-review→Codex+Opus双审→≤2轮自动修复(无人工干预)。主动监控:bg任务每~2min poll报告。Opus沙箱:审查必须内联全文。Codex:exec禁用pty。
§
双审实战:Opus抓逻辑断裂(D2),Codex抓数据精度(D3)。单审会漏。用户纠正:Opus+Codex均为$20/月,成本对等,CLI方式相同。分析深度:用户口头指定L3深度,契约"包含XX"只保覆盖不够。
§
用户要求Agent主动监控任务进展，每2-3分钟主动poll后台进程，不要让用户等不及了手动问"进展呢"。发后台任务后告知预计时间+定期主动报进度。