# Opus → GPT-5.6 Sol 迁移全景（2026-09-01）

## 触发背景
- Claude Code CLI（Opus）账户 2026-08-30 被风控冻结（claude.ai/restricted "Your account is on hold"），判定大概率不恢复（账户级冻结，非凭证问题，判别见 claude-code-troubleshooting skill）
- 用户裁决（2026-09-01）：「所有涉及 Opus 的工作换成 GPT-5.6 Sol」+「原来设计是 opus 和 gpt 双审查的地方，改成 gpt 单审查」
- 即:① 深度审查/分析/sign-off 全部改走 Codex CLI（GPT-5.6 Sol）② 原 L1‖Opus 双审结构简化为 GPT-5.6 单审兜底（L1=qwen3.7-max 快速层保留，L2 仅 GPT-5.6）

## 指定 GPT-5.6 Sol 的 Codex 姿势
```bash
export HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897
# 深度任务（Sol，Plus 配额）:
codex exec -c 'model="gpt-5.6-sol"' --skip-git-repo-check --sandbox read-only < prompt.txt
# 注意: -c 参数风格是 config 键值对, 须带引号; 模型名 gpt-5.6-sol 实测有效(2026-09-01 冒烟 SOL_OK)
```
- 不做深度时用默认模型（省配额）；Plus 官方定位"每周几次聚焦会话"，5h 窗口 Sol 50-500 条（详见 model-subscription-evaluation skill）

## 改动清单（逐文件，回滚用）
| 文件 | 改动 | 备份 |
|---|---|---|
| config.yaml | MoA 段 4 处 `anthropic/claude-opus-4.8`@nous → `deepseek-v4-pro`@opencode-go（presets.default + 顶层 aggregator/reference 兜底） | config.yaml.bak_opus2gpt_20260901_130317 |
| cron/jobs.json | 跨境日报 prompt 文案「Opus 设计」→「资深 AI 设计」（仅文案,非活调用） | jobs.json.bak_opus2gpt_* |
| scripts/daily_report_review.py | codex subprocess 加 `"-c", 'model="gpt-5.6-sol"'`（ad-hoc 验证 PASS: 静态断言+真实调用返回 findings dict） | 无（改动小,git-less） |
| skills/productivity/l1-review | L2 升级目标 Opus → GPT-5.6 Sol；双审→单审说明入 description | — |
| skills/productivity/task-wrapup | 控制流 L1‖Opus 并行 → L1 先行 + GPT-5.6 Sol 单审兜底 | — |
| skills/productivity/sprint-contract | 27 处 Opus → GPT-5.6 Sol（python 批量替换,含 codex 姿势） | — |
| skills/autonomous-ai-agents/claude-code-workflow | 顶部停用横幅（解冻恢复路径指引） | — |
| skills/autonomous-ai-agents/opus-deep-thinking | 顶部停用横幅（编排结构可复用,Opus 调用换 codex） | — |
| skills/autonomous-ai-agents/codex-cli | 触发段加「深度审查默认通道 + Sol 指定」 | — |
| skills/autonomous-ai-agents/agent-mesh-networking | design-review 活引用 Opus → GPT-5.6 Sol | — |
| skills/autonomous-ai-agents/multi-agent-collaboration | claude CLI 坑句 → 停用标注 + codex 姿势 | — |
| skills/devops/local-service-deployment / self-hosted-deployment | 契约/方案审查 Opus → GPT-5.6 Sol（codex exec 姿势） | — |

**刻意保留不动**：历史 provenance 标注（"2026-08-07 Opus 评审确立/确认"这类来源记录）与 references/ 文件名——它们描述过去发生了什么，替换会歪曲记录；未来排查"为什么这里写 Opus"时按本文件对照。

## 恢复路径（若账户意外解冻）
1. `claude auth status --text` → 确认非 Expired/on hold
2. 恢复 claude-code-workflow / opus-deep-thinking（删停用横幅）
3. 恢复审查链前先用户确认（用户已拍板单审,⚠️ 不要自动改回双审）
4. config MoA 回滚用备份文件

## 教训
- 审查模型选择（双审→单审、Opus→GPT）属用户裁决, 迁移前先确认范围（"所有涉及 Opus 的工作"≠只改 cron prompt——还包括 MoA 兜底、部署类 skill 的活调用姿势、文案）
- 旗舰模型冻结 ≠ 全部审查能力丢失：Codex（GPT-5.6）承接后 cheaper 路径（qwen3.7-max 经 opencode 网关 $60 配 0.2%）保持 L1 机械核对独立