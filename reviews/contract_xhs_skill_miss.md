# 审查契约 — 小红书链接分析未调用skill复盘

## 事件
用户发来 xhslink.com 链接要求分析，Agent 尝试了 browser_navigate(2次失败)、curl 提取 __INITIAL_STATE__(3次)、execute_code 多轮抓取，直到用户提醒"调用我们的小红书理解skill做啊？你怎么忘了？"才走 xiaohongshu-analysis skill 流程。

## 验收标准
1. 根因是否准确定位
2. 是否有可执行的改进措施
3. 是否提炼为可写入 lessons.md 的规则
