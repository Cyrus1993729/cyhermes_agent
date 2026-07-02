# Skill 库维护规范（2026-07-01 确立）

## 一、描述格式

每个 SKILL.md 的 `description` YAML 字段统一为：

```
【做什么】一句话说清功能。| 跟 <容易混淆的skill> 的区别：... | 跟 <另一个> 的区别：...
```

**原则：**
- `【】` 前缀让 Agent 一眼看懂职能
- `|` 分隔的「区别」段落是路由质量的关键——两个 skill 功能相近时，Agent 靠这段文字决定选哪个
- 不要只写自己做什么，要写「我不是什么 / 我不覆盖什么」
- 中文优先（用户母语）

**示例：**
```
description: "【定时监控 X 账号+推送到微信】部署 cron 每天拉最新推文。| 跟 x-twitter-data-extraction 的区别：那个是「怎么抓数据」，这个是「怎么定时抓+自动推送」。"
```

## 二、依赖声明

在 YAML 头部声明 skill 之间的依赖关系：

- `requires: [skill-a, skill-b]` — 加载本 skill 时必须同时加载这些
- `extends: [skill-x]` — 本 skill 是 skill-x 的子类/落地实现

**生效机制：** Hermes 目前不自动解析 requires/extends 做预加载，但 Agent 读到 YAML 时会据此决策。配合描述中的「两者需同时加载」效果最佳。

**示例：**
```yaml
name: claude-code-workflow
requires: [claude-code]
description: "【用户自定义的 Claude Code 调用规则】...| 两者需同时加载。"
```

## 三、工作流配方

在核心 skill 的 SKILL.md 末尾加 `## 🧩 工作流配方` 章节，格式：

```markdown
## 🧩 工作流配方

**任务**：一句话
**加载顺序**：
1. `skill-a` — 做什么（先建立上下文）
2. `skill-b` — 做什么（核心逻辑）
3. 条件触发：什么情况下叠加 `skill-c`
4. 涉及行动建议时，触发 `decision-gate`
**交付**：微信分段 + MEDIA 文件
**收尾**：检查 `post-task-review`
```

**已建立的配方（2026-07-01）：**
- serenity-tweet-analysis：serenity-search → 分析 → 产业链 → 闸门 → 复盘
- gold-investment-analysis：gold-macro-framework → 打分 → deep-analysis → 闸门 → 复盘
- bilibili-understand：video-understand-core → 理解 → deep-analysis → 复盘
- supply-chain-ripple-analysis：automated-investment-research → 涟漪分析 → 量化审视 → 闸门 → 复盘
- xiaohongshu-analysis：提取 → deep-analysis（金融/AI/技术全部触发）→ 闸门 → 复盘

## 四、横切约定

当一个模式被多个 skill 重复实现时（如微信分段交付），指定一个 skill 的章节作为标准参考，其他 skill 引用它而非各自重复维护。

**示例：**
xiaohongshu-analysis 的「输出与交付」章节是所有输出型 skill 的微信分段标准参考。其他 skill 写 `**交付**：微信分段（格式见 xiaohongshu-analysis「输出与交付」章节）`。
