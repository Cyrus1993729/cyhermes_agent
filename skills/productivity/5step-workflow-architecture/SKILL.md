---
name: 5step-workflow-architecture
description: "5步流程架构全景：四个skill+插件+脚本的分工、P0-P3防御分层、已知局限与改进路线图。不是执行指南（各skill已有SOP），而是架构设计文档。"
version: 1.0.0
category: productivity
tags: [workflow, architecture, methodology, meta]
---

# 5步流程架构全景

## 组件清单

| 层 | 组件 | 职责 |
|:---|:---|:---|
| ①契约 | sprint-contract | 写契约 + 执行策略判断 + Opus审契约 |
| ②闸门 | decision-gate | 汇报→征得同意→才能动手 |
| ③执行 | 无专门skill | 按契约策略：单模型 or Kanban |
| ④审查 | l1-review + task-wrapup | L1千问6维 + L2 Opus条件触发 + 存档 + 交付 |
| ⑤复盘 | post-task-review | 记lessons + 学习回路（审查发现→回写契约默认值） |
| 提醒层 | workflow-tracker 插件 | pre_llm_call hook 每轮注入流程状态 |
| 打勾层 | workflow_check.py | P2 脚本：skill完成时自动打勾（圈码匹配） |
| 追踪文件 | workflow_*.md | 状态文件：创建于①，删除于⑤ |

## 防御分层（P0-P3）

| 层级 | 状态 | 能防什么 | 防不了什么 |
|:---|:---|:---|:---|
| **P0 提醒层**（插件注入） | ✅ 已生效 | Agent忘记当前步骤 | Agent读到提醒但选择忽略 |
| **P1 哨兵层**（用户"收尾"） | ✅ 就绪 | 流程停摆 | 用户也不记得喊 |
| **P2 脚本层**（自动打勾） | ⚠️ 软焊点 | Agent走到skill末步时自动记录 | Agent跳过skill末步（执行惯性） |
| **P3 hook层**（不经Agent） | 🔜 待建 | Agent裁量之外的硬闸门 | 尚未实现 |

## 关键架构决策

### 1. 四个skill而非一个
不合并为一个"大skill"：大skill挤占上下文、细节压成大纲、且"加载一次看到全局"的好处在第3轮就失效了。

### 2. 插件=唠叨，不是闸门（2026.7.24 两次测试验证）
插件每轮注入「还有步骤未完成」——Agent看到了，但在长链执行惯性中没响应。这就是Opus说的"软vs硬"：注入≠阻断。

### 3. P2 焊点仍是"软"的（2026.7.24 实踩）
即使每个skill末步焊了 `python workflow_check.py --step "X"`，Agent仍可能跳过这些焊点——因为它们是skill文本里的指令，不是系统强制执行的hook。Opus审查结论："P2把失败点从文件编辑挪到了命令调用，概率上无本质改善。"

### 4. 路径一致性（2026.7.24 Opus审查发现）
插件和workflow_check.py必须共用同一个路径解析逻辑。两者都使用 `HERMES_HOME` 环境变量（未设置则回退到 `Path.home()/AppData/Local/hermes`）。历史上曾有分歧（插件用 `~/.hermes`，脚本用硬编码路径），导致两组件指向不同目录。

### 5. 插件函数签名必须完整匹配API契约（2026.7.24 bug）
Hermes v0.19 的 `pre_llm_call` 回调传6个位置参数。函数签名只声明2个→TypeError在函数体执行前抛出→hook runner静默吞异常→插件"默默不工作"。修复：完整列出所有6个参数。

## 已知局限

1. **"打勾"状态完全由Agent自觉维护**（即使有了P2脚本）。理想状态是：状态由工具/产物推导，不靠Agent自报。
2. **追踪文件是"建议性状态、零强制"**。读它、写它都是Agent可选动作。没有独立验证者。
3. **P3 hook化**是唯一真正的硬保证——让workflow_check从skill指令升级为不受Agent裁量的hook。

## 参见
- `sprint-contract` — ①+②契约+闸门SOP
- `l1-review` — ④审查SOP（6维+L2触发）
- `task-wrapup` — ④收尾调度SOP
- `post-task-review` — ⑤复盘SOP
- `scripts/workflow_check.py` — P2自动打勾脚本
- `plugins/workflow-tracker/` — P0提醒层插件
