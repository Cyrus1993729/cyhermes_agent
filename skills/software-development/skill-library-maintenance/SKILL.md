---
name: skill-library-maintenance
description: SKILL.md 太大或用户嫌长时用：原文切片拆分+零丢失校验。
version: 1.0.0
metadata:
  hermes:
    tags: [skill-hygiene, context-budget, refactor, zero-loss]
    related_skills: [hermes-memory-hygiene, model-subscription-evaluation]
---

# Skill 库维护（瘦身 / 拆分 / 零丢失迁移）

## 触发条件

- 用户说「这个 skill 太长了 / 巨长无比 / 精简一下」，或抱怨 agent 变慢而定位到 skill 加载
- 一个 SKILL.md **超过 30KB**（加载一次就是几万 token，之后每次 API 调用都重复付这笔过路费）
- skill 里「坑 1→坑 18」这类条目在无限追加，**已经变成日记而不是操作册**
- 🔴 **一个 SKILL.md 接近或超过 100,000 字符 = 已经无法再改**（见下「硬上限」节），必须立刻拆
- 写完/更新完 skill 后自查：这次是不是又往 SKILL.md 里塞了只该放 references 的细节

## 目标形态（先定标准再动手）

| 位置 | 放什么 | 体量目标 |
|:---|:---|:---|
| `SKILL.md` | **现在该怎么做**：触发条件、决策表、命令速查、安全铁律、references 索引 | ≤ 15KB |
| `references/<topic>.md` | **为什么这么做**：历次实案原文、踩坑逐条记录、复现命令与输出 | 单篇 ≤ 30KB |
| `scripts/<name>.py` | 能直接跑的验证/探测/迁移脚本 | 无上限 |
| `templates/<name>` | 供复制的骨架 | 无上限 |

判据：**「每次加载都必须知道的内容」才配留在 SKILL.md**；「只有特定场景才需要翻的内容」一律下沉。

## 硬规则（违背其一就会丢信息）

1. **只搬不改。** 下沉的内容用原文整段搬移，**不做改写、不做摘要、不删「过时的」条目**。改写就是信息损失，用户会明确要求「任何内容都不要丢」。
2. **源文件固定为原始备份。** 脚本从 `SKILL.md.bak_slim_<时间戳>` 读，不从当前 SKILL.md 读——否则第二次运行会把「已经瘦完的版本」当原文，越跑越少。
3. **按标题行号切片，不按内容猜。** 先 `grep -n '^## \|^### ' SKILL.md` 拿到全部标题行号，再按区间切片。**区间边界必须包含标题行本身**——漏掉标题就是一个整节没了（本 skill 的诞生原因，见下）。
4. **零丢失是校验出来的，不是保证出来的。** 见「校验」节，缺失行数必须为 0 才算完。

## 🔴 硬上限：100,000 字符会让 skill 变成只读

2026-10-30 实踩：`health-nutrition-analysis` 的 SKILL.md 涨到 **100,578 字符**，
只想加 3 行 references 索引都被 `skill_manage` 拒绝：

```
SKILL.md content is 100,578 characters (limit: 100,000).
Consider splitting into a smaller SKILL.md with supporting files in references/ or templates/.
```

**这不是「体积太大很慢」的软问题，是「从此再也改不动」的硬阻塞**——
包括补一行索引这种最小改动。拒绝发生在写入前，**整批 operation 一起回滚**。

🔴 **净减少也不一定能改：判的是「写入后的字符数」，不是增量。**
2026-10-30 实测：该文件 100,372 字符，连做三次「删掉一段旧文 + 加一行索引」的
**净负补丁全部被拒**（结果分别是 100,292 / 100,253 / 100,356）。公式是硬阈值：

```
可写  ⇔  当前字符数 − (old_string 长度 − new_string 长度)  ≤  100,000
```

即**必须一次砍掉至少「当前 − 100,000」个字**。超 372 字就得一次砍 ≥ 372 字，
几十上百字的微调永远不够。**这种情况下不要反复试小补丁**（实测连吃四次拒绝、
触发 loop 告警），直接按本文流程做一次完整拆分。

✅ **例外（很重要）**：`write_file` 新增 `references/` / `scripts/` / `templates/`
**不经过 SKILL.md 体量检查**。所以文件超限时新知识**仍然可以下沉**，而且
`skill_view` 返回的 `linked_files` 会自动列出它们——不会因为 SKILL.md 里加不了索引就被埋没。
2026-10-30 就是这样把 `health-nutrition-analysis/references/branded-drink-no-label.md` 加进去的。
→ **超限时的工作方式：新知识全部先写成 references 文件，指针等拆分时一并补上。**

连带影响：

- `skill_view` 加载 >100KB 的 SKILL.md 会 **spillover 到磁盘**（104.5KB 时实测），
  只返回前 ~1500 字符预览，正文要靠读 spillover 文件。
- 🔴 **别用 `read_file` 翻 spillover —— 那是一个「单行 JSON」**，整个文件只有 1 行，
  `offset/limit` 等于每次把 110KB 重新倒一遍进上下文。
  ✅ 正确读法（2026-11-02 实测，`health-nutrition-analysis` 110,438 字符那次的 spillover）：

  ```python
  import json
  d = json.load(open(spillover_path, encoding="utf-8"))   # 路径在 skill_view 返回里
  c = d["content"]        # SKILL.md 正文全文，是字符串不是行列表
  d["linked_files"]       # references / scripts 清单，一次全拿到
  i = c.find("派活")       # 先定位关键词
  print(c[i-200 : i+2500]) # 再切字符窗口
  ```

  两三次 `find` + 切片就能把要用的几节读全，不必整篇入上下文。
  **任何「按行号定位」的思路在这里全部失效**（行号恒为 1）。
- 但 `read-before-write` 门槛只认 `skill_view`，不认 `read_file` 翻 spillover——
  于是「读全文再改」这条门槛的单次代价被放大到 ~27K token，而且**读了也改不了**。

**判据（比上面的 30KB 硬得多）**：

| `wc -c SKILL.md` | 该做什么 |
|---|---|
| > 30KB | 排期拆分（软触发，本文上半部分） |
| > 80KB | **立即**拆分，不要再往里加任何内容 |
| > 95KB | 已经进入不可写区，先拆再说 |
| ≥ 100,000 | **`skill_manage` 完全拒绝修改**，连一行都加不了 |

**当前超限清单**：`health-nutrition-analysis` = **100,379 字符**（2026-10-30 晚再次实测；当日上午为 100,578，
中途一次成功的「坑 1→✅ 已修复」改写把它降到了 100,379，仍在硬限之上），
需要按本文流程拆分后才能继续维护。新内容一律先下沉到 `references/`——
拆完之前 `skill_view` 的 `linked_files` 仍会自动列出新 references，所以**下沉不会被埋没**。

## 六步流程

```bash
cd <skill_dir>
# 1. 备份（原样字节，含 CRLF）
cp SKILL.md SKILL.md.bak_slim_$(date +%Y%m%d_%H%M%S)

# 2. 摸结构：拿到全部标题行号
wc -l SKILL.md && grep -n '^## \|^### ' SKILL.md

# 3. 写切片 spec，一次跑完
python scripts/slim_skill.py --split split_spec.json

# 4. 零丢失校验（必须 0 缺失）
python scripts/slim_skill.py --verify SKILL.md.bak_slim_<ts> SKILL.md references/a.md references/b.md

# 5. 验证 skill 仍能加载、新 references 已进 linked_files
#    （用 skill_view 工具加载一次，看 linked_files.references 里有没有新文件）

# 6. 清理：只留首次原始备份，删掉中间产物
```

## 校验（唯一可信的「一个字没丢」证据）

**行级集合差**，不是字数对比：

```
原文非空行集合 − (新 SKILL.md ∪ 所有新 references 的非空行集合) = 必须为空集
```

脚本已实现（`--verify`）。判读口径：
- **缺失 0 行** = 通过，可以在回复里说「一个字没丢」。
- 缺失 >0 = **先别下结论**，去看缺的是哪几行。通常是一整节的标题被区间切掉了。
- 单点计数（如 `grep -c '坑[0-9]'`）**要统计所有输出文件的合计**，只看单个文件会误报「少了 6 条」——那些条目只是被拆到别的文件里去了。

## 坑（2026-10-20 实踩，瘦身 agent-mesh-networking 60KB→10KB 时）

- 🔴 **区间漏掉一个整节 = 静默丢 17 行。** 当时按 `seg(29,46) + seg(111,127)` 切，漏了 `47-66` 那一整节（「A2A 网关平台直连路径」），文档看着还挺完整。**是零丢失校验把 17 行逐个列出来才发现的。** 教训：切完别肉眼验收，跑校验。
- **第二次运行要先修源。** 脚本一旦写过 SKILL.md，重跑就会拿瘦身后的文件当原文。把源路径写死成 `glob('SKILL.md.bak_slim_*')[0]`，脚本才能安全重跑。
- **中间备份要清。** 失败那轮会留下一个「瘦身后的备份」，它污染下一次的 `glob()[0]` 选择，也会让后来人搞不清哪份才是原文。删干净，只留首次备份。
- **CRLF→LF 不算丢内容。** `io.open(..., encoding='utf-8')` + `splitlines()` 会把 `\r\n` 规整成 `\n`，字节数对不上是正常的（60,789→60,504）。校验用**行级**比对，别用字节数。

## 新 SKILL.md 必须长成什么样

拆完的 SKILL.md 里缺了这三样，等于制造了一个「不知道该读什么」的空壳：

1. **references 索引表**：`| 文件 | 内容 | 什么时候读 |` 三列。第三列是灵魂——不写触发场景，未来的 agent 不知道该去翻哪一篇。
2. **浓缩版核心规则 + 指路**：把最危险的那几条（如安全铁律五步）留在正文，末尾写「全文见 `references/xxx.md`」。
3. **速查表**：命令、诊断项、路径这类每次都要用的，留正文；带观测输出和复现步骤的，下沉。

## 与用户交互（本用户的硬约束）

- **瘦身属「改文件」，动手前必须先问**（decision-gate）。先给出体量数字（现在多大、目标多大、怎么拆），等一句「改吧」再动。
- **汇报节奏**：拆分不是一步完成的（摸结构 → 切片 → 校验 → 失败重跑），**每完成一段就冒一句**，别整个过程憋到最后一次性交付。校验失败的那一刻就要说，不要闷头修完再报。
- 结论里要给**可回滚的备份路径**（`SKILL.md.bak_slim_<ts>`），并说清「要回滚随时」。

## 参考

- `scripts/slim_skill.py` — 切片 + 零丢失校验二合一。`--split <spec.json>` 按行号区间原文搬移；`--verify <source> <out1> <out2> ...` 做行级集合差。spec 格式见脚本头注释。
