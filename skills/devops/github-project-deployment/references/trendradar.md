# TrendRadar 侦察存档（2026-08-06 会话）

来源：https://github.com/sansan0/TrendRadar（README v6.10.0，61.2k star，GPL-3.0，Python）
定位：AI 舆情/热点监控工具——定时抓多平台热榜 + RSS → 关键词/AI 兴趣筛选 → AI 翻译 + 分析 → 推送多渠道 + Web 报告 + MCP 接口。

## 部署三路线
| 路线 | 特点 | 备注 |
|---|---|---|
| A. Docker（官方推荐） | 稳定、数据本地、内置 cron | 镜像 wantcat/trendradar（推送）+ wantcat/trendradar-mcp（MCP AI，可选） |
| B. GitHub Actions | 免服务器，需云存储（CF R2） | 定期签到续期，非首选 |
| C. 本地 uv | 无需 Docker，uv 自动管 Python | 本机 uv/git/python 全齐，最快跑通 |

## 配置布局
- `config/config.yaml` — 核心功能（报告模式/推送/存储/AI 开关/平台启用）；`config/frequency_words.txt` — 关键词（分组/正则/别名）；`config/timeline.yaml` — 调度；`config/ai_interests.txt` — AI 自然语言兴趣筛选；`config/ai_analysis_prompt.txt` — AI 分析提示词
- `docker/.env` — 敏感信息 + 环境变量（**环境变量 > config.yaml** 覆盖机制）
- 关键 env：`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`、`AI_API_KEY`/`AI_MODEL`/`AI_API_BASE`、`WEBSERVER_PORT`（默认8080）、`CRON_SCHEDULE`（默认 `*/30 * * * *`）、`RUN_MODE=cron`、`IMMEDIATE_RUN=true`、`S3_*`（远程存储 5 参数）
- AI 走 LiteLLM：模型格式 `provider/model`（DeepSeek 默认：`deepseek/deepseek-chat`），支持 OpenAI/Gemini/Anthropic + 任意 OpenAI 兼容接口；`AI_API_BASE` 可指自定义端点
- Web 报告：`http://localhost:8080`（docker compose 只绑 127.0.0.1）；历史报告 output/html/YYYY-MM-DD/
- MCP 服务：HTTP `http://127.0.0.1:3333/mcp`；STDIO `uv run python -m mcp_server.server`；可接入 Hermes native MCP 客户端

## 本机环境（2026-08）
docker ❌ 未装（WSL2+Ubuntu ✅，装 Docker Desktop 即可）；uv 0.11.16 ✅；git 2.54 ✅；python 3.11.15 ✅

## 中国网络要点
- DeepSeek API 国内直连，无需代理
- TG bot API 被墙：TrendRadar 推送 TG 必须设 `HTTP_PROXY`/`HTTPS_PROXY` = 127.0.0.1:7897（uv 直跑可在系统 env 或启动脚本；Docker 在 compose env 加）
- 数据源走 newsnow 免费 API（国内平台热榜），**连通性部署时实测**，不通考虑自建 newsnow 源（config 支持 `api_url` 自定义）
- 给 TrendRadar 建**独立 TG bot**（BotFather），chat id 用 8938729624；别与 Hermes 共用 bot

## 用户契合点（讨论结论）
- 关键词候选：美股/纳指/黄金/联储/AI（用户定投纳指 + 黄金积存金）
- 与现有 gold-investment-analysis / x-monitor 互补：TrendRadar 管多平台热点聚合 + AI 摘要推送
- 建议节奏：先方案 C（本地 uv）半小时跑通看效果 → 确认长期用再上 Docker
- 推送频率控制：newsnow 免费 API 勿高频抓取（作者提示）

## 下一步（等用户拍板）
- 方案 C：clone → `uv sync`（setup-windows.bat 全自动）→ 改 config/config.yaml + frequency_words.txt → 设代理 env → 跑 → 验证 output/ 有数据 + TG 收到推送
- 方案 A：装 Docker Desktop → clone → 改 docker/.env → `docker compose up -d`
