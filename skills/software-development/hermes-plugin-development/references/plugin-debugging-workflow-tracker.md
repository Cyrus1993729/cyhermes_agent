# workflow-tracker 插件调试完整记录

## 时间线 (2026-07-24)

1. 创建插件 → gateway 重启 → `hermes plugins enable workflow-tracker` → 显示 enabled
2. 首次实战测试（金价走势分析）→ Agent 全程跳步，追踪文件空白，无任何注入感知
3. 怀疑插件未生效 → 加心跳日志（无条件写文件到 `~/.hermes/logs/workflow-tracker-heartbeat.log`）
4. 重启 gateway → 心跳仍为空 → 确认 hook 完全未被调用
5. 发插件代码+API 文档给 Opus 诊断 → **确诊：函数签名不匹配**
6. 修复 → 重启 → 心跳有记录 → 注入效果可见 ✓

## 根因分析

```python
# ❌ 错误：只声明 2 个具名参数
def inject_workflow_state(session_id=None, user_message=None, **kwargs):

# ✅ 正确：完整匹配 API 契约 6 个参数
def inject_workflow_state(session_id=None, user_message=None,
    conversation_history=None, is_first_turn=None,
    model=None, platform=None, **kwargs):
```

Python 的 `**kwargs` 只吸收**关键字参数**，不吸收**位置参数**。
Hermes v0.19 按位置传 6 个参数 → 函数体执行前抛 TypeError → hook runner 静默吞异常。

## 排查方法

1. **加无条件心跳**: 在回调函数第一行写文件（不依赖任何条件判断）
2. **重启 gateway**: `hermes gateway restart`
3. **查心跳日志**: `tail ~/.hermes/logs/workflow-tracker-heartbeat.log`
   - 空 → hook 未被调用（注册/签名问题）
   - 有 → hook 在跑（可能是返回值格式或业务逻辑问题）

## 次要注意事项

- `Path.home()` 在 gateway 服务进程下可能指向错误目录 → 用 `HERMES_HOME` 环境变量覆盖
- Windows 上 `open(file, "a")` 不指定 encoding → 中文写入可能 UnicodeEncodeError → 被 `except: pass` 静默吞 → 加 `encoding="utf-8"`
