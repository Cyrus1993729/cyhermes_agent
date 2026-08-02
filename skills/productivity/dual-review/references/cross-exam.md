# 交叉质证 Prompt

你收到另一个审查模型对同一交付物的一条发现。独立判断是否成立。

## 输出

```json
{
  "position": "confirm|reject|partially_confirm|cannot_verify",
  "reason": "一句话理由",
  "evidence_refs": [],
  "severity_assessment": "critical|high|medium|low",
  "alternative_interpretation": null
}
```

- confirm：成立，你认同
- reject：不成立，给反证
- partially_confirm：部分成立
- cannot_verify：无法判断
