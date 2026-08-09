# EigenFlux 调研事实（2026-08-07）

> 来源：GitHub（phronesis-io/eigenflux 及插件仓库 README/源码）+ 官网 eigenflux.ai + 即刻/36氪报道，交叉验证。**均为调研结论，尚未在本机实测**。用户从小红书视频帖发现此产品。

## 产品定位

- Agent-to-Agent 广播网络（"The Communication Layer for AI Agents"），解决「多个 agent 怎么联网」而非「单个 agent 怎么更强」
- 核心机制：广播（一对多）+ 私聊（一对一）+ 订阅匹配——agent 用自然语言声明兴趣，AI 引擎（需要 LLM API key）做供需匹配，只推送相关信号
- 广播格式结构化、agent 友好、高信噪比；官网宣称广播比搜索省 94% token（团队自测，未独立验证）
- 出品方：Phronesis AI（上海知一无限），团队来自 MiniMax/字节/Meta；首席科学家 Pascal（胡永毅）前 MiniMax 大模型算法负责人
- 开源：phronesis-io/eigenflux（Go，529★）；生产代码库即官网所跑版本

## 网络现状（2026-08-07 视频帧截图）

- 4,116 个 Agent、102.7 万条广播、6.5 万个信号；24 小时冷启动 1000+ agent（开源公测初期，团队自述）
- 界面：导航（今天/搜索/广播/关系/消息/设置）、内容分类（供给/需求/资讯/预警）、七日影响力排行（Codex Agent 曾上榜——跨平台实锤）
- 官网有全球广播直播页（社会实验）

## 接入方式（三种 agent）

| Host | 方式 | 依赖 |
|:---|:---|:---|
| Claude Code | 官方插件（marketplace 安装，MCP channel 推送 feed/DM 进会话；ef-broadcast/ef-communication/ef-profile/ef-trading 四个 skills） | Bun + eigenflux CLI |
| Codex | codex-eigenflux 插件（node stdio MCP server，工具 eigenflux_feed/eigenflux_messages）；或直接 shell 调 CLI + skills | Node + CLI |
| Hermes | 无官方插件；可配 stdio MCP client（复用 codex-eigenflux 的 server，config.yaml `mcp_servers`）或 terminal 调 CLI + cron 轮询 | Node 或仅 CLI |

- CLI 安装：Windows 用 `irm https://www.eigenflux.ai/install.ps1 | iex`（install.sh 明确不支持 Windows）；CLI 最新 0.0.30
- CLI 原生多服务器：`eigenflux server add` + `eigenflux auth login --server X` → 可指定连自建 hub
- 接入提示词（官网）：`$Read https://eigenflux.ai and help me join EigenFlux` 发给 agent 自动安装

## 自建 Hub 门槛（❌ 本机场景不推荐）

- docker-compose 全套：postgres + redis + etcd + elasticsearch + kibana + Go 服务二进制
- 生产文档推荐 Linux 4 核 8GB 100GB SSD + 托管 Postgres/Redis/ES + LLM API key
- 实际耗时 1-2 天（非半天），且依赖 Docker Desktop（WSL2/内存/端口冲突排错），对技术小白 + agent 代跑是最坏组合

## 风险（Opus 评审确认）

1. **提示注入**：公开 feed 内容进入 Claude Code 上下文（有文件读写/命令执行权限）→ 本机权限暴露。只用 DM、不订阅公开广播
2. **回复风暴**：agent 自动回复循环烧 token → 回复深度上限 ≤3 跳、TTL、不回自己线程
3. **身份隔离**：一台机器能否开三个独立身份未验证（生死线检查，10 分钟）
4. 轮询成本：10 分钟 × 3 agent × 全天 = 每天 400+ 次 LLM 唤醒（多数空转）
5. 供应商风险：Research Preview + 0.0.30，API/服务随时可能变；`irm | iex` 远程脚本先下载审阅再执行
6. 运行时污染：Bun + Node + Docker Desktop 三套环境改动，先记录便于回滚

## Opus 修订路线（等待用户拍板，2026-08-07 状态）

```
① 工具链 30min → ② 身份隔离检查 10min（失败即停）
→ ③ 本地 broker 对照组 30min（大概率已满足需求）
→ ④ EigenFlux 官方 hub 2-4h（可选：评估产品本身，只用私聊）
→ ⑤ 自建 hub：删除
```

关键决策问题（问用户）：要「结果」（agent 协作）→ 本地 broker；要「产品体验」（EigenFlux 跨用户发现/AI 匹配）→ 官方 hub。两者是不同的任务。
