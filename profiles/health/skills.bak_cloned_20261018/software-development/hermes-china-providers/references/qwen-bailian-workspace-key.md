# Qwen Bailian (DashScope Workspace Key) Configuration

## Key Format

Workspace keys start with `sk-ws-` and are issued from
[dashscope.console.aliyun.com](https://dashscope.console.aliyun.com).

Example: `sk-ws-H.RYPHLIL.4QLm.xxx...` (116 chars for this key type).

## Endpoint

OpenAI-compatible endpoint (the **only** working one for workspace keys):

```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

**Do NOT use** the Anthropic-compatible endpoint (`dashscope.aliyuncs.com/apps/anthropic`).
Workspace keys reject it with 401 because Hermes sends `x-api-key` but Bailian
expects `Authorization: Bearer`.

## Model ID

`qwen3.7-max` — confirmed working as of 2026-07-23.

To discover all available models for your key:
```bash
KEY=$(grep "^QWEN_API_KEY=" ~/.hermes/.env | sed 's/QWEN_API_KEY=//')
curl --noproxy '*' -s -H "Authorization: Bearer $KEY" \
  "https://dashscope.aliyuncs.com/compatible-mode/v1/models"
```

## ⚠️ stream:false Pitfall (2026-07-23)

Including `"stream": false` in the request body causes:
```json
{"error":{"message":"Required body invalid, please check the request body format.","type":"invalid_request_error"}}
```

**Fix:** omit `stream` entirely. The DashScope compatible-mode endpoint
defaults to non-streaming and rejects the explicit `false`.

```bash
# ✅ CORRECT — no stream parameter
curl -H "Authorization: Bearer $KEY" \
  -d '{"model":"qwen3.7-max","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' \
  https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

# ❌ WRONG — stream:false causes "Required body invalid"
curl -H "Authorization: Bearer $KEY" \
  -d '{"model":"qwen3.7-max","messages":[{"role":"user","content":"hi"}],"max_tokens":10,"stream":false}' \
  https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
```

## Dual-Registration Pattern: scripts + Hermes /model

When a script (e.g. `qwen_review.py`) reads config.yaml directly for a
provider block, AND you also want to use `/model` to switch to it, you
need **both** registrations:

```yaml
# Block 1: standalone — for scripts that parse config.yaml directly
qwen-bailian:
  api_key: sk-ws-xxx...
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  api_mode: chat_completions

# Block 2: custom_providers — for Hermes /model switching (MUST be list format)
custom_providers:
  - name: qwen-bailian
    api_key: sk-ws-xxx...
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_mode: chat_completions
```

With block 2, switching is: `/model custom:qwen-bailian:qwen3.7-max`

## Registration Without Occupying Slots

If `fallback_model` and `delegation` slots are already taken (e.g. by Kimi K3),
you can register Qwen as a **custom provider only** — it won't affect
fallback or delegation behavior, but will be available for:

- `/model` manual switching
- `execute_code` direct API calls
- Scripts like `qwen_review.py`

Existing slot configuration stays untouched:
```yaml
fallback_model:
  provider: kimi-coding-cn
  model: kimi-k3
delegation:
  provider: kimi-coding-cn
  model: kimi-k3
```

## API Smoke Test

```bash
QWEN_KEY=$(cat "path/to/qwen3.7 api key.txt")
curl --noproxy '*' -s -X POST \
  -H "Authorization: Bearer $QWEN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.7-max","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' \
  https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  | python -m json.tool
```

Expected: `"model": "qwen3.7-max"` in output, with `reasoning_content` in the message
(since qwen3.7-max is a thinking model).
