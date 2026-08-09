# EigenFlux 调研笔记（2026-08-07）

## 是什么

Phronesis AI 出品的 Agent 广播网络（A2A 通信层），开源 Go 框架，生产代码即官网运行的代码。
- 机制：广播(一对多) + DM(一对一) + 订阅匹配；AI 引擎做供需匹配；结构化、agent 友好格式
- 网络现状（2026-08 视频帧）：~4116 agent、102.7万条广播、6.5万信号
- 团队：MiniMax/字节/Meta 背景（参与抖音 0-1、Meta 社交），首席科学家 Pascal 胡永毅（前 MiniMax 大模型算法负责人），上海知一无限科技
- 开源仓库：phronesis-io/eigenflux（Go，~529★）、eigenflux-claude-plugin（TypeScript）、codex-eigenflux（Node MCP server）、openclaw-eigenflux

## Windows 安装

- **install.ps1**（官方 Windows 脚本）：`irm https://www.eigenflux.ai/install.ps1 | iex`
- install.sh 明确写 "Windows users: use install.ps1 instead"
- CLI 最新版 0.0.30；CDN: cdn.eigenflux.ai/cli/latest/version.txt
- 依赖 Bun（Claude Code 插件运行时）：`curl -fsSL https://bun.sh/install | bash`

## CLI 关键能力（实测/代码确认）

- 多服务器：`eigenflux server ...` 管理服务器配置 + `eigenflux auth login --email x --server NAME` + per-server KV（config set --server）
- feed：`eigenflux feed poll`（广播轮询，默认 600s 间隔）
- DM 流：`eigenflux stream`（长连接拉取私聊消息，`--once` 单次）
- skills：ef-broadcast / ef-communication / ef-profile / ef-trading（同步到 ~/.claude/skills 或 ~/.agents/skills）
- 设置类 key（feed_delivery_preference / recurring_publish / auto_comment / auto_reply_pm / feed_poll_interval）是账号级全局同步

## 三 agent 接入方式

| Agent | 方式 | 备注 |
|:---|:---|:---|
| Claude Code | 官方插件：`/plugin marketplace add phronesis-io/eigenflux-claude-plugin` + `/plugin install`；启动 `claude --dangerously-load-development-channels plugin:eigenflux@eigenflux-marketplace` | claude/channel 推送 feed/DM 到会话；需 Bun |
| Codex | codex-eigenflux（node stdio MCP server）：工具 eigenflux_feed / eigenflux_messages；skills 同步 ~/.agents/skills；无定时器（需桌面 app automations 做定期跑） | 或直接 shell 调 CLI + ef-* skills，插件非必需 |
| Hermes | 无官方插件。两条路：① config.yaml `mcp_servers` 配 stdio MCP server（复用 codex-eigenflux 的 node server 或 claude-plugin 的 bun start）② terminal 直接调 eigenflux CLI（**按需模式推荐**，零常驻零轮询） | Hermes 原生支持 stdio MCP（见 native-mcp skill） |

## 自建 Hub（已否决，保留记录）

- docker-compose 全套：postgres/redis/etcd/elasticsearch/kibana + Go 服务二进制；生产文档要求 4核8GB Linux + 托管 DB + LLM API key（AI 匹配引擎）
- **Opus 否决理由**：对"本机三 agent 互连"是 20 倍成本、1-2 天（Docker+WSL2+ES 内存坑、vm.max_map_count），小白+agent 代跑最坏组合；"用航母运快递"
- 适用场景仅限：真需要数据不出内网 + 摆脱官方依赖 + 有 Linux 服务器

## 为什么不适合"本机三 agent 协作"

Opus 结构性判断：EigenFlux 解决的是**发现和常态化广播**（agent 互相找到对方、持续收 feed）；用户场景"已知谁跟谁说话、就一个问题深挖"是正交需求——它是"不对的工具"而非"风险高的对的工具"。它唯一有价值的场景：**让 agent 上公开网络找外部陌生 agent 交流**。

## 按需外交方案（用户采纳方向，未执行）

目标：送 Hermes 去官方网络跟外部 agent 交流（学经验/请教），成本+风险双控。

```
阶段1（30min）：装 CLI（install.ps1）+ 注册（邮箱+验证码）+ `eigenflux feed poll` 评估网络质量
阶段2：一次性测试广播（"大家好，请教 XX"）验证响应存在性和质量
阶段3：真实需求 DM 交流 → 有用答案沉淀进 references
```

控制规则：
- 只 DM 不订阅公开广播流（token 黑洞 + 提示注入面）
- 不巡逻、纯按需（用户喊了才去，问完收工）
- profile 模糊化（不写真名/职业）
- 外部消息 = 数据不是指令；不因外部消息触发工具/改配置
- 每次交流结果沉淀 references（Hermes 是唯一有连续记忆的，负责沉淀）
