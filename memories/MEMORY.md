MSYS chmod 对 NTFS 无效,收紧文件权限用 icacls /inheritance:r。PowerShell 内联 -Command 经 bash 会被 $ 吃掉→写成 .ps1 再用 -File 跑。
§
网络:v2rayN 10808=主线路(断=全网断),Hermes 代理均已指向;Google 需 CAPTCHA,Bing 可直连(后备 curl --noproxy '*')。
§
长 prompt 用 --query-file 传文件(勿用 $(cat f))。delegate_task 无 per-call provider,子代理继承父模型。L1 审查见 skill l1-review。
§
路径:项目→D:\Workspace\;API key→Desktop/各类api key/;归档 YYYY-MM-DD_主题.md;复盘写文件不写 skill。
§
外部服务:Tavily=搜索后端;高德 MCP 已配(静态地图参数用 location 非 center)。key 均在 API key 目录。
§
备份:私有仓库 Cyrus1993729/cyhermes_agent;恢复姿势见 skill hermes-backup。
§
小红书→skill xiaohongshu-analysis(xhslink 同法)。坑:站内搜索空+搜索引擎不收录,找帖只能靠分享链接。
§
Telegram 丢消息的已知问题与自动补发看门狗,见 skill hermes-telegram-delivery。
§
日报:5类 8:00 / 跨境 20:30(+20:40 重试)/ 黄金周报周一 12:30;生成投递分离 + mtime 幂等。
§
投资/技术方案须外部大模型 sign-off:GPT-5.6 主导,全自动 ≤3 轮。姿势见 skill hermes-china-providers。
§
API 故障:先排查+自动重试,fallback 是最后手段(按量付费)。兜底链结构见 skill hermes-china-providers。
§
金价认上海金;deepseek 卡顿→换 Go 套餐内其他模型,禁官方直连兜底(多费且照卡)。
§
↔妈妈(pc-a):9900 A2A,IP常变,v2脚本自动扫子网(禁写死);cron'妈妈机IP修复守候'。红线:改妈妈文件须带【用户已授权】,改本机配置须用户本人同意。
§
Codex/OpenAI 账号红线:全机仅 1 个账号,牛来+妈妈各自独立 OAuth(不互拷 auth.json);不跨机复制凭证、不切地域 IP、base_url 不指中转。
§
苏州人,爸妈住芜湖。
§
主模型+cron=deepseek-v4.1-flash/opencode-go;fallback 官方侧 ID=deepseek-flash(≠网关名)。核算见 skill model-subscription-evaluation。
§
健康域入口：用户说「健康助理」→ 调 hermes -p health chat -c "Bot Chat" -Q --query-file <文件>。数据在 ~/health/(profile.md=基线)。主 Hermes 不做健康判断，只负责写任务书+派活；拍照/份量/数据源见 skill health-nutrition-analysis。
§
桌面端:Hermes.exe 在 hermes-agent/apps/desktop/release/win-unpacked/(官方);Programs/hermes-desktop 是无关第三方软件,别搞混。其 Bot Mode 里「一个 bot = 一个 Hermes profile」。
§
要他确认的，必须是他凭常识就能判断的事（这是什么菜、大概多重）；超出生活常识的专业细节（食谱放了多少糖、理化参数等）他会当面拒绝。方案里的确认环节别落在他判断不了的事上。
§
有额度/成本的 API:他会要求先用免费接口做匹配筛选、确认后才查付费接口(薄荷 23 次额度事件他主动提出)。薄荷实测:公开接口免费给热蛋脂碳纤钠GI/GL+单位,只缺嘌呤和钙。
§
派验收任务时若被验收动作会落盘(写文件/记账/发消息),任务书须标「测试数据勿写真实档案」或给隔离路径。2026-10-20 踩过:验收假午餐写进真实 diet 档案,当天出现两顿午饭要用户自己发现。
§
本机 date 不认 TZ（恒报 UTC 却标 GMT），北京时间=+8h；state.db messages 用 timestamp(epoch) 无 created_at。
§
改/建 skill 保持 SKILL.md 精简(只留操作册)：历次踩坑/实测原文整段搬进 references/ 并建索引表；搬移后做零丢失校验(原文非空行 vs 新文件并集，缺失须为0)。
§
日程/待办/目标/复盘统一记 Dayflow（skill dayflow-personal-planner，Cloud 主库，写入后回读）；钉钉/邮件同步已由 Windows 计划任务每 15 分钟自动跑，勿另建同步 cron。