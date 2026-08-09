---
name: github-project-deployment
description: Use when 用户发 GitHub 链接要求了解项目/规划部署。评估→方案→确认→部署→验证全流程。
---

# GitHub 项目评估与本地部署

用户常发 GitHub 仓库链接要求先了解再讨论部署（如 TrendRadar）。此 skill 覆盖「评估 → 出方案 → 确认 → 部署 → 验证」完整链路。用户是技术小白但懂概念，重视推导过程与对比论证，**未拍板前绝不自行 clone/安装**（行为红线：方案→确认→执行）。

## 评估阶段（部署前，用户说"了解/讨论"时）

1. **抓仓库页**：`web_extract` GitHub 主页。README 超长时输出会被截断（head+tail），**完整文本已存到 `C:\Users\<user>\AppData\Local\hermes\cache\web\<repo>-<hash>.md`**，输出尾部会给出路径。
2. **缓存文件内定位关键章节**：`search_files` 在缓存 md 里查 section 锚点。
   - 用**简单单词查询**：`快速开始`、`Docker`、`uv`、`部署`、`安装`（区分大小写！）
   - 别用复杂正则（行首锚定 `^#{2,4}` + 中文交替）——转换后的 markdown 不匹配，0 命中白费一轮
   - 命中后 `read_file` 带 offset 翻页精读
3. **关键配置/脚本抓 raw**：`https://raw.githubusercontent.com/<owner>/<repo>/master/<path>`（分支可能是 master 或 main）。README 转换后**代码块命令常被压扁吞掉**，setup 脚本、docker-compose.yml、pyproject.toml 必须抓 raw 才准确。
4. **并行查本机环境**（一条 terminal 串行即可）：
   ```
   docker --version; docker compose version; uv --version; git --version; python --version; wsl --status
   ```
   本机基线（2026-08）：docker ❌ 未装，uv ✅ 0.11.16，git ✅ 2.54，python ✅ 3.11.15，WSL2+Ubuntu ✅。
5. **输出结构**：项目一句话定位 + 核心功能列表 + 本机环境现状表 + 部署路线对比表 + 需准备的凭证/配置 + 推荐路线 + 网络提醒（中国网络项目：TG 等墙外 API 要代理，国内 API 直连）。
6. **闸门**：问用户走哪条路，等拍板。拍板后才出部署契约（参考 sprint-contract：步骤/配置文件/验证点）。

## 部署执行阶段（用户确认后）

- 先出契约：具体步骤、要改的文件、每个验证点，用户确认才动手。
- 部署后验证清单（通用）：
  - 服务健康：端口通了（curl health / 页面 200）
  - 首次数据抓取成功（output/ 或 data/ 目录有新数据）
  - 推送/通知真实送达一条（test 消息，别只看日志"发送成功"）
  - 日志无报错；定时任务（cron）确认生效
  - 重启后能自愈（常驻进程/容器 restart 策略）
- 中国网络项目三件套：① 墙外 API（TG bot、Google 等）设 `HTTP_PROXY`/`HTTPS_PROXY`（本机代理 127.0.0.1:7897）；② 国内 API（DeepSeek 等）直连不动；③ 免费公共数据 API（如 newsnow）控制调用频率，勿竭泽而渔。

## Pitfalls

- `search_files` 大小写敏感：查 `Docker` 命中、查 `docker` 0 命中。
- 转换后 markdown 的代码块内容常被压成一行或整段吞掉——**一切命令以 raw 文件为准**。
- 给新服务建独立推送 bot，别跟主 agent（Hermes）共用一个 TG bot，消息会混流。
- Windows 本地部署（uv 直跑）：进程要自己管（计划任务/后台），关机即停；**长期跑优先 Docker**（内置 cron + 自动重启 + 一条命令升级）。
- Docker 路线要提醒装机成本（Docker Desktop 几个 GB，需 WSL2 后端；本机 WSL2 已就绪）。

## 支持文件

- `references/trendradar.md` — TrendRadar 侦察存档：部署三路线/镜像/配置布局/中国网络要点/本机环境，下次直接部署时复用，免重新抓取。
