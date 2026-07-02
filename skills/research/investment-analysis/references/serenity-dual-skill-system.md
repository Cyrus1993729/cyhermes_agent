# Serenity 双 Skill 体系：产业链卡点 + 估值增强

## 架构

两个 Claude Code skill 并列在 `~/.claude/skills/`，Claude Code 自动叠加加载：

```
~/.claude/skills/
├── serenity-skill/SKILL.md    ← 原版（GitHub 安装，不修改）
└── serenity-value/SKILL.md    ← 用户自定义 overlay（估值增强）
```

## serenity-skill（基础版）

- **来源**：GitHub 第三方 skill，供应链瓶颈猎人
- **核心**：9 步工作流 — 市场叙事 → 系统变化 → 产业链 → 稀缺层 → 公司池 → 证据 → 排名 → 风险 → 下一步
- **能力**：A股/港股/美股/台日韩欧，多市场信源，证据分级
- **定位**：找到"卡脖子环节"中控制稀缺层的公司

## serenity-value（估值 overlay）

- **来源**：用户自建（2026-06-15 创建，2026-06-23 重建）
- **核心**：在 serenity 工作流中插入三个估值判断点
- **不修改原 skill** — 完全独立文件，叠加生效

### 三个插桩点

| 插入点 | 时机 | 动作 |
|--------|------|------|
| ① 第5步后 | 公司池建成，排名前 | 逐家查股价 + P/E + 3年区间 + 行业中位数，标「偏贵/合理/便宜」；周期股走正常化盈利 P/E |
| ② 第7步中 | 排名阶段 | 强卡脖子+便宜→升档；强卡脖子+飞天→降档；中卡脖子+地板价→标注反直觉机会 |
| ③ 第9步中 | 输出阶段 | 每个标的加 `📊 卡脖子强度 · 估值水位 · 综合吸引力 ★★★★★` |

### 周期股特殊处理

强周期行业（半导体设备/化工/航运/钢铁/有色冶炼）不直接用 P/E (TTM)：
- 优先用正常化盈利 P/E（3-5 年均值）
- 辅助 P/B（周期底部更可靠）
- 辅助 PEG（有增长预期的周期股）
- 对比标普 500 P/E 作为宏观水位锚

### 范围锚定规则（防漂移）⚠️ v1.1.0 重大升级（2026-06-23）

**问题根因**：serenity-skill L155-157 有一个具体的正向示例——"A股 AI 半导体 → 先看内存互连、CMP、刻蚀、耗材"。这是**粉色大象效应**（pink-elephant problem）：抽象禁令（"禁止存储"）打不过具体示例（"先看内存互连"）。LLM 处理"禁止"一词后，"存储"反而被激活。

**初版方案（v1.0.0）失败**：三条抽象规则（市场锁定、产业链锁定、用户指令优先）+ 检查机制，连续两次跑偏到美股存储链。**具体示例永远碾压抽象禁令。**

**v1.1.0 三件套修复（2026-06-23，经 Claude Opus 诊断确认）：**

| 层级 | 修复 | 原理 |
|------|------|------|
| ① 正向具体开场白 | 在 overlay 中预置 A 股 AI 半导体的具体标的链：寒武纪→海光→中微→沪硅→通富微电→中际旭创。**用具体替代具体，而非用抽象禁止具体。** | LLM 看到正向路标后，从正确方向起步 |
| ② 显式作废 L155-157 | 在 overlay 中**点名**作废：「serenity-skill/SKILL.md 第 155-157 行在本 overlay 下作废」 | 给 LLM 明确裁决——不用在两条规则间自己权衡 |
| ③ 条件触发硬护栏 | 关键词拦截**仅在用户明确排除时触发**（用户说排除存储→拦截 HBM/Micron；用户说研究存储→放行）。铁律：不替用户做排除决定。 | 硬约束不靠 prompt 说服，靠代码强制；且不误伤未来需求 |

**Claude Opus 诊断摘要**（2026-06-23，见本会话）：根因是"两个并列 skill 之间没有优先级裁决层 + 抽象禁令打不过具体示例（salience bias/pink-elephant problem）"。推荐不改基底 skill（职责错位），在 overlay 层用 ①+②+⑥ 三件套解决。⑥ 指 LLM 之外的 post-filter，本方案已通过 ③ 的条件触发护栏实现。

**最终 prompt 模板（v1.1.0 后极简版）**：用户不需要写硬约束和排除项。只需要：

```
用 serenity-value 深度调研 {A股/美股/港股} {产业链}，找 5 个最值得优先研究的标的。
```

排除项选填——不填时 skill 自带护栏判断方向。如果用户指定了排除项，硬护栏条件触发。

## 使用方式

### Prompt 模板

**极简版（推荐，v1.1.0 起可用）**：serenity-value 已内置方向判断和护栏，用户只需填市场和产业链：

```
用 serenity-value 深度调研 {A股/美股/港股} {产业链}，找 5 个最值得优先研究的标的。
```

排除项选填——不熟悉行业时不要硬写。不知道会往哪跑偏，就别写排除项。skill 内 ①+②+③ 会自动处理方向。

**完整模板文件**（含填写示例）：`~/.claude/skills/serenity-value/assets/prompt-template.md`

四个填写参数：`{市场}`、`{产业链}`、`{标的数}`、`{排除项}`（选填）。

### Claude Code 调用命令

```bash
# Windows（MSYS bash）注意：/tmp 不解析，用 /c/tmp 或 pipe 模式
# 方式 A：pipe（推荐，避免路径问题）
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
cat /c/tmp/serenity-prompt.txt | claude --model opus --max-turns 30 \
  --allowedTools "Read,WebSearch,WebFetch,Bash" \
  --output-format text --verbose 2>&1

# 方式 B：-p 注入（需确认路径正确）
claude -p "$(cat /c/tmp/serenity-prompt.txt)" --model opus --max-turns 30 \
  --allowedTools "Read,WebSearch,WebFetch,Bash" \
  --output-format text --verbose 2>&1
```

**常见错误**：
- `cat: /tmp/...: No such file or directory` → Windows MSYS 下 `/tmp` 不解析，改用 `/c/tmp/`
- `Error: Reached max turns (5)` → 纯分析任务也需要 ≥10 轮（模型可能先思考后执行）
- 两次跑偏结果一样 → 不是 prompt 问题，是 skill 内部示例覆盖了用户指令（见上方粉色大象效应）

### 重要参数说明

- `--model opus`：深度研究必须 Opus（L3 级别任务）
- `--max-turns 30`：≥25 个信源 + ≥20 家公司池需要足够轮次
- `--allowedTools "Read,WebSearch,WebFetch,Bash"`：禁止 Write/Edit，纯研究模式
- `--verbose`：可以看到逐轮进度
- 后台运行 + `notify_on_complete=true`：5-10 分钟不等，完成后自动通知
- 先写 `/tmp/serenity-prompt.txt` 再 `cat`：避免中文 shell 引号问题

## 恢复记录

- **2026-06-15**：首次创建 serenity-value，基于存储产业链研究验证
- **2026-06-22 前后**：系统升级/环境变更，文件丢失
- **2026-06-23**：重建 serenity-value（从对话恢复），写入 `~/.claude/skills/serenity-value/SKILL.md` + `assets/prompt-template.md`
  - **v1.0.0 初版**：三条抽象规则（范围锚定）— **失败**：连续两次跑偏到美股存储链
  - **v1.1.0 升级**：经 Claude Opus 诊断后实施 ① 正向具体开场白 + ② 显式作废 L155-157 + ③ 条件触发硬护栏。第三次运行成功产出全 A 股 AI 算力产业链报告
  - **关键教训**：抽象禁令打不过具体示例（粉色大象效应）。修复方法是用具体打具体，而非加更多禁止词
  - **条件护栏 bug 修**：初版关键词拦截无条件触发（用户说"研究存储"也会被拦）。修复为条件触发——仅在用户明确排除某类别时拦截
  - **Prompt 模板简化**：v1.1.0 后用户不需要写排除项，skill 自身处理方向判断
  - **文件路径注意**：Windows 上 `/tmp` 在 MSYS bash 中不解析，prompt 文件需写 `/c/tmp/` 或用 pipe 模式（`cat file | claude`）

### 恢复方法

当 overlay skill 丢失时：
1. 用 `session_search(query="serenity-value")` 找回原始设计对话
2. 从对话中提取用户的三插桩点设计 + 周期股补丁 + 范围锚定规则
3. 对照 `serenity-skill/SKILL.md` 确认插桩点对齐
4. 重写完整 SKILL.md 到 `~/.claude/skills/serenity-value/SKILL.md`
5. 恢复 `assets/prompt-template.md`

## 相关文件

- `~/.claude/skills/serenity-skill/SKILL.md` — 原版基础 skill
- `~/.claude/skills/serenity-value/SKILL.md` — 估值 overlay
- `claude-research-to-png.md`（同目录）— 研究结果渲染为 PNG 长图的工作流
- Hermes skill `autonomous-ai-agents/claude-code` pitfall #16 — 不修改上游 skill 的铁律
