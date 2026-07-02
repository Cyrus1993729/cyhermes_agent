# MoA 模型计费研究记录

## OpenAI Codex — 走 ChatGPT 订阅配额 ✅

**来源：** OpenAI Help Center, Article #11369540 "Using Codex with your ChatGPT plan"

**原文关键句：**
> "Codex is included across Free, Go, Plus, Pro, Business, Edu, and Enterprise plans. Usage limits and credit options vary by plan."
> "Codex is included in eligible ChatGPT plans, including Free. Usage limits vary by plan."

**Hermes 实现：**
- Provider: `openai-codex`
- 端点: `chatgpt.com/backend-api/codex`（非 api.openai.com）
- 认证: OAuth（浏览器登录 ChatGPT 账号）

**多设备风险：** 全网搜索（Bing/Startpage/DuckDuckGo/Reddit/v2ex/知乎/GitHub）零封号案例。帮助中心无任何多设备限制说明。

---

## Anthropic API — 不走在Claude Pro 订阅配额 ❌

**来源：** Anthropic Help Center, Article #7996885 "What is Claude Pro"

**原文关键句：**
> "This article is about our **commercial products** such as Claude for Work and the **Anthropic API**. For our **consumer products** such as Claude Free, Pro, Max and when accounts from those plans use Claude Code, see…"

**解读：** Anthropic 将 API 归类为「商业产品」、Claude Pro 为「消费者产品」，两类计费体系分开。

**Hermes 实现：**
- Provider: `anthropic`
- 端点: `api.anthropic.com`（标准 API 端点）
- 认证: API Key 或 Claude Code OAuth Token
- 支持 `CLAUDE_CODE_OAUTH_TOKEN` 环境变量，但请求发到 api.anthropic.com → 大概率走 API 计费

**与 OpenAI 的对比：**
| | OpenAI Codex | Anthropic Claude Code |
|:---|:---|:---|
| 订阅内产品 | Codex CLI/IDE/Web | Claude Code CLI |
| 订阅后端 | chatgpt.com/backend-api/codex | （非 api.anthropic.com） |
| API 端点 | api.openai.com | api.anthropic.com |
| Hermes 是否有订阅后端 Provider | ✅ openai-codex | ❌ 无，anthropic provider 都走 api.anthropic.com |

---

## 搜索方法记录

当 `web_search` 工具不可用时，有效的方法：
1. **Bing 国际版直连** — 最稳定，但中文查询效果差
2. **Startpage + 代理** — 英文搜索可用
3. **curl 直接抓取官方文档页面** — 对 JS 渲染页面需 grep 提取 `<p>` 标签内容
4. **Reddit JSON API** — 常被限流，不可靠
5. **GitHub API** — 搜代码/讨论比搜文档更有效

无效的方法：
- Google 搜索（CAPTCHA 阻断）
- DuckDuckGo HTML 版（结果不稳定）
- 中文社区直接搜索（Bing 中文结果质量差）
