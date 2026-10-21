# 小红书博主全量帖子抓取 — 技术方案参考

> 来源：2026-07-05 用户提出需求 → Opus (Claude Code) 技术分析
> 状态：方案阶段，未落地
> 本文件供后续推进此需求时参考

## 核心结论

**这件事技术上可行，但真正的难点不是"翻页"，而是小红书 Web API 的请求签名（x-s / x-t）。**
推荐混合方案：用成熟开源项目拿帖子列表 → 喂给现有 xiaohongshu-analysis skill 做深度分析。

## 关键开源项目（GitHub 调研易漏掉）

| 项目 | ⭐ 量级 | 做法 | 适用场景 |
|:---|:---|:---|:---|
| **NanmiCoder/MediaCrawler** | 数万 star | Playwright 持登录态 + 调用站点自身 JS 签名 → 接口取数 | 事实标准，含博主主页全量采集 |
| **ReaJason/xhs** | 数千 star | Python 封装 XHS 接口，可当 SDK 调 `user_posted` | 适合嵌入自己代码 |
| **cv-cat/Spider_XHS** | 数千 star | Node 重写签名算法 | 纯请求、无浏览器，但签名易随版本失效 |

> ⚠️ 注意：mashukui/xhs_one_spider (7⭐)、mashukui/xhs_user_post_tool (3⭐) 等是闭源付费 GUI，本质是把上述开源项目包壳收费。不适合自动化流水线对接。

## 四个核心技术挑战

### 1. 翻页/帖子列表

- **`__INITIAL_STATE__` 只有第一屏（~30条），不是全部。** 与单帖 skill 的经验不同。
- 全量必须走 Web API：`GET /api/sns/web/v1/user_posted`，参数 `user_id`、`num`、`cursor`、`image_formats`
- 用 `cursor` 游标循环翻页到 `has_more=false`
- ⚠️ 具体路径/字段名会随版本变

### 2. 登录态（必须）

- 未登录几乎拿不到任何数据
- 需要有效 Cookie：`a1` / `web_session`
- `web_session` 会过期，需定期刷新
- 建议用小号，降低主号封禁风险

### 3. 请求签名（真正的拦路虎）

- Web API 请求头需要 `x-s`、`x-t`、`x-s-common` 等签名字段
- 由页面混淆 JS 根据请求路径、参数、Cookie（`a1`）、时间戳动态计算

三种路线：

| 路线 | 做法 | 抗变更 | 维护成本 |
|:---|:---|:---|:---|
| 纯逆向签名 | Py/Node 重写签名算法 | 差（JS 一变就挂） | 高 |
| **浏览器代签（推荐）** | Playwright 加载页面，调用站点自身签名函数 | 好 | 中低 |
| 全浏览器滚动截流 | Playwright 直接滚动、拦截 XHR | 最好 | 慢、重、易被检测 |

### 4. 与现有 skill 对接

- 列表接口返回每条笔记带 `xsec_token`
- 详情 URL 格式：`explore/{note_id}?xsec_token=...&xsec_source=pc_user`
- **列表阶段就要把 `xsec_token` 一起传给单帖阶段**，token 有时效
- 现有 skill 的 `xhslink.com` 短链 → GET 重定向逻辑在此场景不适用（那是分享短链）

## 三种方案对比

| | A. 自研（代签路线） | B. 买闭源工具 | **C. 混合（推荐）** |
|:---|:---|:---|:---|
| 列表采集 | 自己写 Playwright | mashukui GUI | MediaCrawler / ReaJason |
| 深度分析 | 现有 skill | ✗ 无法对接流水线 | 现有 skill |
| 维护 | 全自己扛 | 卖家扛（可能停更） | 蹭社区更新 |
| 自动化 | 可以 | 不行（GUI+CSV） | 可以 |

## 维护成本（长期）

- 签名 JS 更新 → 浏览器代签路线基本自愈；蹭开源社区更新
- Cookie / web_session 过期 → 需要账号池 + 定期刷新机制
- 风控收紧 → 降并发、加延时、加代理 IP、多小号轮换
- 字段结构调整 → 列表侧和单帖侧都需预留容错

**建议**：接口/签名适配层 与 业务分析层 解耦，接口一变只改适配层。

## 风险

1. 违反小红书用户协议，采集账号有封禁风险
2. 不存在"零维护"方案——任何方案都要跟接口变更
3. 具体接口名/参数会随版本漂移，落地时以最新开源实现为准

## 下一步推进顺序

1. 评估 MediaCrawler vs ReaJason/xhs 哪个更适合嵌入
2. 设计"列表采集 → token 衔接 → 单帖分析"对接结构
3. 设计账号池 + Cookie 刷新最小可用机制
