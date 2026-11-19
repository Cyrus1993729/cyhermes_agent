PowerShell经bash吃$和双引号,写.ps1/.mjs跑。
§
网络:v2rayN 10808 主线路;Google需CAPTCHA,Bing可直连(curl --noproxy '*')。
§
长 prompt 用 --query-file(勿 $(cat f))。delegate 子代理继承父模型。L1 见 skill l1-review。
§
归档 YYYY-MM-DD_主题.md;桌面只留快捷方式+5个文件夹(散文档归入文档/);复盘写文件不写 skill。
§
外部:Tavily=搜索;高德MCP已配(静态地图用location非center)。
§
备份仓库 Cyrus1993729/cyhermes_agent,见 skill hermes-backup。
§
小红书见skill xiaohongshu-analysis(搜索空靠分享链接);抓页面用移动Safari UA,桌面UA撞登录墙。
§
TG丢消息/补发看门狗见 skill hermes-telegram-delivery。
§
日报:5类8:00/跨境20:30(+20:40重试)/黄金周报周一12:30;生成投递分离+mtime幂等。
§
外部大模型 sign-off:点名模型(gpt-6.1-sol + effort=high),全自动≤3轮;见 skill codex-cli。
§
金价认上海金。API故障先重试,429换Go模型:gpt-6-luna→glm-5.3-flash→kimi-k3→qwen3.8-max;官方直连排最后;qwen3.7-max已下线(410)。
§
Codex/OpenAI 红线:全机 1 账号,牛来+妈妈各自独立 OAuth(不互拷 auth.json);不跨机复制凭证、不切 IP、base_url 不指中转。
§
苏州人,爸妈住芜湖。
§
主模型+cron=deepseek-v4.1-flash/opencode-go;fallback 官方 ID=deepseek-flash(≠网关名)。Go 档无 Opus(仅 Haiku 5.5),重活要 Opus 5.5 须另开口子(OpenDesign Pro/Kilo/Claude Max)。核算见 skill model-subscription-evaluation。
§
健康域:一律派给 health bot,见 skill health-assistant-delegation(命令/任务书八段/两段式/校验器坑);主Hermes禁识图(走recognize.py);菜名克数以他口述为准(识图冲突作废);同会话勿并发派活。
§
桌面端 Hermes.exe=release/win-unpacked(官方);Programs/hermes-desktop 是第三方。一 bot=一 profile。
§
要他确认的须是他凭常识能判断的(菜名/份量);专业细节(放多少糖/理化参数)他会拒绝,别落在他判断不了的事上。
§
有成本API先免费筛再查付费。
§
记账:核算稿→他明确说「写/存档」才入档;说「记一下」=直接落盘;模糊量先出稿。回执/记账一律不建md不发MEDIA。
§
SKILL.md≥100K 时 patch 拒改,改动只能写 references/。
§
Dayflow-Work-Sync每分钟采集钉钉/邮件,只抓不落日程;否决邮件转日程自动化,勿建cron。
§
微信端=日程秘书(只办日程/复盘,其他话题引到TG);TG=总管。日程类请求必须先加载 skill dayflow-personal-planner 用 client 写云端库,禁自建 cron 充当提醒;编号回复读 state/dayflow/evening_<日期>.json。
§
通知路由:日程/提醒→微信;运维/故障/备份/日报→Telegram。cron运维类deliver=telegram,禁origin(旧指微信)。
§
家里奶:全脂纯牛奶/无糖酸奶(品牌不固定,按他发的标签算),无蛋白粉——一律按全脂算勿建议脱脂。
§
「打算吃/要吃」≠已吃:未发生的餐不进统计。
§
本机 cron 18 个:14 no_agent/4 agent,评估必读 jobs.json。
§
他报份量常用「口/个/碗」模糊单位,须换算成克给他核;「没怎么吃」通常=没吃,先问零或非零;给区间他自己指定取哪头,别取中值
§
Dayflow client items=JSON数组+行诊断JSONL,raw_decode读(loads报Extra data)。
§
TG汇报:接活先应答(收到+怎么拆)再动工具,不能等第一个产出;自己动手每步报进展,子bot那步可一次等结果(skill work-progress-reporting)。
§
gateway 无看护(Windows无服务/计划任务):看门狗 exit 75 后不自恢复,只能重启;取证见 skill daemon-outage-forensics