# 综合评分手工验证流程

> 来源：2026.7.27 黄金周报——main.py 输出 composite=-0.50，手工加权平均为 -0.540

## 问题

main.py 终端输出中的 composite 值与七因子加权平均可能存在微小差异（-0.50 vs -0.540），导致综合评分偏差（37.6 vs 36.5）。根因：main.py 的文本输出和评分模块可能使用不同精度/四舍五入路径。

## 验证步骤

在每次周报生成后，手工验算：

```python
# 从 main.py 输出中提取各模块评分
scores = {
    'macro': -0.90,      # 宏观环境
    'technical': -1.25,  # 技术趋势
    'sentiment': 0.20,   # 情绪仓位
    'valuation': 0.00,   # 估值水平
    'central_bank': -0.12,  # 央行行为
    'china_domestic': -2.00, # 境内需求
    'geopolitical': 0.32,   # 地缘政治
}

weights = {
    'macro': 0.20, 'technical': 0.15, 'sentiment': 0.10,
    'valuation': 0.15, 'central_bank': 0.20, 'china_domestic': 0.10,
    'geopolitical': 0.10,
}

composite = sum(scores[k] * weights[k] for k in scores)
score_100 = (composite + 2) / 4 * 100

print(f"手工 composite: {composite:.4f}")
print(f"综合评分: {score_100:.1f}/100")
```

若手工 composite 与 main.py 输出偏差 >0.01，以手工值为准写入报告。

## 本案例

```
手工 composite = -0.180 + (-0.188) + 0.020 + 0.000 + (-0.024) + (-0.200) + 0.032 = -0.540
main.py 输出 composite = -0.50
偏差 = 0.040
综合评分：37.6 → 36.5（偏差 1.1 分，在同一评级区间内但影响精度）
```

定投映射边界检查：36.5 < 40 → 仍为暂停，结论不变。若评分在 40 附近（±2 分），此项校验更为关键。
