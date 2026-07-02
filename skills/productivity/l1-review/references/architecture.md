# 审查系统架构与脚本清单

## 文件结构
```
hermes/
├── scripts/
│   ├── qwen_review.py    # L1 审查引擎（千问3.7Max，直连API）
│   ├── mem_gc.py          # 记忆时效扫描器（四类标记）
│   └── review_trend.py    # 纵向评估趋势查看器
├── reviews/
│   └── review_log.jsonl   # 自动累积的审查记录
└── skills/productivity/
    ├── l1-review/SKILL.md      # L1 审查调用指南
    └── sprint-contract/SKILL.md # 任务契约模板
```

## qwen_review.py 核心机制
- 从 config.yaml 动态读 qwen-bailian 的 api_key 和 base_url，不硬编码
- 审查 prompt（RUBRIC）固化三维度：完成度/论证质量/风险合规
- **裁决不信任 LLM 自报**：从 items 数组确定性重算 verdict + escalate
- 每次运行自动写 review_log.jsonl（纵向评估数据源）
- 网络异常兜底：HTTPError/URLError/JSONDecodeError 均 exit(2)

## 踩过的坑
1. **`\\d` 双反斜杠 bug**：正则写成了字面反斜杠+d，导致日期匹配完全失效。修复为单 `\d`。
2. **escalate 信任 LLM 自评**：最初直接读 JSON 里的 verdict/escalate 字段，等于让生成者评自己（self-completion bias）。改为代码从 items 重算。
3. **delegate_task 不能指定 provider**：尝试用 delegate_task 调 qwen 失败，因为子代理继承父模型。改为 execute_code 直连 API。
4. **"过程质量"措辞矛盾**：审查原则是"审交付物不审过程"，但维度名叫"过程质量"，读着别扭。改为"论证质量"。
5. **memory 条目用 `§` 分隔**：mem_gc.py 需要按 `§` 行切分，不能用空行或其他分隔符。
