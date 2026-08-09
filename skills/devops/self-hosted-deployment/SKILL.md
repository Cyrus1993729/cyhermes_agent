---
name: self-hosted-deployment
description: "Use when 用户要本地/自托管部署开源项目或选部署方式。侦察→环境检查→方案对比→契约+Opus审→确认。"
version: 1.0.0
category: devops
tags: [deployment, self-hosted, docker, uv, windows, china-network, opus-review]
---

# Self-Hosted Deployment — 本机自托管部署规划

## When to Use
- 用户说"帮我部署 X"、"如何在本机部署 X"、"哪种部署方式适合我"（含迁移场景：从 GitHub Actions / 云服务迁回本机）
- 交付物 = 部署契约/方案 + 用户确认，执行阶段另开任务
- 用户非技术背景但懂概念：方案必须表格化、通俗类比、明确"哪些要你配合、哪些不用"

## 本机环境常量（2026-08 实测）
- 笔记本 i5-6200U 双核 / 8GB 内存 / 256GB SSD，**24 小时开机**，Windows + WSL2(Ubuntu) 已装
- **无 Docker Desktop**；uv 0.11.x / git / Python 3.11 已装
- 常驻：Hermes Agent + Clash 代理 127.0.0.1:7897；TG API 被墙必须走代理，DeepSeek 等国内 API 直连
- 密钥库：`Desktop/各类api key/`（deepseek api key.txt、telegram bot token.txt、qwen3.7 api key.txt 等）
- 项目数据归 `D:\Workspace\Projects\`，日常脚本桌面

## Steps
1. **项目侦察**：web_extract GitHub 仓库页 + 官方文档站；README 很长时用 search_files 定位关键章节（快速开始/部署方式/系统要求/配置），再 read_file 精读。确认：部署方式（Docker/GA/本地uv/云）、配置体系、数据源/推送渠道、硬件要求。
2. **本机环境检查**（一条命令）：`docker --version; uv --version; git --version; python --version; wsl --status`。用事实说话，禁凭常识断言"应该装了什么"。
3. **方案对比矩阵**：按用户真正在乎的轴对比——人工干预频率（签到/额度限制）、配置修改便利度、硬件/内存代价、代理链路、数据备份、升级维护。表格 + 一句话类比（Docker=物业托管，本地=自己开店）。明确推荐 + 理由链。
4. **密钥盘点**：确认本地密钥文件是否覆盖所需（API key、bot token）；注意 bot 隔离——不同服务不要混用同一个 TG bot。
5. **契约 + Opus 红队审**（详见 references/opus-review-technique.md 与 claude-code skill）：
   - 契约按 sprint-contract 格式，验收标准写成"具体命令 + 可看到的结果"，禁"能启动/无报错"这类模糊措辞
   - Opus 审查用 print 模式：契约全文嵌入提示词（Opus 沙箱读不到本地文件）、`--tools ""` 禁工具、`--max-turns 8`
6. **用户确认**：5 步流程对部署类任务**非强制**——用户说"不一定要走5步流程"时允许简化（跳过 L1 审查/复盘）。Opus 审查结论必须逐条给出"有无解决方案"，让用户判断，不丢结论给他自己消化。

## 监控哲学：用户 = 最终心跳
- 用户 24h 开机 + 每天看推送 → "当天没收到推送"就是最可靠故障信号，他自己会发现并报告
- 看门狗/监控设计成：**自动拉起 + 只有拉起失败才通知用户**，不做每日心跳/主动打扰
- 符合用户"事件驱动、极端条件触发、平时静默"的一贯偏好

## Pitfalls（Opus 红队沉淀，本地部署通用）
1. **TG bot 无法主动给未对话用户发消息**（403 Forbidden: bot can't initiate conversation）→ 新建 bot 后用户必须先手机点一次 `/start`。必须写进"用户操作清单"，否则执行中段才发现要用户掏手机。
2. **密钥明文落 git 工作区**：GA Secrets 时代天然隔离；迁本地后 key 在项目文件夹里，非技术用户某天"备份一下"就可能 `git push` 泄露 → key 走 `.env` + 确认 .gitignore + **`git remote remove origin` 物理杜绝误推**。
3. **计划任务环境 ≠ 交互终端**：uv PATH、代理变量、工作目录、Clash 启动时序全部不同 → 手动验证与自启必须共用同一启动脚本，且**重启实测不可省**（"重启实测可选"会让自启缺陷合法通过验收）。
4. **静默失败是最坏形态**：重启/断电后整套系统悄悄停摆，现象只是"今天没推送"。缓解 = 系统级自启（任务计划程序，不依赖 Hermes 存活）。
5. **本地数据失去异地备份**：GA 时代数据 commit 回 GitHub = 免费异地备份；迁本地后是单盘孤本 → 每周自动打包 config/.env/db 到备份目录，并明确告知用户这一可靠性下降。
6. **output/ 持续膨胀**：按小时级频率跑一年会写满 256GB 单盘，且拖垮同机的 Hermes → 保留 N 天自动清理（如 90 天）+ 日志轮转。
7. **Docker Desktop 在 8GB 老笔记本上是负担**：WSL2 VM 常驻吃 2-4GB 内存，与 Hermes 共存吃力 → 老机器优先本地 uv（进程级轻量常驻），除非用户有 VPS。
8. **端口冲突**：部署前 `netstat -ano | findstr :8080` 探测（Hermes 系服务可能占用），占用则改端口。
9. **第三方数据 API 连通性必须实测**：免费公共 API（如 newsnow）在国内家宽 IP 下可能限流/不通；GA 是境外 IP 不代表本机通。验收改为连续多次抓取实测。
10. **改配置生效机制要写进手册**：常驻模式下改关键词/时间线几乎都要重启进程 → 交付"双击重启.bat" + 手册"改完怎么生效"章节。

## Handoff
- 契约存 `hermes/contracts/contract_<任务名>_<日期>.md` + 建 workflow 追踪文件（sprint-contract skill）
- 本 skill 只覆盖到"契约确认"；执行阶段（克隆/依赖/配置/自启/看门狗）完成后按 task-wrapup 收尾
- 执行阶段安全红线：**严禁 taskkill /F /IM python.exe（会杀死 Hermes 自身）**，杀进程用精确 PID

## See Also
- `sprint-contract` / `decision-gate` — 契约格式与 Opus 审闸门
- `claude-code` / `claude-code-workflow` — Opus 调用规范（代理红线、smoke test）
- `china-dev-proxy-setup` — 双网络 Python 项目代理配置
- `references/trendradar-deployment-2026-08.md` — 首个落地案例（TrendRadar 迁移契约 + Opus 全量发现）
