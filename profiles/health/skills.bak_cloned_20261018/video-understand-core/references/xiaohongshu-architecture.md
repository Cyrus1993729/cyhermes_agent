# 小红书内容分析 — 技术架构

> 2026-06-16 Claude Code (Opus) 技术研判产出。
> ⚠️ 时效性标注：小红书反爬机制变动频繁，以下结论基于 2025 年底/2026 初的认知。标有 ⚠️ 的条目建议在实现前联网验证。

## 核心发现

**小红书的分享链接自带访问通行证 (`xsec_token`)**。用户从 App 复制链接时，链接内已包含 token，无需登录即可访问单篇笔记页。内容（标题/正文/图片URL/视频URL）均以 JSON 形式内嵌在首屏 HTML 的 `<script>window.__INITIAL_STATE__=...</script>` 中。

## 与 B站 pipeline 的本质差异

| 维度 | B站 | 小红书 |
|------|-----|--------|
| 内容获取 | `bilibili-api-python` 下载视频 | HTTP GET 笔记页 → 解析 HTML JSON |
| 内容载体 | 视频文件 → ASR+OCR | 图片+正文+可选视频 |
| 反爬 | 轻度（公开 API） | 中-重度（需 token/cookie） |
| 下载 | CDN 直链 | 视频 URL 在 JSON 中，需带 Referer |

**关键架构取舍：不碰需要签名的 JSON API（`x-s`/`x-t`），只走 HTML 页面解析。** 签名逆向是无底洞；页面解析对反爬升级的抵抗力更强（尤其配合 Playwright 截图兜底）。

## 三层降级架构

```
用户发来链接/含链接的文字
        │
        ▼
[L0] 输入解析：正则抽 URL → 跟随 xhslink.com 短链 302 → 得到带 token 的真实 URL
        │
        ▼
[L1] 轻量主路径：HTTP GET 笔记页（住宅IP + 真实UA + 复用cookie）
        │      解析 window.__INITIAL_STATE__ → 取 title/desc/图片URL/视频URL
        │      成功？ → 图片走 Vision，文本走 DeepSeek 总结  ✅
        │
        ├── 失败（token失效/验证码/字段变更）
        ▼
[L2] 兜底路径：Playwright 持久化登录 → 打开URL → 整页截图 → Vision 读图  ✅
        │
        └── 视频帖：解析/拦截拿到 masterUrl → 下载(带Referer) → ASR → 总结
```

## L1: HTML 解析 — 主力路径

### 小红书分享链接格式

- **短链**：`http://xhslink.com/xxxxx`（用户从 App 复制的常见格式，常夹杂中文推广语）
- **真实页**：`https://www.xiaohongshu.com/explore/{note_id}?xsec_token=XXX&xsec_source=pc_share`
- **处理要点**：跟随短链 302 重定向，**务必保留全部 query 参数**（token 在 query 里）

### `__INITIAL_STATE__` 解析

- ⚠️ 字段路径近一年有调整（`note.noteDetailMap[...]` 结构），实现时需验证
- 关键目标字段：`title`, `desc`, `imageList[]`, `video.media.stream.masterUrl`
- 无需签名，完全不依赖逆向

### 访问稳定性

| 因素 | 影响 |
|------|------|
| `xsec_token` | **必需**。裸 note_id 无法访问 |
| Cookie (`a1`, `web_session`, `webId`) | 非必需但**显著降低验证码概率** |
| User-Agent | 建议伪装移动端或桌面端真实 UA |
| IP 类型 | 住宅 IP（用户 Windows）远优于数据中心 IP |
| 访问频率 | ad-hoc 低频使用，风控风险极低 |

## L2: Playwright 截图 — 兜底路径

### 为什么需要

- L1 解析依赖 `__INITIAL_STATE__` 字段结构。小红书改版可能改变字段名/路径 → L1 临时失效
- L2 用「真浏览器 + 整页截图 + Vision」对页面改版**几乎免疫**——页面长什么样，模型就看到什么

### 实现要点

- `launchPersistentContext` 指定固定 profile 目录，cookie 持久化
- 用户**只需扫码登录一次**，后续全自动
- 检测 L1 失败特征（token 失效 / 验证码页面 / 字段缺失）→ 自动切换 L2
- 首次使用时：助手提示用户扫码 → 等待完成 → 验证 cookie 有效性 → 保存 profile

### 维护特性

- 对小红书前端改版免疫（只要页面能渲染，Vision 就能读）
- cookie 过期（几周一次）时：助手检测到失效 → 主动提示用户重新扫码
- 无需维护签名逆向、无需跟踪 API 变更

## L3: 视频处理 — 按需启用

### 视频 URL 获取

1. **L1 路径**：解析 `__INITIAL_STATE__` → `note.video.media.stream.masterUrl`
2. **L2 路径**：Playwright 拦截网络请求，hook `response` 抓 `.mp4`/视频流真实 URL

### 下载要点

- 下载时**必须带 `Referer: https://www.xiaohongshu.com/`** 请求头，否则 CDN 403
- CDN 域名通常为 `sns-video-*.xhscdn.com`
- ⚠️ 视频 URL 有时效性，拿到后尽快下载

### yt-dlp 备选

- yt-dlp 历史上有小红书 extractor，但时好时坏
- 可作为视频下载的第一道尝试，失败后回落到自己解析 JSON

### 轻量替代

很多投资/认知类帖子信息密度集中在**封面图+标题+正文**中。可以先只取封面+标题+desc 给 DeepSeek，只有当用户明确要求「看视频里说了什么」时才触发完整下载→ASR 链路。

## 实施路线图

### P0 — 主路径（半天工作量）
1. 输入解析器：从用户消息抽 URL，跟随 `xhslink.com` 短链重定向
2. HTTP GET 笔记页，解析 `__INITIAL_STATE__`，提取 title/desc/imageList
3. 图片 → Vision，文本 → DeepSeek 总结

### P1 — cookie 持久化
4. 用户登录一次，保存 cookie 长期复用
5. 加重试 + L1→L2 自动切换（检测需登录/验证码页面特征）

### P2 — Playwright 兜底
6. `launchPersistentContext` + 固定 profile
7. 失败时整页截图 → Vision

### P3 — 视频支持（按需）
8. 解析/拦截视频 URL → 带 Referer 下载 → faster-whisper ASR

## 用户操作（仅两项）
1. **首次**：扫码登录一次（获取 cookie）
2. **日常**：把小红书分享链接（或含链接的文字）发给助手

## ⚠️ 待联网验证的时效性结论

1. `xsec_token` 当前是否仍是访问笔记页的必要参数，`xsec_source` 取值
2. `__INITIAL_STATE__` 当前字段路径（近一年有调整）
3. 视频流 `masterUrl` 是否仍可凭 Referer 直接下载，是否加了新 token
4. 住宅 IP 下未登录抓单篇页的验证码触发频率
