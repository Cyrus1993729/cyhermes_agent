# 接地校验规则

## 三模式

| type | 适用 | 校验 | 失败处置 |
|---|---|---|---|
| present_text | "这里写错了" | quote精确匹配+模糊匹配（去空格、标点归一化） | ungrounded |
| omission | "这里该有但没有" | expected_from.ref指向的契约存在 | ungrounded |
| external_evidence | "外部数据证明" | 源可访问+版本明确 | ungrounded |

## ungrounded 处置

- 不改变原始 severity，仅将 confidence 降为 low
- high/critical 级 → 人工复核旁路
- medium/low → 记录放行
- type 为空 → 降为 low
