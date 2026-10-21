# 搜索工具现状（2026-06-25）

## 代理环境

- 代理地址：`127.0.0.1:7897`
- 代理 IP：`162.248.224.204`（数据中心 IP）
- 代理放行范围：X.com 相关流量

## 各搜索引擎可用性

| 工具 | 连接方式 | 结果 | 备注 |
|------|---------|------|------|
| Google | 直连 | ❌ 超时 | 被墙 |
| Google | 代理 | ❌ CAPTCHA | IP 162.248.224.204 被标记 |
| Google Custom Search API | 代理 | ⚠️ 需 key | 免费 100次/天，范围受限 |
| **Bing 国际版** | 直连 | ✅ 可用 | www.bing.com（非 cn.bing.com） |
| **Tavily API** | 直连 | ✅ 可用 | api.tavily.com 可直连 |
| Startpage | 直连 | ❌ 超时 | — |
| Startpage | 代理 | ⚠️ JS 渲染 | curl 不可用 |
| Brave Search | 直连 | ❌ 超时 | — |
| SearXNG | 直连 | ❌ 超时 | — |
| Bing (cn.bing.com) | 直连 | ⚠️ 受限 | 中文内容可搜，英文结果受限 |

## Tavily 配置

- API key 位置：`C:\Users\Administrator\Desktop\Tavily API key.txt`
- Python 包：`tavily-python` (v0.7.26)，用 `uv pip install` 安装
- 免费套餐：1000 次/月
- search_depth=advanced 会抓取二跳页面，include_raw_content=True 返回全文

## Claude Code 代理配置

```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"
```

OAuth 和 API 调用都需要代理环境变量。Claude Code CLI 不继承系统代理设置。

## 结论

当前主力搜索方案：Tavily API（英文搜索）+ Bing 国际版（补充验证）。Google 需要更换为住宅 IP 代理或使用 ValueSERP 等搜索 API 服务才能恢复。
