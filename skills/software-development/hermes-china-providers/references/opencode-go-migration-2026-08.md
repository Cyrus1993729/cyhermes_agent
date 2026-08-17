# OpenCode Go 迁移落地配方（2026-08-16 实测执行）

DeepSeek 官方 API → OpenCode Go 套餐的全量迁移记录。触发背景：DeepSeek 8/17 官方涨价，用户订阅 OpenCode Go（$10/月）替代官方按量。

## 迁移前盘点（全量接入点）

| 位置 | 改什么 |
|---|---|
| `config.yaml` `model` 段 | base_url + provider |
| `config.yaml` `cron` 段 | model_provider（cron 任务默认模型） |
| `config.yaml` `fallback_model` | provider |
| `config.yaml` `moa.presets.china` | aggregator + 2 个 reference_models 的 provider |
| `.env` | `DEEPSEEK_API_KEY` → `OPENCODE_GO_API_KEY`（旧 key 注释保留） |
| `auth.json` deepseek 凭据池 | 不动（回滚保险） |
| `scripts/api_healthcheck.py` | KEY_PATH + URL + UA 头 |
| `scripts/api_probe.py` | 同上 |
| `skills/video-understand-core/scripts/pipeline.py` | key 读取 + URL + 模型名 |
| `skills/video-understand-core/scripts/quick_summary.py` | 同上 |

## 关键事实（文档没写的坑）

1. **内置 provider 优先**：Hermes v0.19.1 内置 `opencode-go`（读 `OPENCODE_GO_API_KEY`，base_url 固定 `https://opencode.ai/zen/go/v1`）。配 `.env` 即可，不要配自定义 providers 段带 api_key——会报 "No usable credentials found for provider 'opencode-go'. Set OPENCODE_GO_API_KEY."
2. **端点**：真实 API = `https://opencode.ai/zen/go/v1/chat/completions`（OpenAI 兼容）。`https://opencode.ai/go/v1` 是文档页 HTML。
3. **协议分裂**：DeepSeek/Kimi/GLM/MiMo/Hy3 → OpenAI 兼容（Bearer）；**Qwen/MiniMax → Anthropic 兼容 `/v1/messages`（x-api-key）**。需两个 provider。
4. **urllib 403**：默认 urllib UA 被网关拒（403）。加 `User-Agent: curl/8.0.0`。requests 库不受影响。

## 配置落地（最终形态）

```yaml
# config.yaml
model:
  base_url: https://opencode.ai/zen/go/v1
  default: deepseek-v4-flash
  provider: opencode-go          # 内置 provider，读 .env
providers:
  opencode-go-anthropic:          # 自定义，qwen 专用（Anthropic 协议）
    base_url: https://opencode.ai/zen/go/v1
    api_key: sk-...               # 同一个 Go key
    api_mode: anthropic_messages
cron:
  model: deepseek-v4-flash
  model_provider: opencode-go
fallback_model:
  model: qwen3.7-max
  provider: opencode-go-anthropic   # ⚠️ 必须 anthropic provider，不能 opencode-go
moa:
  presets:
    china:
      aggregator:
        model: deepseek-v4-pro
        provider: opencode-go
      reference_models:
        - model: qwen3.7-max
          provider: opencode-go-anthropic
        - model: kimi-k2.7-code
          provider: opencode-go
```

```bash
# .env
OPENCODE_GO_API_KEY=sk-...
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
#DEEPSEEK_API_KEY=(old official, commented out, rollback insurance)
```

## 脚本改动模式

```python
# api_probe.py / api_healthcheck.py 统一改法
KEY_PATH = r'C:\Users\Administrator\Desktop\各类api key\opencode go api key.txt'
API_URL = 'https://opencode.ai/zen/go/v1/chat/completions'
PROXY = 'http://127.0.0.1:7897'   # Go 服务器海外，走代理
# urllib 必须带 UA 头：
headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
         'User-Agent': 'curl/8.0.0'}
proxy_handler = urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
opener = urllib.request.build_opener(proxy_handler)
```

video 管线（requests 库）：
```python
resp = requests.post("https://opencode.ai/zen/go/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": "deepseek-v4-flash", ...},   # ⚠️ 原 deepseek-chat 在 Go 不存在
    timeout=120, proxies={"http": PROXY, "https": PROXY})
```

## 用量估算（state.db 精确口径）

```sql
-- session_model_usage 表: input_tokens/output_tokens/cache_read_tokens/api_call_count/first_seen(epoch)
SELECT model, billing_provider,
       SUM(api_call_count) calls, SUM(input_tokens) inp,
       SUM(output_tokens) out, SUM(cache_read_tokens) cache
FROM session_model_usage WHERE billing_provider='deepseek' GROUP BY model;
```

折算成本 = inp/1e6×价 + out/1e6×价 + cache/1e6×缓存价（Flash $0.14/$0.28/$0.0028；Pro $0.435/$0.87/$0.0036）。

## 验证清单（14 项 ad-hoc）

1. 4 个改动脚本 ast.parse 语法
2. 改动文件无 `api.deepseek.com` / `deepseek-chat` 残留
3. Go key 文件可读（len>20）
4. 真实端点 + curl UA → 200
5. 实跑 api_probe.py → `OK <秒>`
6. 实跑 api_healthcheck.py → 静默
7. quick_summary.get_deepseek_key() 返回 Go key
8. pipeline.py 引用 go key 文件 + deepseek-v4-flash
9. config.yaml model → opencode-go
10. config.yaml cron → opencode-go
11. MoA wiring（aggregator/references provider）
12. .env 含 OPENCODE_GO_API_KEY
13. Hermes CLI 主模型回复（无 fallback 警告）
14. qwen 通过 opencode-go-anthropic 回复（anthropic 端点）

## 风险备忘

- **Pro $15/月档是硬顶**：用户 30 天 $12.52 = 83%。重活月必撞，撞了 MoA aggregator 整条拒。用户已知情接受（低频使用）。
- ZDR 协议 8/31 到期（Flash 数据保留 0 天当前），OpenCode 可能调整定价——唯一变数。
- 回滚 = 取消注释 DEEPSEEK_API_KEY + 改回 base_url + provider=deepseek。
