---
name: serenity-search
description: "【Serenity 专用搜索+缓存】搜索 @aleabitoreddit 的推文——关键词/日期/最新，本地缓存+独立脚本。| 跟 x-twitter-data-extraction 的区别：那个是通用 X 抓取工具（所有账号），本 skill 是 Serenity 一个人的专用搜索+本地缓存系统（serenity_search/search.py），有独立 token 配置和增量更新逻辑。"
---

# Serenity Search — 搜索 X 博主 @aleabitoreddit 的推文

## 触发条件
用户要求搜索 Serenity 的推文，包括：
- "Serenity 关于 NBIS 说了什么"
- "看看 Serenity 最近发了什么"
- "搜一下 Serenity 5月份的推文"
- "Serenity 有没有提过 XXX"

## 工具位置
```
C:\Users\Administrator\serenity_search\search.py
```

## 使用方法

### 更新缓存（拉最新推文）
```bash
python C:/Users/Administrator/serenity_search/search.py --update
```

### 搜索关键词
```bash
python C:/Users/Administrator/serenity_search/search.py "NBIS" --limit 10
python C:/Users/Administrator/serenity_search/search.py "photonics"
```

### 看最新推文（⚠️ 用户偏好：只要1条 + 完整原文）
```bash
# 用户说"最新推文"时，只给 1 条，给完整原文，不要摘要
python C:/Users/Administrator/serenity_search/search.py --latest 1
# 然后用 python 读取 cache.jsonl 获取完整 full_text（--latest 可能截断）
python -c "
import json
tweets = []
with open(r'C:\Users\Administrator\serenity_search\cache.jsonl', encoding='utf-8') as f:
    for line in f:
        if line.strip(): tweets.append(json.loads(line))
latest = max(tweets, key=lambda t: t['id'])
print(f'时间: {latest[\"created_at\"]}')
print(f'互动: ❤️{latest[\"favorite_count\"]} 🔄{latest[\"retweet_count\"]} 💬{latest[\"reply_count\"]} 👁{latest.get(\"view_count\",\"?\")}')
print()
print(latest['full_text'])
"
```


### 按日期范围搜索
```bash
python C:/Users/Administrator/serenity_search/search.py --since 2026-05-01 --until 2026-05-31
```

### 组合搜索（关键词+日期）
```bash
python C:/Users/Administrator/serenity_search/search.py "IREN" --since 2026-06-01 --limit 20
```

### 查看缓存统计
```bash
python C:/Users/Administrator/serenity_search/search.py --cache-stats
```

## 认证文件
Token 配置文件：`C:\Users\Administrator\serenity_config\token.txt`
包含 `AUTH_TOKEN` 和 `CT0_TOKEN`。如果过期（出现 CSRF 错误），提示用户重新从浏览器复制。

X API 技术细节见 `references/x-api-notes.md`（query ID、端点状态、逆向笔记）。

## 缓存位置
`~\serenity_search\cache.jsonl` — 推文缓存
`~\serenity_search\state.json` — 抓取状态

## 工作流程
1. 每次搜索前先 `--update` 增量拉取最新推文
2. 再执行实际搜索
3. 结果用中文汇报给用户

## ⚠️ 用户交付偏好（重要）

- **"最新推文" = 只发 1 条**，给完整英文原文，不要摘要、不要批量、不要翻译
- **"搜 XX" = 自然数量**，每条给原文摘要 + 日期 + 互动数据
- **"分析这条推文" = 委托 Claude**，用 `delegate_task` 联网搜索 + 深度阅读理解

## 🤖 深度分析工作流

当用户要求分析某条推文时，使用 `delegate_task` 委托子代理：
- **必须联网搜索**推文中提到的公司/概念背景——金融/产业链分析禁止仅凭知识储备
- 联网搜索时注意：子代理可能网络不通，需在 context 中说明代理限制（X 走代理，搜索走直连）
- 翻译 + 逐层阅读理解
- 分析判断逻辑、产业链关系、与核心方法论的关联
- 输出格式：原文 → 翻译 → 公司背景 → 产业链关系 → 判断逻辑 → 结论
- 注明信息来源性质（官方公告 / 新闻报道 / 推断 / 推测）

## 🕸️ 网络代理注意事项（关键）

- **代理规则**：`127.0.0.1:7897` 仅放行 X.com 相关流量（api.x.com、x.com、abs.twimg.com）
- **X API 调用**：必须走代理，用 `export HTTP_PROXY="http://127.0.0.1:7897"` 
- **搜索引擎**：走**直连**（Google/DuckDuckGo 不通），Bing 和百度直连可用：
  ```bash
  # Bing 直连搜索
  curl --noproxy "*" "https://www.bing.com/search?q=..."
  # 或 Python urllib（默认不走代理环境变量）
  ```
- **Python requests/urllib**：X API 用 curl（因 SSL 协商问题 requests 被 X 拒），搜索引擎用 urllib 直连

## 限制
- 只能通过时间线 API 获取推文（不支持 X 原生搜索 API）
- 时间线缓存覆盖约 400-500 条最近的推文（持续 --update 可回溯更远，但 API 限 ~3200 条）
- 如需搜索更早期的内容，需要持续 `--update` 翻页回溯
- Token 过期需要用户手动更新（提示复制新的 auth_token 和 ct0）
- Python 脚本使用 curl subprocess 而非 requests（X 的 SSL 协商拒绝了 requests 库）
