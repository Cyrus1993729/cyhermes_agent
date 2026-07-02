# Q7 — Memory 作为引擎

## 交付项
1. 每周 Memory 体检 cron job：mem_gc.py 每周一 10:00 自动扫描 MEMORY.md/USER.md，标记 STALE/VOLATILE/SUPERSEDED/DUP，发微信给用户审核
2. 矛盾检测记忆规则：Agent 发现 memory 与现实矛盾时主动提醒用户

## 验收标准
1. cron job 已创建，next_run_at 正确
2. 矛盾检测规则已写入记忆且格式正确
3. 用户确认两项均无需修改
