---
name: workflow-tracker-plugin
description: "Hermes Plugin Hook (pre_llm_call) that auto-injects workflow tracking file state into every turn, so the Agent never forgets which step it's on. Solves the 'PC in Agent's attention' problem — the system reads the tracking file, not the Agent."
version: 1.0.0
category: productivity
tags: [workflow, plugin, hook, pre-llm-call, tracking, context-injection]
---

# Workflow Tracker Plugin

基于 Hermes `pre_llm_call` Plugin Hook 的流程追踪注入插件。每轮自动读 `workflow_*.md` 并将未完成步骤注入 Agent 上下文。

## 解决的问题

追踪文件本身是"建议性状态"——Agent 得主动记得去读。长对话中上下文压缩会把提示滚出注意力窗口，Agent 忘记检查追踪文件，跳过后续步骤直接收尾。

本插件把"读文件"从 Agent 手里拿走——**系统每轮替 Agent 读**。Agent 不需要"记得"，系统替它记。

## 安装

```bash
mkdir -p ~/.hermes/plugins/workflow_tracker
```

创建 `~/.hermes/plugins/workflow_tracker/plugin.py`：

```python
"""Workflow tracker — inject current workflow state every turn via pre_llm_call."""
from pathlib import Path


CONTRACTS_DIR = Path.home() / ".hermes" / "contracts"


def inject_workflow_state(session_id, user_message, **kwargs):
    """Read workflow_*.md and inject unchecked steps into the user message."""
    files = sorted(
        CONTRACTS_DIR.glob("workflow_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None

    wf = files[0].read_text(encoding="utf-8")

    unchecked = []
    for line in wf.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            unchecked.append(stripped)

    if not unchecked:
        return None

    steps = "\n".join(unchecked)
    return {
        "context": (
            "⚠️ 当前流程追踪文件中有未完成步骤：\n"
            f"{steps}\n\n"
            "请检查是否遗漏了上述步骤。如果当前阶段已完成，请更新追踪文件勾选。"
        ),
    }


def register(ctx):
    ctx.register_hook("pre_llm_call", inject_workflow_state)
```

启用：

```bash
hermes gateway restart
```

## 效果

每轮 Agent 在用户消息末尾看到：

```
⚠️ 当前流程追踪文件中有未完成步骤：
- [ ] ④ task-wrapup → 审查+存档+交付
- [ ] ⑤ post-task-review → 复盘+写入 lessons.md
```

## 关键设计决策

- **注入到用户消息**（非系统提示词）→ 保护 prompt cache
- **只注入未完成步骤** → 全完成时零噪音注入
- **临时注入** → 不写数据库，不影响原始消息
- **静默容错** → 无追踪文件时返回 None，不报错

## 局限性

- 只在 Gateway 运行时生效（CLI 直连不触发 Plugin hooks）
- 不阻止步骤跳过——只提醒。真正硬闸门在 skill 自检逻辑
- 不替代追踪文件——追踪文件仍是真相源，插件只是消费者
