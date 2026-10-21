# Hermes 官方接入面全量清点（2026-10-08 源码实测）

来源：`~/AppData/Local/hermes/hermes-agent/` 源码树 + `config.yaml` + `.env`。
适配器随版本增删——引用前先按 SKILL.md 的三条 `ls` 命令复查，不要直接照抄本文件当现状。

## 1. 核心平台适配器 — `gateway/platforms/`

api_server · bluebubbles（Apple iMessage 桥）· msgraph_webhook（微软 365/Outlook 官方 webhook）·
qqbot（腾讯官方 QQ 机器人开放平台）· signal · webhook（通用入站）· weixin（腾讯 iLink 官方个人号）·
whatsapp_cloud · yuanbao（腾讯元宝）

辅助模块（非平台）：`base.py`、`media_cache.py`、`helpers.py`、`signal_format.py`、
`signal_rate_limit.py`、`webhook_filters.py`、`_http_client_limits.py`，另有
`api_server_room_*.py` / `api_server_runs.py`（API server 房间与幂等）。
扩展指引：`ADDING_A_PLATFORM.md`。

## 2. 插件式平台适配器 — `plugins/platforms/`

a2a · buzz · dingtalk（钉钉）· discord · email · feishu（飞书，另有 `hermes-feishu` 相关配置 key）·
google_chat · homeassistant · irc · line · matrix · mattermost · ntfy · photon · raft · simplex ·
slack · sms · teams（Microsoft Teams）· telegram · wecom（企业微信）· whatsapp

## 3. 官方 MCP 目录 — `optional-mcps/`（65 条，每条一个 manifest.yaml）

airtable algolia alltrails amplitude asana atlassian attio aws-knowledge betterstack buildkite
calendly canva circleci clickup close cloudflare cloudinary comfy-cloud context7 craft datadog
deepwiki dropbox figma fireflies gamma gitlab globalping grafana hugging_face indeed intercom
kiwi klaviyo linear microsoft-learn miro mixpanel monday motherduck n8n neon netlify notion
paypal plaid postman prisma-postgres railway robinhood semgrep sentry square strava stripe
supabase todoist trivago twelve-data twilio-docs unreal-engine vercel webflow wolfram wordpress-com

**注意：目录内没有任何中国厂商条目**——高德、X 都是手工加进 `mcp_servers` 的，不在目录里。
`hermes_cli/mcp_catalog.py` 负责加载这些 manifest（含 auth/transport/tools 规格）。
Hermes 原生 MCP 客户端通吃：任何官方 MCP server 手填 `mcp_servers` 即可接入，不限于目录。

## 4. 内置插件（非平台类）— `plugins/`

browser · context_engine · cron_providers · dashboard_auth · disk-cleanup · google_meet ·
hermes-achievements · image_gen · kanban · memory · model-providers · observability · platforms ·
security-guidance · spotify · teams_pipeline · video_gen · web

## 5. 本机实际已启用（2026-10-08）

- **微信**（腾讯 iLink 官方个人号）— 凭证在 `.env`（`WEIXIN_*`），config.yaml 里搜不到
- **Telegram**（官方 Bot API，走代理）— 凭证在 `.env`
- **api_server**（本地 127.0.0.1:8642）+ **a2a**（妈妈机，端口 9900）
- **MCP：x.com 官方 MCP**（43 个工具，经 xurl）+ **高德地图官方 MCP**（12 个工具：路线/POI/天气/地理编码）

已知「看着像启用其实没有」：`spotify`、`yuanbao` 出现在 toolset 注册表里，但 config 无对应配置块。

## 6. 中国国内 —— 官方渠道清单（回答重点）

已启用：微信个人号（腾讯 iLink）、高德地图 MCP（阿里官方）、Telegram 走代理。

原生适配器已在代码里、只差凭证（官方开放平台，非第三方框架）：

- **腾讯元宝** `yuanbao` — 腾讯系官方入口
- **QQ 机器人** `qqbot` — 腾讯官方开放平台
- **飞书** `feishu` — 字节官方，WebSocket 长连接国内直连；2026-09 已调研，能力档位与 TG 对齐
  （见 SKILL.md「中国大陆免代理消息平台」小节）
- **钉钉** `dingtalk` — 阿里官方 Stream 模式
- **企业微信** `wecom` — 腾讯官方
- **邮箱** `email` — 内置 adapter，QQ 邮箱/163 官方 IMAP/SMTP，零成本

可手动配的国内官方 MCP（不在目录内，填 key 即用）：阿里云、腾讯云、百度地图、飞书多维表格、
支付宝、通义、DeepSeek 等。

## 7. 欧美生态 ↔ 用户羡慕的 Gmail 类场景映射

| 用户看到的能力 | Hermes 侧的官方等价物 |
|:---|:---|
| Gmail 邮件 | `email` 插件 adapter（IMAP 通吃 Gmail/Outlook/QQ 邮箱） |
| 微软 365 / Outlook / 日历 | `msgraph_webhook` 核心 adapter（官方 Graph webhook） |
| Google Chat | `google_chat` 插件 adapter |
| iMessage | `bluebubbles` 核心 adapter |
| 日历会议 | `google_meet` 内置插件 |
| 音乐 | `spotify` 内置插件（本机未配凭证） |

其余：Discord / Slack / Teams / WhatsApp / Signal / Matrix / Mattermost / LINE / IRC / Simplex /
Home Assistant 均有适配器。

## 8. 三段式结论模板（可直接复用的回答骨架）

1. 三层全貌：消息平台适配器 / MCP 应用生态（目录 65 条 + 任意官方 MCP）/ 内置插件。
2. 每层三档：已启用 → 原生适配器只差凭证 → 需手动配 key。国内优先。
3. 诚实差距：适配器框架 ≠ 一键 SaaS 连接，多数要自配凭证；但国产生态（微信个人号 / 高德 /
   飞书钉钉）是长板，北美产品接不了。
