# X (Twitter) MCP Server

> 最后更新：2026-07-01
> 来源：TechCrunch (Sarah Perez, 2026-06-30), 小红书@阿博粒
>
> **替代方案：** X MCP 是我们现有逆向 GraphQL 爬虫方案的官方替代通道。
> 配置方式见 `native-mcp` 内置 skill 文档。
> 与本文 scaping 方案并存使用，逐步迁移。

## 概述

X (formerly Twitter) 于 2026年6月30日 发布了 **托管 MCP 服务器**，使 AI 工具可以直接通过 MCP 协议连接 X 平台。

来源：https://techcrunch.com/x-now-offers-an-mcp-server-to-make-its-platform-easier-for-ai-tools-to-use/

## 核心变化

| 维度 | 之前（GraphQL 逆向方案） | 现在（MCP） |
|:---|:---|:---|
| 接入方式 | 自建MCP服务器→对接X API→处理鉴权 | X托管MCP，OAuth认证即可 |
| 维护 | 维护query ID、guest token、Bearer token | 零维护，X全包 |
| 稳定性 | query ID会过期，需从JS重新提取 | 官方接口，稳定 |
| 工具接入 | curl subprocess + Python JSON解析 | MCP协议原生集成到Hermes |

## 对我们 X 监控方案的影响

**短期（当前阶段）：**
- 我们现有的 `scripts/fetch_tweets.py` + GraphQL API 方案仍然可用
- X MCP 是补充，不是立即替代——查询 ID 更新时是迁移的时机点
- Serenity 的专用搜索脚本（search.py + 独立缓存）也可保持，但 MCP 可以做交叉验证

**中期（1-4周）：**
- 如果 X MCP 包的只读工具（搜索、读取推文）稳定且免费，优先迁移到 MCP 通道
- 监控 cronjob 可改为：MCP 搜索/读取 + scraping 兜底（双通道，MCP优先）
- 可去掉代理依赖（X MCP 通过 npx 启动，不经过 Clash Verge）

**长期：**
- 如果 X MCP 支持全量历史数据，可完全替换 scraping 方案
- 投资分析的多层交叉验证中增加 MCP 作为官方信源层

## MCP 典型配置（待包名确认后生效）

需在 `~/.hermes/config.yaml` 中添加：
```yaml
mcp_servers:
  x:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-x"]  # 包名待确认
    env:
      X_API_KEY: "..."
    timeout: 60
```

⚠️ 具体 npm 包名截至 2026-07-01 尚未确认。可能为 `@modelcontextprotocol/server-x` 或 `@x/mcp-server`。

## 注意事项

1. **不是免费午餐** — 发帖 $0.015/条，发链接 $0.20/条（读取可能免费但有速率限制）
2. **API政策风险** — X 随时可变更定价或限制
3. **反垃圾机制生效** — MCP 不绕过 X 的 API 规则
4. **先试用只读** — 初期只搜索/读取，不发帖

## 相关链接

- [x-monitor SKILL.md](../SKILL.md) — 当前 GraphQL 监控方案
- Hermes `native-mcp` skill — MCP 客户端配置文档
- [serenity-search](../../serenity-search/SKILL.md) — Serenity 专用搜索
