# 健康核算引擎 `nutri_calc.py` 与派活规范（2026-11-13 落地）

用户在 2026-11-13 拍板：**核算的算术部分脚本化，口径判断仍归健康助理**。
本文档给主 Hermes 看——派活时怎么带、验收时看什么。

---

## 一、为什么会有这个引擎

旧流程每餐写 4~5 个一次性脚本（`_bf1112_calc.py` / `_lu1112_calc.py` / `_dn1112_calc.py`…），
每餐 22~25 次工具调用、29 次 API 往返。2026-11-13 实测：新流程同一餐 **5 次工具调用**。

**关键设计边界（用户明确同意的那一半）**

| | 归引擎 | 归模型 |
|:--|:--|:--|
| 逐项表 / 合计 / 算术自检 / 未收录项提示 | ✅ | |
| 查食物库、取哪一条 | | ✅ |
| 口径判断（入口比例、可食率、拆分比例、生熟） | | ✅ |
| 看图确认商品参数（`vision_analyze`） | | ✅ |
| 口径说明散文、假设清单 | | ✅ |

🔴 **引擎只消除算术错误，不消除取数错误。** 查错了食物条目，引擎会忠实把错误放大到合计——
所以「数据来源」那一栏**不许省**。

---

## 二、位置与 API 速查

```
C:\Users\Administrator\health\tools\nutri_calc.py
spec 放 C:\Users\Administrator\health\tools\specs\<名字>.py
```

```python
from nutri_calc import Item, DirectItem, Meal, render, compare_to, split_by_ratio, norm1

# 常规行：每 100 g 值 × 克数
Item(name="鸡腿肉", source="薄荷 `jitui` 20.2/11.0/73.6", grams=300.0,
     per100=norm1(kcal=179.8, P=20.2, F=11.0, C=0, fi=0, Na=73.6, Ca=None),
     purine=173.0, purine_mark="‡",
     raw_grams=10.0, ratio=0.85)        # 可选：展示「10 g × 85% = 8.50」

# 直接给值的行（如食堂的「调味钠差额」）
DirectItem(name="调味钠差额", source="含盐率1.2%×150g×400−自带26.79", values=dict(Na=693.21))

m = Meal(name="2026-11-13 午餐", items=[...])
print(render(m, show_source=True))     # 逐项表 + 合计 + 算术自检 + ⚠️ 未收录项
ok, diffs = compare_to({"kcal": 876.33, ...}, m)   # 与档案已记录数字对账
```

`render()` 里 `source` 含 `%` 时记得写 `%%`（走 `%` 格式化），否则 `ValueError`。

---

## 三、四条固化口径（改了就跟历史档案对不上）

1. **每 100 g 值取薄荷公布的 1 位小数** —— `norm1(kcal=65, P=1.18, F=0.08, ...)`。
   缓存里存的是原始多位值（1.18 / 0.08 / 2.25），档案历史用的是 1.2 / 0.1 / 2.2。
   直接用原始值会让分项差 0.01~0.08（实测：蛋白 16.94 vs 16.97、钠 290.56 vs 290.48）。
   用户口径是「**算法别变了**」。
2. **沙拉等比拆分保留 0.1 g** —— `split_by_ratio(total, ratios, ndigits=1)`，
   用最大余数法保证拆分之和严格等于总量。保留 2 位会让热量差 0.01、钠差 0.07。
3. **来源标签栏不可省**（见上文）。
4. **未收录字段按 0 计但必须标出**，引擎会打 ⚠️ 提示。**不许编数。**

---

## 四、回归测试（改引擎前后必跑，必须报不一致 0）

```bash
cd C:/Users/Administrator/health/tools
python _exp_1112_dn_replay.py     # 复现 2026-11-12 晚餐，应「全部 9 项完全一致」
python _exp_1112_lu_rows.py       # 复现 2026-11-12 午餐，应「11 行，不一致 0」
```

这两份是把历史档案的数字当金标准。**任何引擎改动后跑一遍**，是唯一能证明「口径没漂」的手段。

---

## 五、主实例派活时的固定尾注（必须带）

canonical 会话**不会自己学会新流程**（实测 `skill_view` 调用 0 次、也不读 `profile.md`）。
派活时任务书末尾固定带：

```
---
【流程要求】核算的算术部分一律走 `C:/Users/Administrator/health/tools/nutri_calc.py`：
写 spec 到 `C:/Users/Administrator/health/tools/specs/` →
`cd C:/Users/Administrator/health/tools && python specs/<spec>.py`。
不要写一次性临时核算脚本。查料、看图、口径判断、写口径说明仍然你自己做。
```

验收**看工具调用记录，不看它的自述**（它会说「已按流程」然后照旧写临时脚本）：

```python
import sqlite3, json
c = sqlite3.connect(r".../profiles/health/state.db")
for mid, tc in c.execute("select id,tool_calls from messages where session_id=? and id>? order by id", (sid, last_id)):
    for call in json.loads(tc or "[]"):
        print(mid, call["function"]["name"], "nutri_calc" in call["function"]["arguments"])
```

---

## 六、🔴 成品菜先查证，再拆项（2026-11-13 用户质疑）

用户问：「**香菇青菜 和 白菜炒肉 薄荷库里都没有现成的吗？为什么是拆项算的？**」

翻工具记录发现：健康助理只搜了单料（`油菜`/`香菇`/`五花肉`…），**一个菜名都没搜**，直接拆项。

实测（`boohee.anchor()` 免费接口，零额度）：

- **`白菜炒肉` / `白菜炖肉` / `白菜烧肉` / `猪肉白菜炖` → 全部 0 候选**，薄荷确实没有，拆项是必须的。
- **`香菇青菜` → 有 2 条成品菜**：`盒马 香菇青菜` fd5ebd5b 25 卡、`无油盐版香菇青菜` fdb9fc87 20 卡。
  （另有 `盒马 香菇油菜` 34 卡、`蚝油香菇油菜` 84 卡）

**规矩**：核算成品菜前，先 `boohee.anchor("<菜名>")` 查一遍（免费，可以放心试词），
查不到**或明显不适用**（无油盐版 vs 食堂版差 20+ 卡）再拆项，
并在口径说明里写明「**查过，没有 / 不适用**」。
用户会翻工具记录验证你到底查没查。

---

## 七、`tools/` 目录归置的教训（2026-11-13 踩坑）

2026-11-13 把 393 个一次性脚本从 `tools/` 顶层移进 `_scratch/`，
**判断依据只有「文件名带不带下划线」，漏掉了非 .py 的运行时数据文件**——
`prompt_recognize.txt`（`recognize.py` 的识图 prompt，20,664 bytes）被一起挪走，
午饭照片识别直接跑不起来。健康助理自己发现并从 `_scratch/` 拷回去才跑通。

**归置前必须先查正式工具运行时 `open()` 了哪些文件，那些必须留在顶层：**

| 文件 | 位置 | 谁用 |
|---|---|---|
| `prompt_recognize.txt` | `tools/` | `recognize.py` |
| `.pending_meal.json` | `diet/` | `meal.py` 两步流程中间态 |
| `cache.json` / `quota.json` / `token.json` / `piece_weight.json` | `fooddb/boohee_api/` | `boohee.py` |
| `foods.json` / `custom_foods.json` / `gi.json` / `oil_profile.json` | `fooddb/` | `fooddb.py` / `meal.py` |

清单与恢复方式见 `~/health/tools/_scratch/README.md` 和 `_MANIFEST.json`。

---

## 八、切回旧流程

`~/health/archive/pre_engine_20261113_0947/` 有改动前的完整快照
（`skills/` / `config.yaml` / `MEMORY.md` / `USER.md` / `tools_snapshot/`）。拷回即还原。
用户原话：「今天开始尝试新流程，如果什么时候觉得效果不好，随时切回来」。
