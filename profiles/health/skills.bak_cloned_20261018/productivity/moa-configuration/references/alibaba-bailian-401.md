# 阿里百炼 401 根因完整报告（2026-06-27）

## 排查工具：Claude Code Opus 4.8（只读源码分析）

## 结论

阿里百炼 DashScope 的 Anthropic 兼容端点 (`dashscope.aliyuncs.com/apps/anthropic`)
返回 401 的**根因不是 key 问题，而是 Hermes 的 auth 头不匹配**。

## 关键事实

1. ✅ 直接用 curl/urllib 测试——认证头 `x-api-key` → HTTP 200
2. ✅ 直接用 curl/urllib 测试——认证头 `Authorization: *** HTTP 200
3. ✅ API key 正确（sk-ws- 格式，116 字符）
4. ❌ Hermes 内部调用 → 401

## 根因

`agent/anthropic_adapter.py` 中的 `_requires_bearer_auth()`（~531 行）
只白名单了 **MiniMax**（`api.minimax.io/anthropic`、`api.minimaxi.com/anthropic`）
和 **Azure**（`azure.com`）走 `Authorization: Bearer`。

DashScope 的 `dashscope.aliyuncs.com/apps/anthropic`（或 `dashscope-intl`）**不在白名单中**，
因此走了 `x-api-key` 路径。

而百炼的 Anthropic 兼容端点**要求** `Authorization: *** 头。

## 认证机制区分

| 头 | Hermes 何时发送 | 百炼接受？ |
|:---|:---|:---|
| `x-api-key` | 原生 Anthropic API 和未白名单的第三方端点 | ❌ 401 |
| `Authorization: *** 白名单端点（MiniMax、Azure）或 OpenAI 兼容端点 | ✅ |

## 修复方案

### 方案 A：改源码（永久修复）
在 `agent/anthropic_adapter.py:531` 的 `_requires_bearer_auth` 中增加百炼：
```python
or "dashscope.aliyuncs.com/apps/anthropic" in normalized
or "dashscope-intl.aliyuncs.com/apps/anthropic" in normalized
```

### 方案 B：换端点（零代码改动，推荐）
把 `base_url` 从 Anthropic 兼容端点改成 OpenAI 兼容端点：
```yaml
providers:
  qwen-bailian:
    base_url: https://ws-XXXXX.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
    api_mode: chat_completions
```
OpenAI 兼容端点本身就用 `Authorization: *** 路径。

## 排查时间线

1. 直接 HTTP 验证 key 有效（200）→ 排除 key 问题
2. MoA 返回 401 → 怀疑 MoA dispatch 路径
3. 方案 A（改端点）→ 仍 401
4. 方案 B（用 OAuth）→ Qwen CLI 0.19.2 已移除 auth 命令，不可用
5. **交给 Claude Code Opus 4.8**（--bare + --allowedTools Read）→ 阅读源码找到根因
6. Opus 报告：`_requires_bearer_auth` 白名单缺失
7. 方案 B 采用 OpenAI 兼容端点 → 待测试

## Claude Code Opus 调用记录

- 尝试 1：提示词含 YAML → bash 误解析
- 尝试 2：pipe 传参 → max turns 耗尽
- 尝试 3：加 --allowedTools Read → 仍 max turns
- 尝试 4：加 --bare → 丢失登录态
- **尝试 5：成功**（--model opus --max-turns 20 --allowedTools Read --output-format text）
- 关键教训：不要用 `--bare`（会丢失 OAuth 登录），不要直接在 -p 参数里嵌入 YAML
