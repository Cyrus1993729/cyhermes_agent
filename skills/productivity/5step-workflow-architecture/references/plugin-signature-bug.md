# 插件函数签名调试记录

## 症状
workflow-tracker 插件已 enabled，gateway 已重启，但 Agent 全程无感知。追踪文件有未勾步骤时插件应每轮注入提醒，但一次都没发生。

## 根因
Hermes v0.19 `pre_llm_call` hook 回调签名为 6 个位置参数：
```
def callback(session_id, user_message, conversation_history, is_first_turn, model, platform, **kwargs)
```

但旧代码只声明了 2 个具名参数：
```
def inject_workflow_state(session_id=None, user_message=None, **kwargs)
```

Python `**kwargs` 只吸收多余的**关键字参数**，不吸收多余的**位置参数**。Hermes 按位置调用时，TypeError 在函数体执行前抛出，hook runner 静默吞异常 → 插件"默默不工作"。心跳日志一行都不会写（异常发生在写心跳之前）。

## 修复
完整列出所有 6 个位置参数 + `**kwargs` 兜底。

## 教训
- 插件函数签名必须完整匹配 API 契约。
- 添加心跳日志（在函数体第一行写文件）是排查此类问题的关键。心跳为空 = hook 没被调用。
- Hook runner 静默吞异常——不能指望报错来发现注册/签名问题。
