---
name: wechat-article-scraping
description: Scrape articles from WeChat Official Accounts (微信公众号) — Sogou search for quick results, getmsg API for full history, Playwright rendering for JS-heavy pages.
version: 1.0.0
author: Hermes Agent
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [wechat, scraping, knowledge-base, content-extraction, playwright]
    related_skills: [bilibili-content-extraction, xiaohongshu-analysis]
---

# WeChat Official Account Article Scraping

抓取微信公众号历史文章，用于知识库构建或内容分析。

## 核心原理

微信文章只有两个公开入口：
1. **搜狗微信搜索** (weixin.sogou.com) — JS 渲染，反爬强，只能拿到最近 ~100 篇
2. **微信内部 getmsg API** — 需要登录 Cookie，能翻到建号以来全量文章

没有公开 API、没有文章索引页、搜索引擎不收录微信文章。

## 两阶段策略

### 阶段一：搜狗搜索（快速，有限）

适用于快速拿到一批文章、验证公众号是否存在、提取公众号 ID。**搜狗是初始抓取的首选方案**——不需要登录、不依赖用户操作。

**前提：Playwright + 系统 Chrome（不需要 playwright install chromium）**

```bash
uv pip install playwright
# 系统 Chrome 路径: C:\Program Files\Google\Chrome\Application\chrome.exe
```

**搜狗搜索 URL 格式：**
```
https://weixin.sogou.com/weixin?type=2&s_from=input&query={公众号名}&ie=utf8&page=1
```

- `type=1` → 搜公众号（仅限官方认证号，多数个人号搜不到）
- `type=2` → 搜文章（推荐，覆盖更广）

**核心踩坑：搜狗搜索覆盖率与噪音**

搜狗实际只对每个公众号索引前 2-3 页的有效结果。实测数据：
- 第 1-2 页：90%+ 为目标号文章
- 第 3 页：开始混入噪音（同名不同号）
- 第 4 页起：80%+ 为噪音（搜索引擎按字符拆分匹配，如"一味"+ "君"）
- Chrome 在翻到第 4 页时常因 OOM 崩溃 → **每页用独立浏览器实例**
- 典型产出：15-20 篇真正属于目标号的文章

**使用 `wait_until="domcontentloaded"` 而不是 `"networkidle"`**——微信页面有大量持续的后台请求（分析、广告），`networkidle` 会超时。

**搜狗反爬：**
- 搜狗跳转链接包含会话级 token，**必须在同一 session 内立即跟随**（见下方"合并搜索+跳转"）
- 反爬在 Phase 2（跟随跳转）触发率最高，搜索阶段通常安全
- 触发反爬后需等 8-10s 冷却
- 用 `channel="chrome"` 比默认 Chromium 指纹更好

### 阶段二：getmsg API（全量历史，仅限自有账号）

**⚠️ 重大限制**：getmsg API 需要登录 mp.weixin.qq.com，但该后台**只能管理登录者自己的公众号**。你无法用它查看/抓取其他人的公众号文章。这意味着**对别人公众号的完整历史抓取，目前没有免费技术方案**。

如果抓取的是用户**自己**的公众号，getmsg 是最佳方案：

**前提条件：**
1. 用户在 Chrome 登录 `https://mp.weixin.qq.com`（微信扫码）
2. 该公众号必须是用户自己管理的账号
3. Playwright 使用 `channel="chrome"` + persistent context 继承 Chrome 的登录态

**Cookie 获取的坑：**
- `browser-cookie3` 在 Windows 上无法解密 Chrome 的 DPAPI 加密 Cookie ❌
- `launch_persistent_context` 在 Chrome 运行时因 profile 锁定而失败 ❌
- **可行方案**：开一个可见的 Playwright 浏览器窗口，用户在窗口里扫码登录 → 保存 Cookie 供后续使用
- `wait_until="networkidle"` 在 mp.weixin.qq.com 会超时 → 必须用 `"domcontentloaded"`

**API 格式：**
```
GET https://mp.weixin.qq.com/mp/profile_ext
  ?action=getmsg
  &__biz={公众号biz}
  &f=json
  &offset={翻页offset}
  &count=10
  &is_ok=1
```

**返回 JSON 结构：**
```json
{
  "ret": 0,
  "can_msg_continue": {下一页offset或0表示结束},
  "general_msg_list": "[{\"comm_msg_info\":{\"datetime\":...,\"id\":...},\"app_msg_ext_info\":{\"title\":\"...\",\"content_url\":\"...\",\"digest\":\"...\",\"cover\":\"...\",\"multi_app_msg_item_list\":[...]}},...]"
}
```

**无登录态的返回：`ret=-3, errmsg=no session`**
**非自有账号的返回：同上（即使已登录，也只能看自己的号）**

## 完整工作流（实际可行版）

**抓取别人的公众号（最常见场景）：**
```
用户提供公众号名
    ↓
[搜狗搜索] Playwright 搜狗 type=2 搜索
    ↓
合并搜索+跳转：每搜到一篇立即跟过去拿真实 URL 和 biz
    ↓
过滤噪音：用 biz 验证是否属于目标号
    ↓
翻页到噪音超过 50% 或 Chrome 崩溃 → 停止
    ↓
逐篇加载正文 → 保存到知识库
    ↓
预期产出：15-20 篇有效文章
```

**抓取自己的公众号（如有权限）：**
```
用户提供文章链接 → 提取 biz
    ↓
用户扫码登录 mp.weixin.qq.com（Playwright 可见窗口）
    ↓
getmsg API 循环分页 → 全量文章（可到建号第一篇）
    ↓
逐篇加载正文 → 保存到知识库
```

## 直接文章链接抓取（最快路径，首选）

用户直接给出 `mp.weixin.qq.com/s/xxx` 文章链接时，**不需要搜狗、不需要 Playwright**：

### 🔴 `web_extract` 会**静默截断**正文 —— 永远当「预览」用，不要当成品（2026-11-12 实踩）

2026-11-12 抓一味君《我们现在的亚马逊做法》：`web_extract` 返回 4,277 字，**结尾停在句子中间**
（「认知驱动供应链——因为你知道用户真正在意什么（比如运动产品」戛然而止），
而全文实际 **4,533 字**，后面还有「四：运营是执行岗位」「五：721 法则总结」「六：推荐工具」三个大节。
**它不报错、不提示截断**，`char_limit` 调大也没用（不是长度限制，是正文容器被提前闭合）。

**判据**：`web_extract` 结果**最后一句不是句号/问号收尾** → 立刻判定截断，改走 curl 全文路径。
**代价**：直接拿它存盘 = 用户拿到一份缺三分之一、且看不出缺了一部分的知识库文件。

→ **正解：`web_extract` 只用来 5 秒确认「链接活着、标题对不对」，正式交付一律用下面 curl 全文路径。**

✅ **同效替代（2026-11-16 实测）：已经开着浏览器时，不用 curl，直接用 browser_exec 取 `#js_content` innerText**：
`js("(() => { const e=document.querySelector('#js_content')||document.body; return e.innerText; })()")`
——本次同一篇链接：`web_extract` 只返回概述版（丢了「01/02/03」三节正文），
`#js_content` innerText 拿到 **2,193 字的完整正文**（含鱼尾「欢迎来吹牛」）。
判据同上：看结尾是不是句号收尾；不放心就用 `document.querySelector('#activity-name').innerText` 核对标题、
比对长度是否明显大于 web_extract 返回值。适合只是要「读文章内容做分析」、不需要落盘成知识库的场景。

### 交付路径：curl 全文 → `#js_content` 提取 → 缺句校验

1. **curl + 浏览器 UA 下载整页**：
   ```bash
   curl -s --noproxy '*' 'https://mp.weixin.qq.com/s/xxx' \
     -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' \
     -o wx_article.html
   ```
   ⚠️ **不带 UA 必挂**：返回 2KB 的「未知错误，请稍后再试」页面（标题"未知错误"、含 `WeixinJSBridgeReady` 脚本）。这不是网络问题也不是链接失效，是 UA 校验——带 Chrome UA 才能拿到完整 ~3MB HTML。
   ✅ 正常大小参考：3.6 MB / 3.59 M 字符（2026-11-12 实测）。**小于 50 KB 就是被拦了。**
2. **一键提取**：`python scripts/extract_wechat_article.py wx.html out.md <原文链接>`
   —— 元数据 + 正文分层 + 图片链接 + **缺句校验**一次出。
3. **必做完整性校验**（脚本已内置，手工时照抄）：把 `#js_content` 纯文本去空白后按「。！？\n」切句，
   逐句检查是否出现在成品里；**missing 里出现的都是真缺句**，若只因为加了 Markdown 前缀（`## `/`- `）
   导致断句，属假阳性，肉眼扫一遍即可。
   🔴 **假阳性还有第二种成因（2026-11-12 第三篇踩到）**：做比对时把 `-` 也当 Markdown 前缀剔掉了，
   于是「一条链接在小类目 **100-200** 名」这种带连字符的句子永远匹配不上，白报一条缺句。
   **比对时只剔 `#` `*`，不要剔 `-`**；或者直接看成品里 `grep` 关键词确认。

### 🔴 微信正文的三个结构坑

| 坑 | 现象 | 处理 |
|---|---|---|
| **小标题没有 h 标签** | 「一：xxx」「二、xxx」只是加粗 `<span style="font-weight:bold">` 的普通段落 | 文本层正则识别，**分隔符必须含「、」**：`^[一二三四五六七八九十]{1,2}\s*[：，,:、]` → `## `；`^\d+[.、]` 且 ≤26 字且以 `。？` 结尾 → `### `（2026-11-12 第三篇就是「一、」，漏了「、」整篇标题全没认出来） |
| **文首有目录** | 正文开头先列一遍「一、二、三…」的框架目录 | 目录那几行转成 `- `，**不要和正文章节一起转 `## `**。🔴 判据用**开头连续 N 行（N≥2）章节标题且后面还有章节标题**，不要用「同名标题出现两次」——目录和正文标题措辞常不同（目录「四：运营是执行岗位和维护岗位」vs 正文「…和优化岗位」），会漏判 |
| **容器正则可能提前闭合** | `id="js_content"` 里嵌套 div | 🔴 **已修复**：`scripts/extract_wechat_article.py` 改用 `HTMLParser` **按 div 深度计数**截取（2026-11-12 第二篇实测：正则版能跑但理论上会在首个 `</div><script` 提前闭合，不再冒这个险） |
| **微信表情混进图片清单** | `res.wx.qq.com/.../Expression/*.png` 是表情，不是配图 | 图片清单里过滤 `res.wx.qq.com`；否则「图片数」虚高（实测 5→3）、文末链接表全是表情 |
| **没有 h 标签的小标题** | 「第一步 先看清盘子有多大」也是普通段落 | 加一条正则：`^第[一二三四五六七八九十\d]{1,2}步\s*\S` 且 ≤30 字 → `### ` |

### 广告段照原文保留，但要在回执里点名

公众号文章常带返佣广告（折扣码、服务商链接）。**用户要「扒正文」就照原文保留**，不要自行删除，
但回执里要明说「第 N 节是广告/返佣内容，需要纯干货版我可以另存一份」——决定权交回用户。

**元数据提取**（页面变量与 DOM）：
- 公众号 ID：`var user_name = "gh_xxxxx"`
- 发布时间：`var create_time = "1786665721"`（Unix 秒 → 转北京时间，可判断是否新文）
- 公众号显示名：`<a id="js_name">一味君</a>`（⚠️ **不是** `var nickname`，该变量在部分页面不存在）
- 作者：`<span id="js_author_name">跨境三人行</span>`
- biz：部分页面无 `var __biz`；直接链接场景不需要它

一键提取：`python scripts/extract_wechat_meta.py <html文件>`（只取元数据）。
**元数据 + 正文一起出**用 `scripts/extract_wechat_article.py`（见下节）。

## 文章正文抓取

拿到 `content_url` 后，用 Playwright 加载页面：
- 正文在 `#js_content` 或 `.rich_media_content` 中
- 页面标题：`var msg_title = "..."` 
- 发布时间：`var create_time = "..."`（Unix 时间戳）
- 作者：`var nickname = "..."`

## 限制与风险

| 风险 | 说明 |
|------|------|
| **搜狗覆盖率上限** | 实测每个公众号只能拿到 15-20 篇有效文章（前2-3页），第4页起80%+为噪音 |
| **搜狗深度翻页 Chrome 崩溃** | 翻到第4页 Chrome 常因 OOM 崩溃 → **每页用独立浏览器实例** |
| **getmsg 仅限自有账号** | 登录 mp.weixin.qq.com 只能管理自己的号，无法抓取别人的文章 |
| 搜狗反爬 | 跳转链接包含会话级 token，必须立即跟随；触发后等 8-10s |
| **browser-cookie3 Windows 不可用** | Chrome 用 DPAPI 加密 Cookie，Python 无法解密 |
| **Chrome profile 锁定** | 用户正在用 Chrome 时，`launch_persistent_context` 失败 |
| **networkidle 超时** | 微信页面后台请求不断，始终用 `domcontentloaded` |
| 搜狗未认证号 | 未认证公众号在搜狗搜不到（type=1），但 type=2 可能搜到文章 |
| 搜索引擎不收录 | Bing/Google 不索引微信文章 |

## 搜狗搜索关键实操细节

### 合并搜索+跳转（防止 token 过期）

**错误做法**：先遍历所有搜狗页面收集链接 → 再逐个跟随跳转。跳转 token 已经过期 → 全被反爬拦截。

**正确做法**：在同一会话内，搜到一篇文章后**立即**跟随跳转：

```python
# Phase 1: 收集链接 → Phase 2: 跟随跳转  ← 错误！
# 改为在同一个 page.goto 循环内：
for pagenum in range(1, MAX_PAGES + 1):
    await page.goto(search_url)  # 搜索页面
    links = await page.query_selector_all('.txt-box h3 a')
    for link in links:
        href = await link.get_attribute('href')
        await page.goto(f"https://weixin.sogou.com{href}")  # 立即跟随！
        final_url = page.url  # 拿到真实 mp.weixin.qq.com URL
```

### 过滤搜狗噪音

搜狗搜索 `type=2` 按关键词匹配，第 3 页起出现大量同名但不同账号的文章：
- 例：搜"一味君"会出现"补阳还五汤"、"茶境一味 邀君品鉴"等无关文章
- 过滤方法：跟随跳转后从页面源码提取 `var biz`，与已知公众号的 biz 对比
- 备选：维护噪音关键词黑名单（但对新内容不通用，biz 验证更可靠）

### Biz 提取与验证

从文章页面源码提取：
```python
import re
biz_match = re.search(r'var\s+biz\s*=\s*"([^"]+)"', page_content)
# 或 var __biz = "..." （两种变量名都存在）
```

验证是否属于目标公众号：`biz == "Mzg3ODcwNTI4NA=="`（例：一味君）

## 替代方案

| 方案 | 完整性 | 成本 |
|------|:---:|------|
| 搜狗搜索 | 低（~100篇） | 免费 |
| getmsg API + Cookie | 高（全量） | 免费，需用户操作 |
| 新榜/清博/西瓜数据 | 高 | 付费 |
| `wechat-article-exporter`（浏览器插件） | 高 | 免费，需用户在浏览器操作 |

## 🔑 UA 不只影响微信——「同一 UA 规则」适用于其它中文平台（2026-11-05）

本文上面那条「不带 UA 必挂」不是微信独有的怪癖，而是中文内容平台的一个**通用模式**：
站点按 User-Agent 分流，哄回来的 HTML 要么是完整页、要么是登录墙/空壳。

**遇到「HTML 很小 + 关键数据键为空」时，先换 UA 再改解析器**：

| 站点 | 桌面 UA 的结果 | 解法 |
|---|---|---|
| 微信公众号 | 2KB 「未知错误」页 | 带 Chrome UA |
| 小红书 `/discovery/item/` | **302 跳 `/login`**，37KB 空壳（`noteDetailMap` 为空） | **换 iPhone UA** → 165KB 完整页，`__SETUP_SERVER_STATE__` 出现 |

→ 完整症状对照、判定顺序（302/login 或 HTML<50KB → 立即换 UA）、以及配套的「用 python urllib 而非 bash 循环批量下静态资源」：
见 `references/mobile-ua-fetch-bypass.md`。

## 参考文件

- `references/getmsg-api-reference.md` — getmsg API 详细说明和返回格式
- `references/mobile-ua-fetch-bypass.md` — **移动端 UA 降级通用解法**：登录墙/空壳页识别、iPhone UA 实测对照表、批量下载静态资源必用 python 的姿势
- `references/sogou-playwright-workflow.md` — Sogou + Playwright 完整实操脚本与关键踩坑记录
- `scripts/extract_wechat_article.py` — **直接链接交付首选**：离线 HTML → Markdown（元数据头 + 小标题分层 + 图链 + 缺句校验）
- `references/yiweijun-case-study.md` — 一味君抓取实战案例：结果数据、getmsg 权限限制发现、Chrome 崩溃解决方案
