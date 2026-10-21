# X (Twitter) MCP Server — 官方托管方案

> 2026年6月30日 X 发布官方托管 MCP 服务器，Agent 可通过 OAuth 2.0 直接访问 X API。
> **端点**: `https://api.x.com/mcp`
> **桥接工具**: `xurl` (`@xdevplatform/xurl`)
> **来源**: TechCrunch (Sarah Perez), 官方文档, a2a-mcp.org

## 架构

```
Hermes Agent → xurl mcp (本地 stdio) → https://api.x.com/mcp (X托管MCP)
                    │
                    ├─ OAuth 2.0 PKCE 认证
                    ├─ Token 缓存 (~/.xurl) + 自动刷新
                    └─ Bearer token 注入
```

xurl 是 X API 官方 CLI（Go 编写），`xurl mcp` 子命令作为 stdio 桥接，读取 JSON-RPC → 转发到托管 MCP 端点 → 写回响应。

## 前置条件

- Node.js（Hermes 环境通常已安装）
- **X Developer Platform 账号** + OAuth 2.0 应用
- CLIENT_ID + CLIENT_SECRET（在 X Developer Portal 创建 App 后获得）
- 回调地址 `http://localhost:8080/callback` 必须在 X App 设置中注册
- App 必须加入 **Pay-per-use** 套餐并切换到 **Production** 环境（否则返回 `client-not-enrolled`）

## 安装 xurl

```bash
npm install -g @xdevplatform/xurl   # 全局安装
xurl mcp --help                      # 验证
```

## Hermes 配置

在 `~/.hermes/config.yaml` 的 `mcp_servers` 中添加：

```yaml
mcp_servers:
  x:
    command: "xurl"
    args: ["mcp", "https://api.x.com/mcp"]
    env:
      CLIENT_ID: "你的_CLIENT_ID"
      CLIENT_SECRET: "你的_CLIENT_SECRET"
    connect_timeout: 300
    timeout: 120
```

首次运行 xurl 会自动打开浏览器进行 OAuth 2.0 登录，完成后 token 缓存到 `~/.xurl`。

**无头服务器**: 先用有浏览器的机器执行 `xurl auth oauth2 --headless`，再把 `~/.xurl` 拷贝过去。

## 提供的能力

注册后 Hermes 自动获得 `mcp_x_*` 工具：

| 能力 | 说明 |
|:---|:---|
| 推文搜索 | 全文搜索 X 帖子 (full-archive) |
| 用户查找 | 按用户名/ID 查用户信息 |
| 时间线 | 获取用户时间线 |
| 趋势 | 获取当前趋势 |
| 书签 | 管理书签和书签文件夹 |
| Mentions | 查看提及 |
| News | 获取新闻 |
| Articles | X Articles 相关操作 |

## 定价

读取/搜索有免费层（速率限制），写入操作收费：
- 发帖：$0.015/条
- 发链接：$0.20/条

## 与旧 scraping 方案对比

| 方案 | 可靠性 | 维护成本 | Token 管理 | 适用场景 |
|:---|:---:|:---:|:---:|:---|
| X MCP（官方托管） | ★★★★★ | 低 | 自动 OAuth | 日常监控、搜索、研究 |
| Guest Token scraping | ★★ | 中 | 手动提取 | 快速 97 条快照 |
| twscrape（账号池） | ★★★★ | 高 | IMAP 自动 | 历史数据全量拉取 |
| x-monitor（GraphQL） | ★★★ | 高 | Cookie 手动 | 特定博主深度监控 |

**推荐策略**: 优先使用 X MCP，scraping 方案保留为备用/补充。

## 参考资料

- 官方 X MCP 文档: https://docs.x.com/tools/mcp
- xurl GitHub: https://github.com/xdevplatform/xurl
- TechCrunch (2026.6.30): "X now offers an MCP server to make its platform easier for AI tools to use"
- a2a-mcp: https://a2a-mcp.org/entry/x-mcp-zh
