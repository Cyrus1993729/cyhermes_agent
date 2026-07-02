# 中国大模型 API 定价对比

最后更新: 2026-06-29

## 文本生成模型（每百万 token，人民币）

| 模型 | 输入（缓存命中） | 输入（缓存未命中） | 输出 | 上下文 | 来源 |
|:---|:--:|:--:|:--:|:--:|:---|
| DeepSeek V4 Pro（平时） | ¥0.025 | ¥3 | ¥6 | 1M | api-docs.deepseek.com |
| DeepSeek V4 Pro（高峰）⚡ | ¥0.05 | ¥6 | ¥12 | 1M | 官方通知（7月中旬实施） |
| Kimi K2.7 Code | ¥1.30 | ¥6.50 | ¥27 | 262K | platform.moonshot.cn |
| Kimi K2.7 Code HighSpeed | ¥2.60 | ¥13 | ¥54 | 262K | platform.moonshot.cn |
| GLM-5.2 | ¥2（缓存命中） | ¥8 | ¥28 | 1M | open.bigmodel.cn |
| Qwen 3.7 Max | — | — | — | — | ❌ 阿里云百炼 JS 动态渲染，公开页面无法爬取 |

## 价格排序（输出价格，便宜→贵）

| 排名 | 模型 | 输出 ¥/M |
|:--:|:---|:--:|
| 1 | DeepSeek V4 Pro（平时） | ¥6 |
| 2 | DeepSeek V4 Pro（高峰） | ¥12 |
| 3 | Kimi K2.7 Code | ¥27 |
| 4 | GLM-5.2 | ¥28 |
| 5 | Kimi K2.7 Code HighSpeed | ¥54 |

## 定价页可爬取性

| 供应商 | 页面 | 可爬取 | 方法 |
|:---|:---|:--:|:---|
| DeepSeek | api-docs.deepseek.com | ✅ | curl 直接抓，纯 HTML 表格 |
| Kimi | platform.moonshot.cn/docs/pricing | ✅ | browser_navigate + browser_snapshot |
| GLM | open.bigmodel.cn/pricing | ✅ | browser_navigate + browser_snapshot |
| Qwen/百炼 | help.aliyun.com/zh/model-studio | ❌ | 全部 JS 渲染，控制台需登录 |

## Chrome CDP 爬取方法

Kimi 和 GLM 定价页为 JS 渲染，需通过 Chrome DevTools Protocol 抓取：

```bash
# 1. 启动 Chrome（headless + 允许 CDP）
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* \
  --headless=new --no-sandbox --disable-gpu

# 2. 在 Hermes 内通过 browser_navigate 加载页面
# 3. browser_snapshot 提取表格内容
```

对于 Aliyun（Qwen），`help.aliyun.com` 使用动态路由，公开文档页无法加载定价详情。需手动登录 bailian.console.aliyun.com 查看。

## ⚠️ DeepSeek 高峰定价（7月中旬起）

- 高峰时段：工作日北京时间 9:00-12:00、14:00-18:00
- 高峰价格 = 平时价格 × 2
- 目前有效通知来源：DeepSeek API 用户站内信/邮件（非公开网页）
- 平时价已通过 api-docs.deepseek.com 验证
