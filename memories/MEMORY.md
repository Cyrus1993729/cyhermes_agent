PowerShell 经 bash 会吃 $ 和 -e 内双引号,写 .ps1/.mjs 跑。
§
网络:v2rayN 10808=主线路,已全局指向;Google需CAPTCHA,Bing可直连(curl --noproxy '*')。
§
长 prompt 用 --query-file 传文件(勿用 $(cat f))。delegate_task 无 per-call provider,子代理继承父模型。L1 审查见 skill l1-review。
§
路径:项目→D:\Workspace\;API key→Desktop/各类api key/;归档 YYYY-MM-DD_主题.md;复盘写文件不写 skill。
§
外部服务:Tavily=搜索后端;高德 MCP 已配(静态地图参数用 location 非 center)。key 均在 API key 目录。
§
备份仓库 Cyrus1993729/cyhermes_agent,见 skill hermes-backup。
§
小红书→skill xiaohongshu-analysis。坑:站内搜索空,只能靠分享链接。
§
TG丢消息/补发看门狗见 skill hermes-telegram-delivery。
§
日报:5类8:00/跨境20:30(+20:40重试)/黄金周报周一12:30;生成投递分离+mtime幂等。
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
健康域:「健康助理」→hermes -p health chat -c "Bot Chat" -Q --query-file。数据在~/health/(profile.md=基线)。主Hermes不做健康判断,只派活;见 skill health-nutrition-analysis。
§
桌面端:Hermes.exe 在 hermes-agent/apps/desktop/release/win-unpacked/(官方);Programs/hermes-desktop 是无关第三方软件,别搞混。其 Bot Mode 里「一个 bot = 一个 Hermes profile」。
§
要他确认的须是他凭常识能判断的(菜名/份量);专业细节(放多少糖/理化参数)他会拒绝,别落在他判断不了的事上。
§
有额度/成本的 API:他会要求先用免费接口做匹配筛选、确认后才查付费接口(薄荷 23 次额度事件他主动提出)。
§
派验收任务若会落盘(写文件/记账/发消息),任务书须标「测试数据勿写真实档案」或给隔离路径(踩过:假午餐写进真实 diet)。
§
date 不认 TZ(恒报 UTC),北京时间=+8h;state.db messages 用 timestamp(epoch)。
§
skill 保持精简:踩坑原文搬 references/ 建索引;搬后做零丢失校验。
§
日程/待办/目标/复盘统一记 Dayflow（skill dayflow-personal-planner，Cloud 主库，写入后回读）；钉钉/邮件同步已由 Windows 计划任务每 15 分钟自动跑，勿另建同步 cron。
§
微信端=日程秘书(只办日程/复盘,其他话题引到TG);TG=总管。日程类请求必须先加载 skill dayflow-personal-planner 用 client 写云端库,禁自建 cron 充当提醒;编号回复读 state/dayflow/evening_<日期>.json。
§
通知路由:日程/提醒→微信;运维、故障、备份、日报→Telegram。cron 运维类 deliver 用 telegram,禁用 origin(旧 origin 指向微信)。
§
家里常无脱脂奶(只有全脂纯牛奶/全脂无糖酸奶);给奶类建议按全脂算,别默认他能换脱脂。