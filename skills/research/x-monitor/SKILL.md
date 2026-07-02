---
name: x-monitor
description: "【定时监控 X 账号+推送到微信】部署 cron 每天拉最新推文、中文摘要、推送到微信。| 跟 x-twitter-data-extraction 的区别：那个是「怎么抓数据」（Guest API/Auth/Playwright/twscrape 四档方案），本 skill 是「怎么定时抓+自动推送」——只关注 cron 部署和交付流程，不重复讲抓取技术。"
version: 2.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [twitter, x, monitor, proxy, china, cron, graphql, api]
    requires: [x-twitter-data-extraction]
---

# X/Twitter Monitor — 从中国监控 X 账号

## 触发条件

- 用户想追踪某个 X/Twitter 博主的动态
- 用户要求「每天告诉我 XXX 的最新推文」
- 用户分享 X 博主截图后想持续监控

## 前置条件

- 代理可用（Clash Verge 默认 `127.0.0.1:7897`）
- 知道目标账号的 screen_name（如 `aleabitoreddit`）

## 接口速查（优先级从高到低）

| 接口 | 用途 | 时效 | 分页 | 推荐度 |
|------|------|------|------|--------|
| **X GraphQL API** | 推文时间线（最新 + 历史） | 实时 | ✅ cursor | ⭐⭐⭐ **首选** |
| `api.fxtwitter.com/{name}` | 用户资料（粉丝数/简介等） | 实时 | ❌ | ⭐⭐ 辅助 |
| `syndication.twitter.com/timeline-profile/screen-name/{name}` | 嵌入式时间线 | 缓存延迟 | ❌ 有限 | ⭐ 备用 |
| Nitter 实例 | 第三方前端 | — | — | ❌ 已死 |

---

## 🚀 首选方案：X GraphQL API（v2.0 新增）

### 原理

X 的 Web 客户端通过 GraphQL API 获取数据。我们模拟这个流程：

1. 从 x.com 主页 JS 提取 Bearer token（静态，极少变）
2. 激活 guest token（每次调用）
3. 调用 `UserTweets` GraphQL 查询
4. 用 `cursor` 分页翻历史

### 快速使用：一行命令

```bash
# 拉最新 20 条
python scripts/fetch_tweets.py aleabitoreddit

# 拉全部历史（100 页上限）
python scripts/fetch_tweets.py aleabitoreddit --all --max-pages 100

# 指定页数和 cursor
python scripts/fetch_tweets.py aleabitoreddit --count 50 --cursor <cursor>
```

### 手动流程（如需调试）

**Step 1: 激活 guest token**

```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

GUEST_TOKEN=$(curl -sL --connect-timeout 10 \
  -X POST "https://api.x.com/1.1/guest/activate.json" \
  -H "Authorization: Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA" \
  -H "User-Agent: Mozilla/5.0" | python -c "import sys,json; print(json.loads(sys.stdin.read())['guest_token'])")
```

**Step 2: 解析 screen_name → user_id**

GraphQL: `UserByScreenName` (query ID: `32pL5BWe9WKeSK1MoKv20w`)

**Step 3: 拉推文**

GraphQL: `UserTweets` (query ID: `hr4gzZONlq23okjU8fIe_A`)

API 端点格式：
```
https://x.com/i/api/graphql/{QUERY_ID}/UserTweets?variables={...}&features={...}
```

Headers:
```
Authorization: Bearer {BEARER}
x-guest-token: {GUEST_TOKEN}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

Variables:
```json
{
  "userId": "1940360837547565056",
  "count": 20,
  "cursor": null,
  "includePromotedContent": false,
  "withVoice": true,
  "withV2Timeline": true
}
```

**响应结构：**
```
data.user.result.timeline.timeline.instructions[]
  └─ TimelineAddEntries
       ├─ TimelineTimelineItem → content.itemContent.tweet_results.result.legacy
       │    ├─ full_text       # 推文正文
       │    ├─ created_at      # 发布时间
       │    ├─ favorite_count  # 点赞
       │    ├─ retweet_count   # 转发
       │    ├─ reply_count     # 回复
       │    └─ id_str          # 推文 ID
       └─ TimelineTimelineCursor (Bottom) → value  # 下一页的 cursor
```

### Query ID 会过期！

X 会不定期更换 GraphQL query ID。当 API 返回 404 时：

```bash
# 从主 JS 中提取当前 query ID
export HTTP_PROXY="http://127.0.0.1:7897"
curl -sL "https://x.com" | python -c "
import sys, re
scripts = re.findall(r'src=\"([^\"]*main[^\"]*\.js[^\"]*)\"', sys.stdin.read())
if scripts:
    print(scripts[0])
" | xargs -I{} curl -sL {} | python -c "
import sys, re
text = sys.stdin.read()
for m in re.finditer(r'queryId:\"([^\"]+)\",operationName:\"(UserTweets|UserByScreenName)\"', text):
    print(f'{m.group(2)}: {m.group(1)}')
"
```

输出示例：
```
UserTweets: hr4gzZONlq23okjU8fIe_A
UserByScreenName: 32pL5BWe9WKeSK1MoKv20w
```

---

## 辅助：fxtwitter（仅 profile）

```bash
export HTTP_PROXY="http://127.0.0.1:7897"
curl -sL "https://api.fxtwitter.com/{screen_name}" | python -c "
import sys, json
d = json.loads(sys.stdin.read())
u = d.get('user', {})
print(f'名称: {u.get(\"name\")}')
print(f'粉丝: {u.get(\"followers\")}')
print(f'推文数: {u.get(\"tweets\")}')
print(f'认证: {u.get(\"verification\",{}).get(\"verified\")}')
print(f'简介: {u.get(\"description\",\"\")[:200]}')
"
```

---

## 完整监控部署

### 一次性：拉取全量历史

```bash
python scripts/fetch_tweets.py {screen_name} --all > ~/x_history_{screen_name}.json
```

### 每日监控 cron

```bash
cronjob(
    action='create',
    schedule='0 9 * * *',          # 每天早 9 点
    prompt='用 scripts/fetch_tweets.py 拉取 @{screen_name} 最新推文。
             和 ~/x_history_{screen_name}.json 对比，只处理新增的。
             每条推文用中文提取：核心观点、涉及的股票代码、情绪方向。
             用 send_message 分段发送到微信。',
    skills=['x-monitor'],
    enabled_toolsets=['terminal'],
    model={provider='deepseek', model='deepseek-v4-pro'}
)
```

**去重策略：** 读取上次最新推文 ID，只取 ID > 该值的新推文。跑完后更新 ID 记录。

---

## 陷阱 & 经验

### 接口选择
- **首选 GraphQL API** — 实时、支持分页、数据完整。唯一缺点是 query ID 偶尔过期。
- **syndication 接口是备选** — 返回也是完整 JSON，但有缓存延迟（数小时到数天），且不分页。
- **不要试 Nitter。** 所有实例要么停运，要么返回空 body（HTTP 200 + Content-Length: 0）。
- **fxtwitter 只能拿 profile。** `/tweets`、`/timeline`、`/status` 全部 404。

### 认证
- **Bearer token 是静态的**，从 x.com 主 JS 文件提取。当前值在脚本中硬编码。如果 JS 文件名变了（`main.bfb69eea.js` 可能换成新 hash），重新提取即可。
- **Guest token 每次调用前激活**，有效期短，不要缓存。

### 分页
- 每页最多约 100 条，用 `cursor` 字段翻页。
- API 可能在中途返回空（不报错），此时 `next_cursor` 为 null。
- X 的 API 对历史推文有上限（约 3200 条可见），更早的可能无法通过 API 获取。

---

## MCP 替代方案（新增！2026-07-01）

X 已于 2026-06-30 发布 **托管 MCP 服务器**（官方通道，无需逆向工程）。
- 详见 `references/x-mcp-server.md` — 方案对比、配置方式、迁移路径
- 当前 `x-monitor` 仍以 GraphQL 逆向方案为主；MCP 包名确认后逐步迁移

## 参考文件

- `scripts/fetch_tweets.py` — 完整可执行脚本（支持 --all 历史拉取 + --cursor 分页）
- `references/syndication-response-format.md` — syndication 接口返回格式（备用方案）
- `references/fxtwitter-api-notes.md` — fxtwitter 接口限制
