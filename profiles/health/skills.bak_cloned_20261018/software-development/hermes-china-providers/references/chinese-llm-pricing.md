# 中国大模型 API 定价对比

最后更新: 2026-08-13（DeepSeek 8/17 涨价方案已公示；Token Plan 调研）

## 按量价（每百万 token，人民币）

| 模型 | 缓存命中输入 | 未命中输入 | 输出 | 来源 |
|:---|:--:|:--:|:--:|:---|
| DeepSeek V4 Flash（8/17 前现价） | 0.02 | 1 | 2 | api-docs.deepseek.com |
| DeepSeek V4 Flash · 空闲（8/17 起） | 0.05 | 1.5 | **4.5** | 官方新价表 |
| DeepSeek V4 Flash · 高峰（8/17 起） | 0.10 | 3.0 | **9.0** | 官方新价表 |
| DeepSeek V4 Pro（8/17 前现价） | 0.025 | 3 | 6 | api-docs.deepseek.com |
| DeepSeek V4 Pro · 空闲（8/17 起） | 0.15 | 4.5 | **13.5** | 官方新价表 |
| DeepSeek V4 Pro · 高峰（8/17 起） | 0.30 | 9.0 | **27.0** | 官方新价表 |
| Qwen 3.7 Max | 12（限时 5 折 6） | 12（5 折 6） | 36（5 折 18） | help.aliyun.com |
| Qwen 3.8 Max | 12 | 12 | 36 | help.aliyun.com（无 5 折标记） |
| Kimi K3 | 2 | 20 | **100** | platform.kimi.com |
| GLM-5.2 | 2 | 8 | 28 | bigmodel.cn |

**排序（输出价，便宜→贵）**：DeepSeek flash 空闲 4.5 < flash 高峰 9 < DeepSeek pro 空闲 13.5 < 千问 3.7 5折 18 < GLM-5.2 28 < 千问 3.8 36 < pro 高峰 27 < Kimi K3 100。

## DeepSeek 8/17 涨价方案（2026-08-13 官方公示，8/17 00:00 生效）

- 时间线：8/6 预告"整体上调、涨幅较大" → 8/13 官方定价页挂出新价表（api-docs.deepseek.com/zh-cn/quick_start/pricing，比新闻早）
- **新结构 = 峰谷定价（空闲 = 高峰一半），且整体价格中枢上移**——不是简单"现价×2"：flash 输出 2 → 空闲 4.5（×2.25）/ 高峰 9（×4.5）；flash 缓存命中 0.02 → 0.05（×2.5）/ 0.10（×5）；pro 输出 6 → 13.5 / 27
- 高峰时段：北京时间工作日 9:00-12:00、14:00-18:00；空闲 = 其余时段（含 12-14 点午间、18 点后）
- **用户月费估算方法**（Hermes agent 场景，622M token/月 ¥79.21 反推）：从账单反解用量结构——输出仅 ~3%（18.8M）、输入 97%（603.7M，95% 缓存命中）。涨价后：全空闲 ~158 元 / 70% 高峰 ~270 元 / 全高峰 ~317 元（**3-4 倍**）。cron 定时（11:00/17:00）和白天对话都踩高峰 → 实际偏上限
- **涨价后仍碾压性最便宜**：flash 高峰输出 9 vs 千问 36 vs K3 100——同用量月费 DeepSeek ~270-320 vs 千问 ~1700+ vs K3 ~3600。预算敏感时优先"用量工程"（错峰 -45%、上下文瘦身 -50%）而非换模型

## Token Plan 对比（2026-08-13 调研，用户预算 ≤100 元/月）

| Plan | 价格 | 额度 | 兼容 622M/月 用量 | 合规/风险 |
|:---|:---|:---|:---|:---|
| **OpenCode Go**（opencode.ai/go） | 首月 $5，之后 **$10/月**（≈72 元） | 等价用量 $12/5h、$30/周、$60/月 | ✅ 选便宜模型档（GPT-5.6 Luna / MiMo V2.5 / DeepSeek flash）~$11-40/月 | 官方明示"可配合任何代理"（Hermes 合规✅），无禁自动化条款；超额度免费模型兜底；美国服务器需代理；模型偏编程向 |
| 百炼 Token Plan Standard | 139 元/月 | 10,000 credits/7 天（≈4.3 万/月） | ⚠️ 临界——credits 换算官方不透明，实测才知道（qwen3.6-plus 示例：输入 ~200 credits/M、缓存 ~20-40/M、输出 ~1204/M） | Hermes Agent 在官方兼容工具列表✅；**个人版明文禁止"API 形式自动化/非交互式批量调用"**（cron 日报踩线灰色区）；数据用于训练；7 天窗口触顶即暂停 |
| 百炼 Lite | 39 元/月 | 2,500 credits/7 天 | ❌ 只够约一半（8/11 分析） | 同上 |
| 智谱 GLM Coding Plan | Lite ~$10/月、Pro ~$30/月（~200+ 元） | Lite 10,000 积分/周、Pro 60,000 | ❌ Lite 只够 24%（积分公式实测：用户周消耗 ~40,868 积分）；Pro 够但超预算 | 积分公式公开：（输入×6.9+缓存×1.7+输出×24）/10000；非高峰（非周一至五 14-18 点）50% 抵扣；仅限官方指定工具 |
| Kimi 会员（Moderato 99 元） | 99 元/月 | 会员额度只给 Kimi Code 工具 | ❌ **Hermes 无法用会员额度**（接 Kimi 只能按量 API 20/100 元，用不起） | — |

**要点**：
- 百炼套餐内模型列表含 deepseek-v4-pro/flash-0731，但同样受"禁自动化"约束
- 百炼 Token Plan 专属 key 是 `sk-sp-` 开头，与普通百炼 key 不通用（混用 = 按量扣费不消耗套餐）
- OpenCode Go 各模型单价（美元/M）：GLM-5.2 $1.4/$0.26/$4.4、Kimi K3 $3/$0.3/$15、GPT-5.6 Luna $0.2/$0.02/$1.2、MiMo V2.5 $0.14/$0.0028/$0.28
- 用户当前倾向（2026-08-13）：先试 OpenCode Go（最便宜+合规最宽松），百炼 Standard 备选，GLM/DeepSeek 涨价后按量均不达标

## 定价页可爬取性

| 供应商 | 页面 | 可爬取 | 方法 |
|:---|:---|:--:|:---|
| DeepSeek | api-docs.deepseek.com/zh-cn/quick_start/pricing | ✅ | curl 直接抓，纯 HTML 表格（8/13 已验证含新价表） |
| Kimi | platform.kimi.com / kimi.com/zh-cn/resources/kimi-k3-pricing | ✅ | web_extract 可拿（8/12 验证） |
| GLM | bigmodel.cn/pricing + docs.bigmodel.cn/cn/coding-plan/overview | ✅ | web_extract 可拿（含积分系数） |
| Qwen/百炼 | help.aliyun.com/zh/model-studio/model-pricing + token-plan-*-overview | ✅ | web_extract 可拿（8/12-13 验证；此前 6/29 记录"JS 渲染不可爬"已过时） |
