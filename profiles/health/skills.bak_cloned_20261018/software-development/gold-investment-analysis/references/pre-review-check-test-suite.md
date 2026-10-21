# pre_review_check 测试套件

位置: `scripts/test_pre_review_gate.py`
Fixtures: `scripts/fixtures/`

## 4 个测试用例

| Fixture | 场景 | 期望 exit | 关键字断言 |
|:--|:--|:--|:--|
| `clean_passing.md` | 合规交付物 | 0 | "闸门通过" |
| `bad_wrong_mapping.md` | 评分<40→30%（应暂停） | 1 | "定投映射" |
| `bad_wrong_threshold.md` | D4.4 ±10%→±5% | 1 | "D4.4" |
| `bad_amplitude_mismatch.md` | $4,200 超出振幅 $3,900-$4,000 | 1 | "振幅" |

## 运行

```
python scripts/test_pre_review_gate.py
```

## 设计原则

- 每次修改 `pre_review_check.py` 后必须跑回归测试
- 不仅要断言 exit code，还要断言 stdout 中的阻断关键字
  （防止"对结果错原因"的巧合通过——如 D4 阈值抓错列但仍误打误撞 exit 1）
- 合规用例（clean_passing.md）验证闸门不会误杀正常产出
- 修改闸门逻辑后应增补对应 fixture

## 已知缺陷（已修复）

- 2026.7.27: D4 阈值正则抓到数据列（-6.0%）而非判定列（±10%），合规交付物被误杀。
  修复: 正则显式跳到第4列 + ±≤标准化比较。
- 2026.7.27: 定投非暂停档只 WARN 不 BLOCK，私改 50%→75% 可漏过。
  修复: 升级为 BLOCK，匹配时容忍整数/N/100 格式变体。
