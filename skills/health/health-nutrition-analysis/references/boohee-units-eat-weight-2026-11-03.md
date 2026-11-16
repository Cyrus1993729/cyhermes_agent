# 薄荷 units 的 weight vs eat_weight + code 真伪判定（2026-11-03）

> 起因：早餐报「1 根香蕉」，健康助理用了 `xiangjiao` 的 **88.5 g（eat_weight）**，
> 并在档案里指出「薄荷那行标的 139.5 卡是按毛重 150 g 算的」。复核证明它是对的。

## 一、🔴 带皮/带壳类：`weight` 与 `eat_weight` 必须分清

`public_detail("xiangjiao")` 实测 units：

```
大根: weight 210.0 / eat_weight 123.9 / calory 195.3
小根: weight 110.0 / eat_weight  64.9 / calory 102.3
根  : weight 150.0 / eat_weight  88.5 / calory 139.5
```

`units[].calory` 是**按 weight（毛重）算的**，不是他能吃到嘴里的量。
每 100 g 值：93 kcal / 蛋白 1.4 / 脂肪 0.2 / 碳水 22.0 / 纤维 1.2 / 钠 0.8 / 钙 7。

| 算法 | 结果 |
|---|---:|
| 套 units.calory（按毛重 150 g） | **139.5 卡** ❌ 多算 57 卡 |
| 按 eat_weight 88.5 g × 93/100 | **82.3 卡** ✅ |

规则：**同时存在 weight 与 eat_weight 时，一律用 eat_weight**。差异最大的是香蕉、虾（带壳）、玉米棒、带骨菜——同一类坑。

## 二、`public_detail` 没有 `calcium` 键

返回键里有 `natrium`（钠），**没有 calcium**。对香蕉它返回的钙是 `None`。
所以档案里的钙只有两个正当来源：① 成分表同码条目（香蕉 `065033` 钙 7 mg/100 g）② 明确标注「借 USDA」。
数值可以取，但**来源标签要写清哪一列来自哪个库**，别整行都挂「薄荷」。

## 三、code 真伪只能用 `public_detail` 判

`boohee_api/docs_index_raw.json` 是**分页响应**，只含一部分条目：
- 在里面 grep 不到 `fd58f046`（黑莓）≠ 该 code 是编的
- 反过来 `xiangjiao` 的字面匹配命中的其实是 `qingxiangjiaopingguo`（青香蕉苹果），是子串假阳性

判真伪一律走免费 `public_detail(code)`：

```python
import sys
sys.path.insert(0, r"C:/Users/Administrator/health/tools")
from boohee import public_detail
r = public_detail(code)
d = r[0] if isinstance(r, tuple) else r     # 🔴 返回 tuple
```

2026-11-03 复核结果（全部存在、逐项数值与档案一致）：

```
xiangjiao 香蕉   93 / 1.4 / 0.2 / 22.0 / 纤 1.2 / 钠 0.8
fd58f046  黑莓   43 / 1.4 / 0.5 /  9.6 / 纤 5.3 / 钠 1.0   （与 USDA 一致）
fddb62ac  茶叶蛋 141 /13.7 / 9.1 /  2.2 / 纤 0.0 / 钠 444.0，个=50 g
```

## 四、本地 cache 与免费接口的分工

`boohee_api/cache.json`（130 条）是**付费/历史**结果的落盘，**新粮、新水果多半不在里头**。
本地没有 **不等于** 要降级估算——先 `public_detail`（免费、不花额度），再用 `quota.json` 有无当天键自证没花额度。
