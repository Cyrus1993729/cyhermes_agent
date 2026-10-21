# OpenCode Go Fallback 链设计 —— 2026-08-16 故障复盘 + Opus 红队审查

## 故障时间线（2026-08-16）

| 时间 | 事件 |
|---|---|
| 11:00 | 五类日报成功（同日对照：上午网关正常） |
| 16:32 | TG polling degraded 一次（本地代理抖动迹象，独立事件） |
| 16:56 | MCP x server keepalive failed（独立事件） |
| 17:00:18 | 日报 Job A 首调 deepseek-v4-flash @ opencode-go → 连接挂起 |
| 17:01:18 | APIConnectionError（60s 超时）→ 重试 |
| 17:02:21 | 再次 APIConnectionError → fallback 激活 qwen3.7-max @ opencode-go-anthropic |
| 17:02:23 | fallback 首调 2s 内收到 503 "Upstream request failed: Endpoint is unavailable"（服务端响应，网关活着） |
| 17:02:41 | 503×3 后任务以 error 结束；cron 输出文件 = `# Cron Job: ... (FAILED)` 报告（非日报） |
| 17:15 | Job B 投递任务静默（草稿非今天，符合 deliver_cb.py 设计） |
| 17:30 | api_healthcheck 正常（静默）——30 分钟粒度抓不住 2.5 分钟窗口 |
| 17:43 | api_probe OK 2.5s（自愈确认） |
| 17:53 | 手动 cronjob run Job A 成功（草稿 16KB + 存档生成） |
| 17:55 | 手动 cronjob run Job B 投递成功（标记 == 草稿 mtime，agent.log 见 delivered） |

故障窗口 ≈2.5 分钟（17:00:18-17:02:41），自愈。同日 17:53 同配置重跑成功 → 判定瞬时上游故障，非配置 bug。

## 根因链

1. 主链路（deepseek @ opencode-go）与 fallback（qwen @ opencode-go-anthropic）**同一 opencode.ai 网关**（不同协议路径但同域名同服务）
2. 网关整体故障：OpenAI 兼容端点连接挂起（60s×2），Anthropic 兼容端点返回 503（网关→上游模型供应商不可用）
3. 同源 fallback 形同虚设 → 任务失败，无自动重试 → 当天日报缺失

## Opus 红队审查要点（决定方案走向）

- **M1 根因分层**：APIConnectionError（本地侧连接失败）与 503（服务端响应）是两种不同性质失败，可能叠加（本地代理抖动 + 上游不可用）。但 503 是硬证据：opencode.ai 网关在 17:02 是活的，是它的上游端点不可用
- **M2 最便宜修复被漏**：cron 延迟重跑（失败后 10 分钟自动重试）对"瞬时故障 + 非实时日报任务"100% 有效、零成本、零新 provider 风险——优先级高于 fallback 链
- **M3 第二层是 bug 隐藏器**：fallback 链无触发告警时，第一层配错会被第二层静默接住 → 必须可观测
- **M4 会话粘性 = 成本乘数**：sticky fallback 时一次抖动 = 整个日报任务几十次调用全走按量付费（源码确认 sticky，见 SKILL.md）
- **M5 context 不匹配**：同名模型在不同 provider 窗口可能不同 → 400 → 链条继续掉。DeepSeek 官方与 Go 同模型名规避此问题
- **L1** provider 名拼错行为未知（可能继承主 base_url 发到错误端点）
- **L2** 提高健康检查频率是错误方向（烧额度买抓不住的探针）；正确 = fallback 触发即告警
- **L3** 主 + 第二层仍同域名 opencode.ai，单点未真正消除
- **总评**：方向对（单一服务商单点是真实的），但 qwen-bailian 第一层是错的选择；最小改动 = 重跑兜底 + DeepSeek 官方 fallback

## 验证数据（第 0 步，全部只读实测）

- DeepSeek 官方 API：`GET https://api.deepseek.com/v1/models` → `deepseek-v4-flash` / `deepseek-v4-pro`（**官方已弃 deepseek-chat 命名**）；key 有效（注释在 .env），直连 + 代理 7897 均 200/0.1s
- 内置 `deepseek` provider：plugins/model-providers/deepseek/__init__.py — env_vars=("DEEPSEEK_API_KEY",)，base_url=https://api.deepseek.com/v1
- dashscope workspace 端点：238 模型，含 qwen3.7-max；直连 + 代理均通（作为第三层候选）
- OpenCode Go 端点：26 模型，配置引用的 deepseek-v4-flash/pro、qwen3.7-max、kimi-k2.7-code、minimax-m3 全部存在
- api_probe.py / api_healthcheck.py：已迁移 opencode-go 端点（opencode.ai/zen/go/v1/chat/completions + UA 头 + 代理 7897），迁移彻底
- agent 请求路径：bash HTTPS_PROXY=http://127.0.0.1:7897 + NO_PROXY（不含 opencode.ai）→ httpx trust_env 默认走代理 = 与探测脚本同一路径，探测有效

## 拟定方案（2026-08-16 定稿，待用户确认实施）

**第 1 步（零成本）**：Job A schedule `0 17 * * *` → `0,10 17 * * *` 双触发点；prompt 开头加幂等检查（今天草稿/存档已存在 → 输出 [SILENT] 退出，避免重复跑）。

**第 2 步（fallback 独立化）**：
```yaml
fallback_providers:
  - provider: deepseek        # 内置 provider，官方 API，独立于 opencode.ai
    model: deepseek-v4-flash
fallback_model:               # 第二层保留（覆盖仅 Anthropic 端点挂的场景）
  provider: opencode-go-anthropic
  model: qwen3.7-max
```
配套：.env 取消注释 DEEPSEEK_API_KEY。主链路仍全走 Go 订阅；qwen-bailian 作第三层候选（覆盖 DeepSeek 上游也挂的罕见场景）。

**第 3 步（可观测）**：fallback 触发告警——扫当天 agent.log "Fallback activated" → TG 告警（并入 healthcheck_daily.py 或独立 cron）。

## 排查姿势复盘

- 判断配置 bug vs 瞬时故障：**重跑测试**是黄金标准（同配置故障后重跑成功 = 瞬时故障）
- cron 输出文件是 `# Cron Job: ... (FAILED)` 报告（read_file 可能判 binary，用 python 读）
- Clash sidecar_latest.log 会轮转：先 head/tail 确认覆盖范围再下"没走代理"结论（本次 17:59 轮转，17:00 前记录全丢，一度误判）
- fallback 触发证据在 agent.log：`Fallback activated: deepseek-v4-flash → qwen3.7-max (opencode-go-anthropic)` + `clearing primary credential pool (pool_provider=opencode-go)`
