# 审查契约 — Hermes 备份方案

## 任务
提出 Hermes Agent 数据备份方案，避免换电脑/硬盘损坏导致全部沉淀丢失。

## 验收标准
1. 方案覆盖所有核心资产（memory/skills/scripts/config/reviews/lessons等）
2. 有明确的备份方式（Git + cron）
3. 有排除清单（cache/logs/auth等不进git）
4. 有恢复流程（换电脑后如何还原）
5. 未自动执行——先出方案等用户确认
