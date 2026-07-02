# 多 Agent 生态系统调研（2026年6月）

> 调研来源：小红书视频「拥有上百AI员工是什么体验」+ 联网搜索 + 官方文档交叉验证

## 四大工具速览

| 工具 | 性质 | Stars | 核心定位 | 开源 |
|:---|:---|:--|:---|:---|
| **Moltbook** | AI社交网络 | — | 只允许AI入驻的社交平台，Agent有身份/记忆/社交关系 | ❌ |
| **Paperclip** | Agent管理面板 | 70K+ | "如果OpenClaw是员工，Paperclip是公司" — AI CEO/CTO/CMO管理面板 | ✅ MIT |
| **Claude Code Agent Teams** | IDE内置 | — | 多Claude Code实例协作，支持Agent间直接通信 + 科学辩论 | ❌ |
| **Kimi Agent Swarm** | 对话式集群 | — | 最多300个子Agent并行，教练裁决制，计划引入子Agent直接通信 | ❌ |

## Kimi Agent Swarm 细节

### 核心架构
- Orchestrator（教练）看全局 + 定策略 + 分配任务
- Sub-agents（队员）专注执行，彼此**当前不通信**
- PARL训练：只训练教练，队员冻结 → "所有功劳和责任清晰归属于调度决策"

### 互约束机制
- 角色对立部署（怀疑型VC vs 资深PM vs 伦理专家）
- 上下文隔离（Context Sharding，每个子Agent只看自己的"小本子"）
- 教练做"最终汇总与验收"
- 官方：「创造条件让独立智能体得出不同结论，然后强制进行调和」
- 官方计划：「introducing direct sub-agent communication」（尚未实现）

### 训练防退
- 惩罚"串行崩溃"（教练偷懒全扔给一个Agent）
- 惩罚"虚假并行"（盲目拆无意义子任务）
- 早期训练高权重约束 → 后期降低，专注结果质量

## Claude Code Agent Teams 细节

### 核心差异：Agent间直接通信
- 子Agent可以互相发消息，不经过教练中转
- 「互相证伪对方的理论，像科学辩论一样」
- Plan审核机制：队员提交计划→教练审批→才执行
- 任务依赖链：A完成后B自动解锁

### 限制
- 同一模型换马甲（所有Agent用同一底层模型）
- Lead不能转让，Teammate不能自己spawn子Agent
- 会话恢复时in-process teammate丢失
- 仍在实验阶段（需设置环境变量开启）

## 与 Hermes Agent 对比

| 能力 | Hermes | Kimi Swarm | Claude Teams |
|:---|:---|:---|:---|
| 多Agent并行 | ✅ delegate_task（3并发） | ✅ 300并发 | ✅ 3-5推荐 |
| Agent间直接通信 | ❌ | ❌（计划中） | ✅ |
| 不同模型 | ❌ 全局同一模型 | ❌ | ❌ |
| 持久记忆 | ✅ | ❌ | ❌ |
| 定时自治 | ✅ cronjob | ❌ | ❌ |
| 自定义Skill | ✅ | ✅ | ✅ |

## 核心结论

**没有任何产品真正解决了Agent间的互相约束问题。** 
- Kimi是教练裁决制（中枢判定），Claude Code走得更远（Agent间通信+辩论）但仍是同一模型换马甲。
- 本质瓶颈：生成能力和批判能力在同一模型内冲突，同一个基座模型给不同system prompt产生的分歧远小于预期。
- 需要「真正的多模型对等辩论」架构 — 目前所有工具都是空白。
