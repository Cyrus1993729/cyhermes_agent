---
name: x-twitter-data-extraction
description: >-
  【抓取 X/Twitter 数据】唯一入口。四档方案：
  Guest API（97条快照）→ Auth Token（3200条+分页）→ Playwright（无认证全量）→ twscrape（自动登录池）。
  覆盖搜索、监控、token管理、代理穿透、X MCP 官方方案。
  | 跟 x-monitor 的区别：本 skill 是「怎么抓数据」，
  x-monitor 是「怎么定时监控+推送到 Telegram」；
  跟 serenity-search 的区别：本 skill 是通用抓取，
  serenity-search 是 Serenity 专用的搜索+缓存工具。
triggers:
  - "抓取 X/Twitter 推文"
  - "监控 X 用户"
  - "爬 X 推文历史"
  - "搜索 X 关键词"
  - "获取 twitter 推文"
  - "from:aleabitoreddit"
  - "serenity 推文"
  - "X API guest token"
  - "GraphQL query ID"
  - "搜他/她的X推文"
  - "监控这个X账号"
  - "抓取Twitter时间线"
  - "search tweets from @user"
  - "Serenity / aleabitoreddit"
  - "from:username keyword 搜索"
  - "auth_token cookie X API"
  - "nitter 不能用了怎么爬 X"
---

# X/Twitter 数据抓取 — 完整方案

> 2026-07-01：X 已发布官方 MCP 服务器（OAuth 认证，搜索/用户/趋势/书签）。
> 见 [X MCP 配置指南](references/x-mcp-server.md)。
> MCP 可用时优先用 MCP；本 skill 中的 GraphQL/Playwright 方案作为备用/补充。

---

## 方案速查：四条路，按需选

| 方案 | 能拿多少 | 需要什么 | 适合场景 | 复杂度 |
|------|---------|---------|---------|--------|
| **① Guest API** | ~97 条热门 | 无（Bearer 从 JS 提取） | 快速头像扫描 | ⭐ |
| **② Auth Token（GraphQL）** | ~3200 条+分页 | bot 账号的 auth_token+ct0 | 全量历史、搜索 | ⭐⭐ |
| **③ Playwright 浏览器** | 全量、无上限 | Chromium+Playwright | 无需账号的全量抓取 | ⭐⭐⭐ |
| **④ twscrape（自动池）** | 3200+、多账号轮换 | 1-3 个 bot 账号 | 高频采集 | ⭐⭐⭐⭐ |
| **⑤ X MCP（官方）** | 搜索/用户/趋势 | X OAuth 2.0 令牌 | 搜索+读帖（2026-07 新增） | ⭐ |

---

## 方案 ①：Guest API — 快速快照（~97条，无认证）

### 适合场景
只是想快速看一眼用户的热门推文，不需要历史全量。

### 步骤

**Step 1：提取 Bearer Token**
```bash
# 从 x.com HTML 找 main JS URL
curl -sL --proxy http://127.0.0.1:7897 "https://x.com" | \
  grep -oP 'src="https://abs\.twimg\.com/responsive-web/client-web/main\.[^"]+\.js"'
# 下载 JS 提取 token
curl -sL --proxy http://127.0.0.1:7897 "<上面的URL>" | \
  grep -oP 'AAAAA[A-Za-z0-9%\-_]{50,}'
```

当前 Bearer Token（固定，极少变）：
```
AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA
```

**Step 2：激活 Guest Token**
```bash
curl -sL -X POST "https://api.x.com/1.1/guest/activate.json" \
  -H "Authorization: Bearer AAAAAA...TnA" \
  --proxy http://127.0.0.1:7897
# 返回: {"guest_token":"2069..."}
```

**Step 3：获取 user_id**
```bash
curl -sL --proxy http://127.0.0.1:7897 "https://api.fxtwitter.com/<screen_name>" | \
  python -c "import sys,json; print(json.load(sys.stdin)['user']['id'])"
```

**Step 4：拉推文（GraphQL UserTweets）**

当前 Query ID：`hr4gzZONlq23okjU8fIe_A`

```python
import subprocess, json, urllib.parse

USER_ID = "1940360837547565056"
QUERY_ID = "hr4gzZONlq23okjU8fIe_A"

vars_d = {"userId": USER_ID, "count": 100, "includePromotedContent": False,
          "withVoice": True, "withV2Timeline": True}
feats = {"responsive_web_graphql_exclude_directive_enabled": True,
         "view_counts_everywhere_api_enabled": True,
         "longform_notetweets_consumption_enabled": True}

url = (f"https://x.com/i/api/graphql/{QUERY_ID}/UserTweets"
       f"?variables={urllib.parse.quote(json.dumps(vars_d))}"
       f"&features={urllib.parse.quote(json.dumps(feats))}")

cmd = ["curl", "-sL", "--connect-timeout", "15",
       "--proxy", "http://127.0.0.1:7897",
       "-H", f"Authorization: Bearer AAAAAA...TnA",
       "-H", f"x-guest-token: {guest_token}",
       url]
result = subprocess.run(cmd, capture_output=True, text=True)
resp = json.loads(result.stdout)
```

### Guest API 限制
- ❌ 仅 ~97 条，按互动量（热门）排序，非时间序
- ❌ 无分页 cursor → 无法翻页
- ❌ UserTweetsAndReplies 和 SearchTimeline 对 Guest 返回空

---

## 方案 ②：Auth Token（GraphQL）— 全量历史 + 分页

### 适合场景
需要完整历史推文、支持分页回溯、支持搜索（本地过滤）

### 获取认证凭证

需要 bot 账号的 **auth_token** 和 **ct0**：

**从 Chrome 提取**（中文浏览器路径）：
1. 用 bot 账号登录 x.com
2. F12 → 应用（Application）→ 存储（Storage）→ Cookies → `https://x.com`
3. 复制 `auth_token`（32 位十六进制）和 `ct0`（长十六进制字符串）
4. 保存到本地配置文件（不要明文发送到聊天）

详见 `references/cookie-extraction.md`

### Auth 请求头
```python
headers = {
    "Authorization": f"Bearer {BEARER}",
    "Cookie": f"auth_token={AUTH_TOKEN}; ct0={CT0_TOKEN}",
    "x-csrf-token": CT0_TOKEN,  # 必须和 cookie 里的 ct0 一致
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

### 分页翻页
Auth 模式下 `UserTweets` 返回 `TimelineTimelineCursor`（cursorType: "Bottom"），每页约 17-19 条：

```python
vars_d = {"userId": USER_ID, "count": 100, "includePromotedContent": False,
          "withVoice": True, "withV2Timeline": True}
if cursor:
    vars_d["cursor"] = cursor  # 从上一页 Bottom cursor 获取
```

一直翻页直到不再返回 Bottom cursor。

### 搜索（本地过滤）
SearchTimeline 端点即使 auth 也返回空 → 拉全量 timeline 后在本地按关键词/日期过滤。

**X 搜索语法**（用于本地过滤）：
```
from:aleabitoreddit NBIS
from:username keyword since:2025-09-01 until:2025-10-01
```

### Auth 能力表

| 端点 | Guest | Auth |
|------|:-----:|:----:|
| UserTweets | ⚠️ 97条热门 | ✅ 全量+分页 |
| UserTweetsAndReplies | ❌ | ✅ |
| SearchTimeline | ❌ | ❌（仍空） |
| 总量上限 | ~97 | ~3200 |

---

## 方案 ③：Playwright 浏览器自动化 — 无需账号、全量无上限

### 适合场景
不想搞 auth token 但需要完整时间线的场景。

### 安装
```bash
uv pip install playwright
playwright install chromium
```

### 核心代码
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        proxy={"server": "http://127.0.0.1:7897"},
        headless=True
    )
    page = browser.new_page()
    page.goto(f"https://x.com/{username}")
    page.wait_for_selector('[data-testid="tweetText"]', timeout=15000)

    # 滚动加载更多
    for _ in range(scroll_count):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

    # 提取推文
    tweets = page.query_selector_all('[data-testid="tweet"]')
    for tweet in tweets:
        text = tweet.query_selector('[data-testid="tweetText"]').inner_text()
        # ... 提取时间、互动数据等

    browser.close()
```

### Playwright 特点
- ✅ 全量、时间序、无需认证
- ⚠️ 慢（~2秒/滚动，~100条/滚动）
- ⚠️ 首次安装需下载 ~150MB Chromium

---

## 方案 ④：twscrape — 多账号自动轮换

### 适合场景
高频采集、需要多账号防止限流

```bash
pip install twscrape
```

```python
import asyncio
from twscrape import API, gather

async def search_tweets():
    api = API(proxy="http://127.0.0.1:7897")
    await api.pool.add_account("user", "pass", "email", "email_pass")
    await api.pool.login_all()

    # 搜索
    results = await gather(api.search(
        "from:aleabitoreddit NBIS since:2025-11-01 until:2025-12-01", limit=100
    ))
    for t in results:
        print(f"{t.date} | {t.rawContent[:100]}")

    # 全量 Timeline
    user = await api.user_by_login("aleabitoreddit")
    tweets = await gather(api.user_tweets(user.id, limit=500))
```

详见 `references/twscrape-setup.md`

---

## 方案 ⑤：X MCP 官方服务器（2026-07 新增）

X 官方托管 MCP 服务器，OAuth 2.0 认证，提供搜索、用户查找、趋势、书签等。

**优先使用 MCP，本 skill 中所有 GraphQL/Playwright 方案退为备用。**

详见 `references/x-mcp-server.md`

---

## 通用知识

### ⚠️ 关键：Python 用 curl，不用 urllib/requests

Python 的 `urllib.request` 和 `requests` 库通过代理 `127.0.0.1:7897` 访问 X API **全部返回 404**（SSL/TLS 协商问题），curl 正常。

```python
# ✅ 正确——永远用 subprocess 调 curl
import subprocess, json

def curl(method, url, headers=None):
    cmd = ["curl", "-sL", "--connect-timeout", "15", "-X", method,
           "--proxy", "http://127.0.0.1:7897"]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return json.loads(result.stdout) if result.stdout.strip() else {}
```

### 代理设置
```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"
```

### Query ID 会过期
X 不定期更换 GraphQL query ID。404 时重新提取：

| 操作 | Query ID（当前） | 
|------|-----------------|
| UserTweets | `hr4gzZONlq23okjU8fIe_A` |
| UserTweetsAndReplies | `FIFgycIi-CNJcV0R-135Uw` |
| SearchTimeline | `Bcw3RzK-PatNAmbnw54hFw` |
| UserByScreenName | `32pL5BWe9WKeSK1MoKv20w` |

从 main JS 重新提取：
```bash
curl -sL --proxy http://127.0.0.1:7897 "https://x.com" | \
  grep -oP 'src="https://abs\.twimg\.com/responsive-web/client-web/main\.[^"]+\.js"' | \
  head -1 | xargs -I{} curl -sL --proxy http://127.0.0.1:7897 {} | \
  grep -oP 'queryId:"([^"]+)",operationName:"(UserTweets|UserTweetsAndReplies|SearchTimeline)"'
```

### 其他端点
| 端点 | 用途 | 限制 |
|------|------|------|
| `api.fxtwitter.com/<name>` | 用户资料（粉丝数/简介） | 无 timeline，无 tweets |
| `syndication.twitter.com/timeline-profile/screen-name/<name>` | 嵌入式时间线 | ~97条，不分页，有缓存延迟 |
| Nitter 实例 | 第三方前端 | ❌ 全部已死 |

### Token 有效期
- **Bearer token**：静态，极少变（从 main JS 提取）
- **Guest token**：~1小时，每次请求前重新激活
- **auth_token**：数月有效，改密码或异地登录失效
- **ct0**：与 auth_token 配对，同样数月有效

### 代理验证
```bash
curl -sL --connect-timeout 10 \
  -X POST "https://api.x.com/1.1/guest/activate.json" \
  -H "Authorization: Bearer AAAAAA...TnA" \
  --proxy "http://127.0.0.1:7897"
# 200 + guest_token = 代理通
```

---

## 其他 X 相关 skill 的区别

- **`x-monitor`**：定时监控 + cron + 推送到 Telegram。本 skill 解决「怎么抓」，x-monitor 解决「怎么定时抓+推送」
- **`serenity-search`**：Serenity 专用的搜索+缓存工具（`serenity_search/search.py`），不是通用抓取
- **`serenity-tweet-analysis`**：Serenity 推文分析工作流（翻译→大白话→金融分析）

---

## 参考文件

- `references/x-mcp-server.md` — X MCP 官方服务器配置指南（2026-07 新增，首选方案）
- `references/twscrape-setup.md` — twscrape 完整安装配置指南
- `references/x-api-endpoints.md` — GraphQL 端点详细文档
- `references/cookie-extraction.md` — 浏览器提取 auth_token 和 ct0 步骤
- `references/query-id-extraction-guide.md` — Query ID 提取方法
- `references/graphql-endpoints.md` — GraphQL 端点参考
- `references/x-api-reverse-engineering.md` — 逆向过程完整记录
- `references/bearer-token.md` — Bearer Token 提取记录
- `references/query-ids.md` — Query ID 历史记录
- `references/serenity-profile.md` — Serenity 博主资料
- `references/serenity-archive.md` — Serenity 推文归档笔记
- `scripts/x_search.py` — curl-based 搜索脚本模板
- `scripts/scrape_timeline.py` — Auth 模式 timeline 抓取脚本
- `scripts/debug_guest_api.py` — Guest API 调试脚本
