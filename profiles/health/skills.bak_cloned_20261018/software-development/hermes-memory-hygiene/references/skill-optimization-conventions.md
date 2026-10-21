# Skill 库优化方法论

## 第一步：合并重复项

**触发条件**：库中存在 2+ 个 skill 描述高度重叠（关键词一致、描述几乎相同）

**做法**：
1. 读所有重复 skill 的完整 SKILL.md
2. 选其中最全面/最后更新的作底板
3. 把其他 skill 独有的知识（参考文件、脚本、已知陷阱）汇入底板
4. `skill_manage(action='delete', absorbed_into='底板skill')` 删掉其余

**案例**：x-twitter-data / x-twitter-data-collection / x-twitter-scraper / x-twitter-scraping / x-tweet-scraping（6 个）→ x-twitter-data-extraction（1 个）

---

## 第二步：统一描述格式

所有 skill 的 YAML `description` 统一成：

```
【做什么】一句话定位。| 跟 XX 的区别：具体差异描述。
```

**关键原则**：
- 每个 description 必须写明跟最相似的 skill 有什么区别
- 语言用中文，用户是中文使用者
- 如果有多段区别描述（跟 A 和跟 B 都不同），用 `。` 分隔

**案例改动**：
- `x-monitor`：`【定时监控 X 账号+推送到微信】... | 跟 x-twitter-data-extraction 的区别：那个是怎么抓数据，本 skill 是怎么定时抓+自动推送`
- `investment-analysis`：`【通用量化投资框架方法论】... | 跟 gold-investment-analysis 的区别：那个是黄金专属七因子打分系统，这个是通用方法论`
- `claude-code`：`【Claude Code CLI 使用方法】... | 跟 claude-code-workflow 的区别：那个是调用规则，这个是工具使用方法。两者需同时加载`

---

## 第三步：建立依赖关系

在 YAML 前导块中添加：

```yaml
requires: [依赖的基础 skill]       # 本 skill 运行前必须加载
extends: [扩展的上层 skill]        # 本 skill 是某通用框架的具体落地
```

已建立的关系：
- `claude-code-workflow` → requires `claude-code`
- `x-monitor` → requires `x-twitter-data-extraction`
- `gold-investment-analysis` → extends `investment-analysis`
- `bilibili-understand` → requires `video-understand-core`
- `serenity-tweet-analysis` → requires `serenity-search`
- `mcp-server-setup` → requires `native-mcp`
- `subagent-driven-development` → requires `writing-plans`

---

## 工作流配方模板

当多个 skill 组成一个串行分析流程时，在**主角 skill** 末尾添加：

```markdown
## 🧩 工作流配方

**任务**：{任务名}
**加载顺序**：
1. `skill-a` — {做什么}
2. `skill-b` — 本 skill：{做什么}
3. {条件触发} `skill-c` — {什么条件下叠加}
4. {条件触发} `decision-gate` — {什么条件下触发闸门}
**交付**：微信分段 + MEDIA 文件（格式见 xiaohongshu-analysis「输出与交付」章节）
**收尾**：检查 `post-task-review` 触发条件
```

已建立的配方：
- Serenity 推文分析（serenity-tweet-analysis）
- 黄金周报（gold-investment-analysis）
- B站视频分析（bilibili-understand）
- 供应链涟漪分析（supply-chain-ripple-analysis）
- 小红书内容分析（xiaohongshu-analysis）

---

## 横切约定

- **微信分段交付**：所有输出型 skill 统一引用 `xiaohongshu-analysis` 的「输出与交付」章节，不各自重复维护
- **复盘触发**：重任务 skill 末尾统一加「检查 post-task-review 触发条件」
- **决策闸门**：分析涉及操作建议时统一触发 `decision-gate`
- **框架审视**：xiaohongshu/B站分析涉及金融/AI/技术主题时，触发 `deep-analysis-workflow`（有框架加载框架，无框架向 Claude 借框架）
