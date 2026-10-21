---
name: hermes-skill-hygiene
description: "【Skill 库维护与优化】审计、合并重复、统一描述、建立依赖。当你发现 Hermes 选错 skill、skill 之间有重叠、或需要定期整理时加载。跟 hermes-memory-hygiene 的区别：那个是整理 Memory 存储，这个是整理 Skill 文件本身。"
triggers:
  - "整理 skill 库"
  - "skill 太多了"
  - "skill 重复了"
  - "统一描述"
  - "优化路由"
  - "skill 选错了"
---

# Hermes Skill 库维护

当 skill 库膨胀到 30+ 时，Agent 路由准确度会下降——语义相近的 skill 互相争抢同一任务。本 skill 提供三步优化法。

---

## 三步优化法

### 第一步：合并重复项

**识别信号：** 多个 skill 的 description 描述同一类操作（如"抓取 X 推文""提取 X 数据""Scrape X timeline"）。

**操作流程：**
1. 读完所有候选 skill 的完整 SKILL.md
2. 选内容最全、最接近当前状态的一个做底板
3. 从其他 skill 中提取**独占内容**（某个特有的方案、陷阱、参考文件）
4. 汇总到底板中，按"方案速查"组织（方案①→②→③→④，从简到繁）
5. 删除其余 skill，`absorbed_into` 指向底板

**重要陷阱：** `skill_manage(action='delete')` 会删除整个 skill 目录，包括 `references/` 和 `scripts/`。删除前用 `skill_manage(action='write_file')` 把关键参考文件迁到底板，或确认内容已内联到合并后的 SKILL.md。

### 第二步：统一 description 格式

**目标：** 每个 skill 的 description 让 Agent 一眼看出「做什么」和「跟邻居的区别」。

**标准格式：**
```
"【一句话做什么】核心能力简述。| 跟 XX 的区别：那个是做 A 的，这个是做 B 的。跟 YY 的区别：那个是...。"
```

**优先级：先改会互相争抢的 skill 对。** 比如：
- X 类：抓取 vs 监控 vs 搜索 vs 分析
- 投资类：通用框架 vs 黄金专用 vs 宏观定价
- 开发类：写代码 vs 清理 vs 执行计划

**描述不需要面面俱到**——它在路由阶段能被看到，关键是"我该选这个而不是那个"的判断信息。

### 第三步：建立依赖关系

在 YAML frontmatter 中加 `requires` / `extends` 声明：

```yaml
# 强依赖——用 A 必须同时加载 B
requires: [claude-code]

# 继承关系——A 是 B 的一个落地实例
extends: [investment-analysis]
```

同时在 description 中加"两者需同时加载"提示。即使 Hermes 当前不做自动加载，Agent 读到时就知道要补。

---

## 其他维护动作

- **skill 名过时？** 用 `skill_manage(action='edit')` 重写整个 SKILL.md（同时改 name 字段即可改名）
- **单个 skill 内容有误？** 用 `patch` 做 targeted edit，比 `edit` 高效且不容易出错
- **补充参考文件？** 用 `skill_manage(action='write_file', file_path='references/xxx.md')`

---

## 效果衡量

优化后应该能观察到的变化：
- 用户说"搜 Serenity 推文"时，Agent 不再在 6 个 X 抓取 skill 里瞎猜
- 触发条件相近的 skill 对之间，Agent 能靠 description 中的区分信息选对
- 加载一个 skill 时附带加载了正确的依赖项
