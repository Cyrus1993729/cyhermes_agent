---
name: hermes-plugin-development
description: Hermes Agent 插件开发与调试——hook API 契约、常见 bug、调试方法。
version: 1.0.0
tags: [hermes, plugin, hook, debugging]
---

# Hermes 插件开发与调试

## pre_llm_call hook API 契约（v0.19）

**触发**: 每轮一次，`run_conversation()` 内，context compression 后、工具循环前。

**回调签名**（必须逐参数匹配）:
```python
def callback(session_id=None, user_message=None, conversation_history=None,
             is_first_turn=None, model=None, platform=None, **kwargs):
```

**返回值**: `{"context": "..."}` 或 纯字符串 → 追加到用户消息；`None` → 不注入。

## 常见 bug

### 函数签名不匹配（2026.7.24 实战）

**症状**: 插件 enabled、gateway 重启、全程无效果。
**根因**: 只声明 2 个参数 `(session_id=None, user_message=None, **kwargs)`。`**kwargs` 不吸收多余位置参数 → TypeError 在函数体执行前被 hook runner 静默吞。
**修复**: 完整列出 6 个参数。
**最快排查**: 加无条件心跳日志写文件→重启→查文件是否存在。空=hook 未调用。

详见 `references/plugin-debugging-workflow-tracker.md`。

## 插件文件结构

```
~/.hermes/plugins/<name>/
├── plugin.yaml    # name, version, hooks: [...]
├── __init__.py    # from .plugin import register
└── plugin.py      # def register(ctx): ctx.register_hook(...)
```

启用: `hermes plugins enable <name>`（需 gateway 重启生效）。
