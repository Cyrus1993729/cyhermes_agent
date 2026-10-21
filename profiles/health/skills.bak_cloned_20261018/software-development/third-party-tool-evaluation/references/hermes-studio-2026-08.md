# Hermes Studio 群聊评估案例（2026-08-15）

## 背景
小红书「第240集 两个顶级Harness agent」推荐 Hermes Studio（群聊式多 Agent 工具，称可同时挂 Codex/Claude Code/DeepSeek、邀请真人进群）。用户考虑是否下载。最终结论：**不装**。

## 功能路径核查（源码级，非 README 宣传）
- 仓库真实存在：EKKOLearnAI/hermes-studio，10.2k stars，第三方（非 Nous Research 官方），npm 包 hermes-web-ui
- 群聊机制 = @路由 + 上下文投影 + handoff 状态机 + 共享工作区：
  - mention-routing.ts：@名字/@all 解析，带边界检测防误触发
  - agent-clients.ts：执行器类型 hermes/ekko/codex/claude（@ 即拉起真实 CLI）
  - context-projection.ts：他人发言/工具结果以 `[名字]: 内容` 注入对方上下文
  - handoff-depth.ts + index.ts：完整状态机（chain/attempt/outbox/inbox/重试/租约，默认深度 4）
- 30+ 测试文件、40+ 变更文档（**数量≠质量，是弱证据**）

## 信任边界核查（Opus 要求补查后才发现）
- `BIND_HOST` 默认 `0.0.0.0`（监听所有网卡，非 127.0.0.1）——Opus 的 RCE 担忧被证实且更实
- 默认账号 admin/123456（README 明示，登录后提示改）
- 有 JWT 认证（30d）、CSP/CORS 安全头，但需主动配置
- 五属性叠加：第三方 + 持全部 API key + 真实命令权限 + Web 控制台 + 邀请码 = 潜在 RCE 结构

## Opus 评审要点（独立视角，不附和）
1. 群聊本质 = 人在环里的串行接力，非多 Agent 自主协同；AutoGen GroupChat/CrewAI/Swarm 一脉标准做法，营销夸大一个量级
2. 四局限：上下文投影有损（架构性）/ token≈N 倍 / @路由=人当调度器 / 并发写冲突（Hermes 漏查）
3. 唯一强场景：投资实时对辩（对话本身就是共享状态，投影损耗近零）——与用户「双视角 sign-off」习惯严丝合缝
4. 修正 Hermes：「群聊不会让审查管线变好」过头——可观测性+可插话是真实增量，但 Telegram 推中间输出可替代八成
5. 自省金句：「我通过另一个 Agent 的文本投影评估我看不到的源码——这正是上下文投影≠共享状态的证明，你需要的不是更多 Agent 意见，而是一次亲自验证」

## Hermes 被说服/修正点
- 「群聊不会让审查管线变好」→ 认，修正为「增量真实但替代路径成立」
- 漏查并发写冲突、把测试文件数量当质量证据 → 认
- 反驳 Opus 一处：Opus 无联网权限无法核实仓库，Hermes 已用 GitHub API 核实（但 star 可刷担忧仍成立）

## 最终建议（双视角一致）
1. 不下载
2. 零成本验证：Hermes 把 DeepSeek→千问→审查管线每环中间输出推 Telegram，用户手动插话两周
   - 几乎每次都想打断追问 → 需求真实，再考虑装（带验收标准）
   - 基本只看终稿 → 需求是假的，省一次风险暴露
3. 若真装：隔离环境 + 额度上限子 key + 禁邀请 + BIND_HOST=127.0.0.1 + 空工作目录 + 先只跑 Web UI 两周
