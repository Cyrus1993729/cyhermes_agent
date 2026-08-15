# Hermes Studio 评估实踩（2026-08-15）

## 背景

用户从小红书帖子（第240集 两个顶级Harness agent,哈工大AI全栈工程师Peter）看到 Hermes Studio 的群聊功能，问"是噱头还是真的能协同，决定要不要下载"。帖子封面 OCR 误读为 "Holmes Studio"，实际为 **Hermes Studio**。

## 仓库身份

- **仓库**: EKKOLearnAI/hermes-studio（10.2k ⭐, 2026-08 更新）
- **本质**: Hermes Agent（NousResearch/hermes-agent）的**第三方 Web 控制台/桌面应用**，非官方
- **安装**: `npm install -g hermes-web-ui && hermes-web-ui start`；有 Windows/macOS/Linux 桌面版、Docker 镜像
- **官网**: hermes-studio.ai
- **技术栈**: TypeScript + Vue3 + Socket.IO + SQLite

## 群聊模块源码判定（噱头 or 真协同 → 真功能）

文件树 `git/trees/main?recursive=1` 共 1769 文件，群聊相关 40+ 变更文档 + 30+ 测试文件 → 重度开发模块。

关键源码路径（packages/server/src/services/hermes/group-chat/）：
- `mention-routing.ts` — @名字/@all 解析，带中英文边界处理（CJK/标点/emoji），防英文单词误触发
- `agent-clients.ts` / `agent-relay.ts` — 执行器类型 `agent: 'hermes' | 'ekko' | 'codex' | 'claude'`，**真实拉起外部 CLI 干活**（Codex CLI、Claude Code），非聊天模拟。这是"真协同"的分水岭证据
- `context-projection.ts` — 多 Agent 独立上下文，他人消息/工具调用以 `[名字]: 内容` 文本注入；工具结果对全员可见
- `handoff-depth.ts` + index.ts 中 gc_handoff_* 表 — 完整交接状态机（chain/attempt/outbox/inbox、重试、租约、幂等），默认深度 4
- 共享工作区：群统一目录，文件 diff 广播全员

**架构本质**：消息总线 + @路由 + 上下文投影 + handoff 状态机。不是"共享大脑"，是务实的多 Agent 平级协作（互相 @、互相交接、共享现场）。

## 对用户的结论（价值判断示范）

- 功能真 ≠ 对用户有用。用户主要做日报/监控/投资分析/内容理解，单 Agent 已闭环；群聊最强场景是"写代码+审查+拍板"的软件协作，用户不做开发
- 用户已有 l1-review 管线（DeepSeek 生成→千问审查），群聊不会改善这条线
- 真正值得装的是 Web UI 本身（成本中心/cron/Kanban/模型管理可视化），非群聊
- 建议：不为群聊装；若好奇可视化面板可评估第三方安全边界

## 产品名确认坑（复用价值高）

- 封面 OCR 读 "Holmes Studio"（错），视频帧内 Codex 自我介绍写 "Hermes Studio"（对），工作目录 `~/.hermes-web-ui/` 佐证
- ASR 听成 "Hermers The Studio" / "Panguei Hardness"（第二个工具，真名 PenguinHarness）
- **判定链：视频帧内 UI 文本 > ASR > 封面**。封面是艺术字/缩略图，OCR 不可信
- 第二个工具 PenguinHarness（V0.2.0）：自进化 AI 开发 Agent，全模型接入（OpenRouter/Kimi K3），成本中心可视化；博主评价"自进化能力甚至比 Hermes 好"

## 技术要点

- 小红书视频 CDN 签名过期（封面 0 字节/视频 150 字节）→ 重取页面刷新签名，立即下载
- ASR 脚本调用：`python "C:\Users\...\whisper_chunk.py" <wav>`（Windows 路径，勿用 ~）
- 抽帧 fps=1/3 得 57 帧；Vision 逐帧确认工具名，比 OCR/ASR 可靠
