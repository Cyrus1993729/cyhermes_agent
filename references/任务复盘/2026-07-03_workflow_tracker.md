# 任务复盘：workflow 追踪机制

- 日期：2026-07-03
- 任务目标：在 sprint-contract skill 中新增流程追踪文件机制，解决 LLM 执行惯性导致 5 步闭环遗漏的问题
- 实际流程：
  1. 用户要求复盘"为什么没走流程" → 发现"涌现型任务"vs"计划型任务"的模式差异
  2. 提出文件追踪方案 → 用户确认 → 执行
  3. 本次改动本身走完整 5 步闭环（可复现）
  4. 千问 L1 三轮审查：FAIL → FAIL → CONDITIONAL(2)，未触发升级
- 踩过的坑：
  - 交付物内联内容不完整导致千问误判（第一轮 FAIL 3 条）
  - Opus 审查两次 hit max-turns（prompt 太长、工具太多）
  - 追踪文件命名不符合契约口径（workflow_tracker → workflow_sprint_contract_tracking）
- 最终结果：SKILL.md 新增章节完成，千问 CONDITIONAL(2) PASS，Opus 三点建议采纳两条、一条因边界约束不采纳
- 可优化点：
  - D4 的自指问题（qwen_review 审查 qwen_review 的输出）本质无解，可以接受
  - Opus 调用无工具模式（--bare）需要 ANTHROPIC_API_KEY，当前不可用
