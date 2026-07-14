---
name: task-wrapup
description: "【收尾自检清单】所有干活类 skill（产出分析报告/文件/方案的）最后一步强制引用。自动触发审查、区分来源、存档产物、平台分段交付。不等用户喊「审」。"
version: 1.3.0
platforms: [windows]
metadata:
  hermes:
    tags: [wrapup, review, delivery, workflow]
---

# 收尾自检清单

所有产出交付物的任务，在交付前必须逐条过这个清单。**不可跳过。**

## ⚠️ 硬触发

任何干活类 skill 的**最后一步**必须写：

> 执行收尾自检 → 见 `task-wrapup` skill

这不是建议，是 SOP 结构的一部分。审查不靠人喊，焊死在流程里。

### ℹ️ 微信 iLink 限流（2026.7.3 实战，历史记录）

> ⚠️ 2026.7.4 主通信平台已迁移到 Telegram。Telegram Bot API 无类似频率限制碰撞问题，收尾阶段可放心发送多条消息。以下保留微信时代的故障分析作为历史参考。
>
> **问题**：task-wrapup 执行期间会产生多条微信消息，短时间密集推送可能触发 iLink 限流，后续消息被延迟最多数分钟。
>
> **缓解（旧平台时代）**：收尾阶段消息控制在 3 条以内；连续消息间隔至少 3 秒。
>
> **反例（2026.7.3）**：workflow 追踪机制改 skill 任务中触发限流 → 22:26~22:35 九分钟消息中断。

**问题：** 任务经历多轮反复修改后，Agent 会产生"终于对了，收工"的执行惯性，遗忘之前约定的完整流程（审查→存档→复盘）。Agent 自己无法可靠地克服这个惯性——在"完成"的满足感中停不下来。

**解决：用户哨兵，双触发词。** 流程断成两段，两个触发词各管各的：
- 用户说 **"走流程"** → sprint-contract + decision-gate + 执行
- 用户说 **"收尾"** → task-wrapup + post-task-review

"收尾"是最终保险——即使用户忘了在开头喊"走流程"，最后喊一声"收尾"仍然可以触发审查+存档+复盘闭环，只是缺了契约文件。

**反例（2026.7.3）：** 微信限流修复任务中，Agent 在 Opus 审查 + 千问审查后停了下来，但没有执行 task-wrapup 的步骤 4（产物存档）和步骤 5（分段交付），也没有触发 post-task-review 复盘。用户不得不主动问"复盘一下原因"。

## ⚠️ 长任务不沉默

任务执行中遇到耗时步骤（ASR、视频下载、后台大模型调用等），**不能沉默等结果**。必须：
- 开始前告知：「正在做 X，预计需要 Y 秒」
- 等待中主动 poll 进度
- 超过 60 秒无进展 → 主动汇报当前状态

> 本 session 实踩 2 次：ASR 跑 180 秒期间沉默、AgentBay 报告中连续发送后沉默。用户两次追问「进展呢」。

---

## 控制流（⚠️ 短路逻辑 + 自动审查循环）

自检分两段，中间有自动循环：

```
┌─ 质量门 ──────────────────────────────────────┐
│ 1. 步骤完整性                                  │
│ 2. 来源区分                                    │
│ 3. 自动审查（L1 → Opus）                       │
│    ├── PASS → 进入 Opus（若有）→ PASS → 投递   │
│    ├── FAIL/CONDITIONAL → 自动修复 → 重审      │
│    │    ├── L1 层最多 3 轮（含 CONDITIONAL）   │
│    │    │   ├── 3轮内 PASS → 进入 Opus 层      │
│    │    │   └── 第4轮启动前 → 停下，通知用户   │
│    │    ├── Opus 层最多 3 轮（独立计数）        │
│    │    │   ├── 3轮内 PASS → 进入投递          │
│    │    │   └── 第4轮启动前 → 停下，通知用户   │
│    │    └── 全程 Agent 自动修复，不询问用户     │
└──────────────────────────────────────────────┘
         ↓ (L1 + Opus 全部通过后才走)
┌─ 投递动作 ───────────────────┐
│ 4. 产物存档（含失败留痕）     │
│ 5. 将交付物作为回复正文发送   │
└──────────────────────────────┘
```

**任一质量门不过 → 不进入投递。**
审查循环全程自动——Agent 发现问题后自己修、重审，不打断用户。仅当同一层连续 3 轮未 PASS 时才停下（详见 sprint-contract v1.2 升级规则）。

---

## 质量门（不过不进投递）

### ✅ 1. 步骤完整性

**执行方式**：列出本次所用 skill SOP 的关键步骤名，逐条对照是否已执行。

```
1. 本次所用 skill：________
2. 该 skill SOP 关键步骤：
   - [ ] 步骤A：________
   - [ ] 步骤B：________
   - [ ] ...
3. 逐条判定：已执行 ✓ / 跳过 ⚠️ / 未执行 ✗
```

示例（小红书视频帖）：
- [✓] 密度判定
- [✓] 信号评估
- [✓] 首遍填槽
- [✓] 缺口判断

> 不硬编码特定 skill 的步骤。Agent 需从本次所用 skill 的 SOP 中提取关键步骤名填入。

**输出**：`步骤完整 ✅` 或 `跳过 X 步骤 ⚠️ → 补充执行`

### ✅ 2. 来源区分

**在审查之前做**——审查要检查的就是来源是否清晰。

检查交付物中的关键论断，按三类标注：

| 类型 | 标注方式 | 示例 |
|:---|:---|:---|
| **一手事实** | 说明来源（如「来自帖子 desc」「来自 GitHub README」） | 「PlanWeave 描述为 file-backed loop engineering system」 |
| **外部数据** | 必须附 URL 或明确出处 | 「12 stars（GitHub API，2026-07-03）」 |
| **推断/建议** | 标注「（推断）」 | 「💡 建议（推断）：cronjob 内维护状态 JSON」 |

**原则**：读者能一眼分清「哪句是事实」「哪句是我说的」「哪句来自外部」。报告中已有「来源说明」段落概括的，不逐句贴链接。关键数字和可操作结论必须有出处。

**输出**：`来源清晰 ✅` 或 `未标注 X 处 ⚠️ → 补充标注`

### ✅ 3. 自动审查（不等用户喊，全程自动修复）

**审查循环规则**（详见 sprint-contract v1.2 升级规则）：
- L1 发现问题 → Agent 自动修复 → 重审 → 循环至 PASS（最多 3 轮）
- L1 PASS 后 → 发 Opus 审查（投资分析类强制，其他类可选）
- Opus 发现问题 → Agent 自动修复 → 重审 → 循环至 PASS（最多 3 轮，独立计数）
- Agent 全程**不询问用户**是否修复或升级，自动修复+重审
- 仅当同一审查层第 4 轮启动前（即 3 轮未 PASS）才停下询问用户
- CONDITIONAL 算审查轮次，修完必须重审

**路径规则**：
- 契约文件：`~/AppData/Local/hermes/contracts/contract_<任务名>_<YYYY-MM-DD>.md`
- 交付物文件：`~/AppData/Local/hermes/output/<任务名>_<YYYY-MM-DD>.md`
- 审查脚本：`~/AppData/Local/hermes/scripts/qwen_review.py`

L1 审查步骤：
```
1. 定位契约文件路径
2. 定位交付物文件路径
3. 运行 python <审查脚本> --contract <契约> --deliverable <交付物>
4. 若脚本超时（API不可达）→ 降级为人工自检（见 L8 规则）
5. PASS → 进入 Opus 审查（若需要）
6. FAIL/CONDITIONAL → 自动修复 → 回到步骤 3 重审
7. 累计 3 轮未 PASS → 停下告知用户（第 4 轮不启动）
```

Opus 审查步骤（投资分析类强制，见 sprint-contract）：
```
8. 用 claude -p --model opus 审查交付物
9. PASS → 进入投递
10. FAIL/CONDITIONAL → 自动修复 → 回到步骤 8 重审
11. 累计 3 轮未 PASS → 停下告知用户
```

**输出**：`审查 ✅ L1 PASS (N/N) + Opus PASS` 或 `审查 ⚠️ CONDITIONAL（已修N轮）` 或 `审查 ❌ FAIL（已重试3轮，停下）`

> ⚠️ PASS 后的 N/N **必须从审查脚本实际输出中抄录**，不得凭印象填写。

---

## 投递动作（质量门全过后才执行）

### ✅ 4. 产物存档（含失败留痕）

**无论成功还是失败，都记一行。** 失败也是信息。

1. 目录：`~/hermes_output/`（不存在时自动创建）
2. 文件命名：`<YYYY-MM-DD>_<任务名>.md`（中文用英文替代，空格用下划线）
3. 在 `~/hermes_output/index.md` 追加一行：

```
| 日期 | 任务 | 文件 | 审查结论 |
|:---|:---|:---|:---|
```

示例：
```
| 2026-07-03 | planweave_xhs_analysis | 2026-07-03_planweave_xhs_analysis.md | PASS |
| 2026-07-03 | task_wrapup_skill | 2026-07-03_task_wrapup_skill.md | FAIL(2次) |
```

> **失败不留产物的任务**（审查卡住、无产出文件）：仅追加 index 行，文件列填 `无`，审查结论列写卡在哪。

**输出**：`已存档 ✅ → ~/hermes_output/<文件名>` 或 `无产物，已记失败 ✅`

4a. **归档 contract + deliverable 到 archive/**

在 L1 审查 PASS 后（或 CONDITIONAL 呈报后），立即执行：

```bash
cd hermes/contracts
mkdir -p archive/<任务名>_<YYYY-MM-DD>
mv contract_<任务名>_<YYYY-MM-DD>.md archive/<任务名>_<YYYY-MM-DD>/
mv deliverable_<任务名>_<YYYY-MM-DD>.md archive/<任务名>_<YYYY-MM-DD>/
```

> **文件治理规则**（详见 `hermes/contracts/file_governance_standard.md`）：
> - 归档 ≠ 删除——contract 和 deliverable 完整保留在 archive/ 下
> - 仅 workflow 追踪文件在 ⑤ post-task-review 后删除
> - 本次治理任务前若有未归档的历史文件，一并归位

**输出**：`已归档 ✅ → contracts/archive/<任务名>_<日期>/`

### ✅ 5. 将交付物作为回复正文发送

**⚠️ 硬性规则**：最终交付物必须作为回复正文发送给用户，不可仅说"已存到文件"或只贴文件路径。用户应在对话中直接看到完整报告。

**⚠️ 平台差异：**
- **Telegram（主平台）**：单条消息 ~3500 字合理上限，Markdown 渲染良好，无回复条数限制。超长自动分段。
- **微信（iLink，备用）**：单条消息 ~1500 字硬限制，每轮仅 10 条回复额度。仅在 Telegram 不可用时回退。

**ℹ️ 历史记录**：2026.7.4 主通信平台已从微信迁移到 Telegram。微信时代的 1500 字限制、iLink 10 条额度、投递三难困境等问题不再适用。历史分析见 [`references/wechat-delivery-trilemma.md`](references/wechat-delivery-trilemma.md)。

**用户偏好：** 在 Telegram 中阅读，可接受 MEDIA 文件和 Markdown 格式。

**交付规则（分离管理消息与正文，每条独立可读）：**

**原则**：管理型消息（MEDIA 文件、自检摘要）和分析型内容（报告正文）拆成**三条独立回复**，每条都是自足消息。顺序打乱或某条丢失，其余条仍可独立阅读。

**⚠️ 任务边界清晰（2026.7.3 实战教训）**：不要在收尾/进度汇报消息的末尾顺便启动下一个任务。规则：**一个回复只做一个任务的事**。

**回复 #1 — 分析报告正文**
1. ≤3500 字（Telegram 主平台）→ 一条回复发完整报告
2. >3500 字 → 拆成 N 段（按逻辑段落切分），每段标 `（1/N）` 序号
3. 关键结论放前 2 段
4. 微信备用：阈值降至 ~1500 字

**回复 #2 — MEDIA 文件（独立回复）**
- 单独一条，仅含 `MEDIA:/path/to/file`，不加其他文字

**回复 #3 — 收尾自检摘要（独立回复）**
- 单独一条，模板见下方「收尾自检报告模板」

**输出**：`已交付 ✅ 报告(N段) + MEDIA + 自检` 或 `≤3500字，已交付 ✅ 报告 + MEDIA + 自检`

> 若用户反馈「没收到完整报告」→ 立即重发缺失部分

### ⚠️ Pitfall：只存档文件路径，没把正文发给用户（2026.7.13 黄金周报实踩）

Agent 完成审查+存档后回复："报告已存档至 hermes_output/2026-07-13_gold_weekly.md"——但没有发报告正文。用户追问："最终版的周报你没有发给我呀。"

**根因**：Agent 误以为"指个路径就够了"，但用户要在对话中直接看到完整内容。存档是备份，正文才是交付。

**正确做法**：存档后必须把交付物全文作为回复发送。`read_file` 读取文件内容 → 作为回复正文逐段发出。

---

## 收尾自检报告模板

全部过完后，向用户输出简短摘要：

```
🔍 收尾自检：
✅ 步骤完整
✅ 来源已区分
✅ 审查 PASS/CONDITIONAL（N/N）
✅ 已存档 → hermes_output/YYYY-MM-DD_xxx.md
✅ 已分段发送（N段）
```

有未完项时标注状态和后续行动。有 FAIL 时写清卡在哪。

---

## 和 sprint-contract / l1-review 的分工

| skill | 管什么 | 什么时候触发 |
|:---|:---|:---|
| `sprint-contract` | 开头：定义「做到什么算完」 | 任务开始 |
| `l1-review` | 审查：千问逐条审交付物 | task-wrapup 第 3 步调用 |
| **`task-wrapup`** | **收尾：打包上述所有收尾动作** | 任何干活类 skill 的末步 |

`l1-review` 是刀刃，`task-wrapup` 是刀柄——握着它把所有收尾动作一起完成。

---

## 其他 skill 如何引用

在干活类 skill 的末步写：

```markdown
## Step N（强制，不可跳过）: 收尾自检
执行收尾自检 → 见 `task-wrapup` skill
```

`xiaohongshu-analysis` 已做示范（见该 skill 末尾）。

---

## 验证

- [ ] 创建后，跑一次真实任务验证全流程
- [ ] 确认其他 skill 引用格式正确
- [ ] 确认短路逻辑生效（模拟一次 FAIL 看是否阻止投递）

## 参考

- **文件治理规范**：`走流程` 产生的所有文件（contract/deliverable/workflow）的命名、生命周期、归档规则。详见 `hermes/contracts/file_governance_standard.md`。
- **Cron 自治 5 步闭环适配**：交互式「走流程」适配为 cron 无人值守执行的完整模式（decision-gate→自检闸门、task-wrapup→嵌入 prompt）。详见 [`references/cron-5step-autonomous-adaptation.md`](references/cron-5step-autonomous-adaptation.md)。
- **Cron no_agent 脚本格式**：no_agent 模式用 Python 执行脚本（非 bash/cmd）。`.py` 可用，`.sh`/`.bat` 不可用。详见 [`references/cron-no-agent-script-format.md`](references/cron-no-agent-script-format.md)。
