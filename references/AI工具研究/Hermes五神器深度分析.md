# 🔬 Hermes Agent 5大神器 · 深度分析

> 来源：小红书 @喵了个AI的  
> 链接：https://www.xiaohongshu.com/discovery/item/6a35c9a1000000000f014cf9  
> 👍36 ⭐62 ↗️16

---

## 1️⃣ 橙皮书：从入门到架构精通的系统教材

**仓库**：`alchaincyf/hermes-agent-orange-book` ⭐4,490 · 🍴454  
**作者**：花叔（300K+粉丝AI创作者，B站/YouTube/公众号同名）

### 它是什么？
一本 **21节、6大部分** 的系统教材（PDF免费下载），覆盖 Hermes Agent v0.16.0 全部能力。第一版基于v0.7.0，两个月后产品大变样（桌面端、浏览器面板、23个平台接入），于是完全重写为2.0版。

### 六大部分具体内容

| 部分 | 主题 | 具体内容 |
|:---|:---|:---|
| ① 这是什么 | 认识Hermes | 一个大脑多个面孔、Nous为什么造它、与传统AI Agent的区别 |
| ② 缰绳自生 | 三大自我改进引擎 | Curator机制、自动Skill生成、什么不该学 |
| ③ 如何记住你 | 三层记忆系统 | 短期/中期/长期记忆、Session Search、Skill进化、多Agent编排 |
| ④ 连接一切 | 工具与平台 | 64个内置工具、MCP协议、23个消息平台、3种交互界面 |
| ⑤ 多Agent编排 | 协作与调度 | delegate_task机制、Kanban平台、协作模式、swarm并行 |
| ⑥ 部署与安全 | 边界与防御 | 部署方案、OS安全边界、Promptware防御、能力上限 |

### 关键技术点
- Hermes Agent 是「Harness Engineering」（缰绳工程学）5个组件（指令/约束/反馈/记忆/编排）的产品化
- 不像 Claude Code / OpenClaw，Hermes 的独特之处在于**内置自我改进循环**——Skill可以自动创建、自动进化
- 新版本加入了持久化多Agent Kanban平台和OS级安全模型

### 对你有什么用？
- 你已经深度使用 Hermes，这本教材能帮你从「会用」到「理解为什么」
- 第③部分（记忆系统）直接关系你当前的使用效率
- 第⑤部分（Kanban多Agent）是你做批量任务（如同时分析多个帖子）的基础设施
- **PDF下载**：https://github.com/alchaincyf/hermes-agent-orange-book/raw/main/Hermes-Agent橙皮书2.0-v260607.pdf

---

## 2️⃣ 优化手册：把 Hermes 调到生产级

**仓库**：`OnlyTerp/hermes-optimization-guide` ⭐461 · 🍴37  
**作者**：Terp AI Labs · 更新至 2026-06-17 · 支持中/英/日三语

### 它是什么？
**实操手册型项目**——不是教科书，而是给你**直接能用的配置、脚本、Skill**。26个部分，涵盖从安装到生产部署的全流程。每个部分都配有可执行文件。

### 核心资产（126个文件）

**13个可安装的 Skill：**

| 类别 | Skill | 功能 |
|:---|:---|:---|
| 🛠 开发 | `pr-review` | 自动化PR代码审查 |
| 🛠 开发 | `meeting-prep` | 会议材料准备 |
| 🛠 开发 | `release-notes` | 自动生成发布说明 |
| ⚙️ 运维 | `cost-report` | API/模型成本报告 |
| ⚙️ 运维 | `daily-inbox-triage` | 每日消息分拣处理 |
| ⚙️ 运维 | `hermes-weekly` | 周报自动生成 |
| ⚙️ 运维 | `nightly-backup` | 夜间自动备份 |
| ⚙️ 运维 | `telegram-triage` | Telegram消息智能分拣 |
| ⚙️ 运维 | `weekly-dep-audit` | 依赖包安全审计 |
| 🔒 安全 | `audit-approval-bypass` | 审批绕过审计 |
| 🔒 安全 | `audit-mcp` | MCP服务器安全审计 |
| 🔒 安全 | `rotate-secrets` | 密钥轮换管理 |
| 🔒 安全 | `spam-trap` | 垃圾信息过滤 |

**5套即用配置模板：**
- `minimum` —— 最小化（省资源）
- `telegram-bot` —— Telegram机器人专用
- `production` —— 生产环境全功能
- `cost-optimized` —— 成本优先模式
- `security-hardened` —— 安全加固

**一条命令部署到VPS：**
```bash
curl -sSL https://raw.githubusercontent.com/OnlyTerp/hermes-optimization-guide/main/scripts/vps-bootstrap.sh | sudo bash
```
这会在空白 Debian/Ubuntu 上自动安装：Hermes + Node.js + Caddy（自动HTTPS）+ UFW防火墙 + fail2ban + 创建 hermes 用户 + hardened systemd + 14个Skill就位。

### 19个独立部分文件
`part1-setup.md` 到 `part19-security-playbook.md`，覆盖安装、迁移、LightRAG、Gateway、桌面端、MCP服务器、编程Agent、安全手册等。

### 对你有什么用？
- 如果你将来想部署 Hermes 到云服务器24/7运行，`vps-bootstrap.sh` 一条命令搞定
- 运维Skill可根据需要选择安装（备份、成本报告）
- **但大部分内容偏DevOps运维，你本地场景可能不需要**

---

## 3️⃣ GBrain：YC总裁的"数字大脑"

**仓库**：`garrytan/gbrain` ⭐23,569 · 🍴3,389  
**作者**：Garry Tan（Y Combinator 总裁兼CEO）  
**规模**：TypeScript项目 · 43个内置Skill · 30+ MCP工具 · CHANGELOG 1.9MB

### 它是什么？
Garry Tan 为他的 Hermes 和 OpenClaw 构建的**知识管理系统**。核心理念：给AI Agent一个真正的长期记忆——不是"搜出10个片段你自己读"，而是"替你读完全部，给出综合答案+标注已知缺口"。

### 核心差异：搜索 vs 思考

**传统知识工具（搜索模式）：**
```
你问："明天跟Alice开会前我该知道什么？"
它返回：
  1. people/alice —— Alice在Acme管工程...
  2. meetings/2026-03-15-alice-q1 —— Q1产品复盘...
  3. customers/acme —— Acme是B轮金融科技...
  （你得自己打开5篇文档读完才能准备好）
```

**GBrain（合成模式）：**
```
你问："明天跟Alice开会前我该知道什么？"
它回答：
  Alice在Acme（B轮金融科技）管工程。上次联系是4月22日聊定价。
  3件事还挂着：
  1. 她还欠你新套餐安全审查（5月1日截止，没更新）
  2. 你承诺了500席定价方案（4月25日发出，没回复）
  3. 她提到在招CSO，你说帮她介绍人
  
  ⚠️ 注意：4月22日后大脑里没有Alice的新信息（已过6周）。
  她可能邮件/Slack回了你——那些渠道大脑看不到。开会前先跟她确认。
```

每个结论都有来源页面。最后的「⚠️注意」告诉你**大脑不知道什么**——这是传统搜索做不到的。

### 技术架构

| 能力 | 实现细节 |
|:---|:---|
| **知识图谱** | 每写入一页自动提取实体关系（`works_at`, `invested_in`, `founded`, `advises`），**零LLM调用** |
| **检索性能** | P@5=49.1%, R@5=97.9% — 比纯向量检索高31.4个百分点 |
| **混合检索** | 向量 + 关键词 + RRF融合 + 来源层级加权 + 重排序器 |
| **夜间巡航** | 66个cron在你睡觉时运行——消化邮件/会议/推文/语音→丰富人脉和公司信息→修正引用→整合记忆 |
| **团队大脑** | 每人按登录身份隔离可见范围。模糊测试验证0信息泄漏 |
| **MCP集成** | 30+工具通过MCP暴露，支持Claude Code/Codex/Cursor/Windsurf/ChatGPT/Perplexity等 |

### Garry Tan自己的大脑数据
- 146,646 页知识
- 24,585 人被追踪
- 5,339 家公司被追踪
- 66个cron 24/7自主运行

### 43个内置Skill（部分精选）

| Skill | 功能 |
|:---|:---|
| `meeting-ingestion` | 会议内容自动消化入库 |
| `article-enrichment` | 文章自动丰富化（提取实体、关系） |
| `citation-fixer` | 引用自动修正 |
| `concept-synthesis` | 跨文档概念合成 |
| `signal-detector` | 信号检测（发现重要变化） |
| `idea-lineage` | 想法谱系追踪（一个idea的演变路径） |
| `cross-modal-review` | 跨模态复核（文本/语音/图片交叉验证） |
| `soul-audit` | 大脑「灵魂审计」（检查知识一致性） |
| `brain-taxonomist` | 知识分类学家 |
| `strategic-reading` | 战略性阅读（优先读最重要的） |
| `voice-note-ingest` | 语音备忘录消化 |
| `book-mirror` | 书籍镜像（整本书结构化入库） |
| `briefing` | 自动生成简报 |
| `daily-task-manager` | 每日任务管理 |

### 安装方式
```bash
# 有AI Agent帮你装（推荐）——粘贴这行给Agent：
# https://raw.githubusercontent.com/garrytan/gbrain/master/INSTALL_FOR_AGENTS.md

# 本地给Claude Code/Codex装（2秒数据库 + 1条命令）：
gbrain init --pglite                     # 本地脑（无需Docker）
claude mcp add gbrain -- gbrain serve    # 连上Claude Code
```

### 对你有什么用？
- 这**不是**一个装了就行的插件——它是一个需要你自己数据进去才能发挥价值的完整系统
- 但它的**设计理念**极有价值：合成答案+已知缺口、夜间自主巡航、知识图谱自动构建
- 如果你有分散各处的笔记/资料（Obsidian、聊天记录、书签），GBrain可以统一管理
- **实操建议：** 先不装。读它的设计文档和AGENTS.md，理解Garry如何设计Agent记忆系统——对调你自己的Hermes有启发

---

## 4️⃣ Superpowers-zh：让你的Hermes真正懂中文

**仓库**：`jnMetaCode/superpowers-zh` ⭐5,650 · 🍴543  
**基础**：superpowers（233K+⭐ 全球最火AI编程Skill框架）  
**社区**：微信公众号「AI不止语」+ 微信/QQ群 · 官网 sp.aiolaola.com

### 它是什么？
superpowers的**完整汉化增强版**——14个翻译Skill + 6个中国原创Skill = 20个实战技能。支持18款AI编程工具。**npm包形式分发**，一条命令自动识别并安装。

### 完整技能清单（20个）

**14个翻译自上游的经典Skill：**

| Skill | 功能 | 适用场景 |
|:---|:---|:---|
| `brainstorming` | 结构化头脑风暴 | 新功能/新项目启动 |
| `writing-plans` | 写bite-size实施计划 | 编码前规划 |
| `subagent-driven-development` | 子代理驱动开发 | 大型任务拆分 |
| `test-driven-development` | TDD红-绿-重构循环 | 高质量代码 |
| `systematic-debugging` | 系统化4阶段调试 | 复杂Bug排查 |
| `requesting-code-review` | 提交前代码审查 | 安全扫描+质量门 |
| `github-pr-workflow` | PR全生命周期 | 分支→提交→CI→合并 |
| `github-code-review` | PR代码审查 | diff分析+行内评论 |
| `github-issues` | Issue管理 | 创建/分类/分配 |
| `github-repo-management` | 仓库管理 | 克隆/创建/Fork |
| `codebase-inspection` | 代码库检查 | LOC/语言统计 |
| `mcp-builder` ⭐ | 构建MCP服务器 | 创建新MCP工具 |
| `workflow-runner` ⭐ | 多角色YAML编排 | 自动化流水线 |
| `design-review` ⭐ | 设计审查 | 红队式批判审查 |

⭐ = 中国原创Skill

**6个中国原创Skill：**
1. **多Git平台适配** —— GitHub + Gitee + Coding + 极狐GitLab + CNB（腾讯）
2. **中国CI/CD模板** —— GitHub Actions + Gitee Go + Coding CI + 极狐CI + `.cnb.yml`
3. **中文Git提交规范** —— Conventional Commits中文适配版
4. **中文文档规范** —— 中文排版+中英混排规则+告别机翻味
5. **国内团队沟通适配** —— 代码审查语气/措辞适配中国文化
6. **MCP-builder** —— 独立MCP服务器构建Skill

### 核心理念：改变AI的「干活方式」

**没装 superpowers：**
```
你：给用户模块加批量导出
AI：好的，我来实现...（直接开始写代码）
    export async function exportUsers() { ... }
你：等等，格式不对，没分页，大数据量会OOM...
```

**装了 superpowers：**
```
你：给用户模块加批量导出
AI：在开始实现之前，我需要了解几个关键问题：
    1. 导出格式是 CSV 还是 Excel？
    2. 预计数据量多大？需要异步处理吗？
    3. 有权限要求吗？
    → 给出2-3个方案，你确认后再动手
```

### 与英文上游的关键差异

| 维度 | superpowers（上游） | superpowers-zh（增强版） |
|:---|:---|:---|
| Skills总数 | 14 | **20** |
| 支持工具 | 6款 | **18款** |
| 安装方式 | 按工具分别装 | `npx superpowers-zh` 自动识别 |
| Git平台 | GitHub | GitHub + Gitee + Coding + 极狐 + CNB |
| CI/CD | GitHub Actions only | 5种CI模板 |
| 接受新Skill PR | 一般不接受 | 欢迎PR |

### 安装到Hermes
```bash
npx superpowers-zh --tool hermes
```
自动把20个Skill装到 `~/.hermes/skills/`

### 对你有什么用？
- **这是5个里最直接可用的。** 一条命令、20个Skill全部就位
- 你已经有部分Skill（plan、debugging等），但superpowers-zh提供的是**统一的方法论体系**——所有Skill遵循一致的交互模式
- `workflow-runner` 对你有直接价值——如果你想编排自动化流水线（如小红书内容全自动分析），这个可以直接用
- **中文原生**——不再需要手动翻译英文Skill的指令

---

## 5️⃣ Avoid-AI-Writing：消灭AI写作痕迹

**仓库**：`conorbronsdon/avoid-ai-writing` ⭐1,911 · 🍴192  
**作者**：Conor Bronsdon · MIT协议 · 0个Open Issue（维护得很好）

### 它是什么？
一个**可验证、可量化**的AI文本检测+重写Skill。不是简单一句prompt「去AI味」，而是一整套109项词汇替换表 + 49个模式分类 + 两轮检测的工程化体系。

### 三大模式

| 模式 | 功能 | 适用场景 |
|:---|:---|:---|
| **Rewrite（默认）** | 标记→重写→二次扫描 | 你要发布的内容 |
| **Detect** | 仅标记不修改 | 审查他人内容、判断哪些是真问题 |
| **Edit** | 原地最小化编辑 | 保留已有的人类表达，只改AI痕迹 |

### 109项词汇替换表（3层分级）

**Tier 1（必标）**——AI几乎必用，人类几乎不用：
> "Leverage" → "use" · "Commence" → "start" · "Moreover" → 删除  
> "In conclusion" → 删除 · "It is worth noting that" → 删除

**Tier 2（聚类标）**——单个词不一定AI，扎堆出现就可能是：
> "Robust" · "Seamless" · "Comprehensive" · "Cutting-edge"

**Tier 3（高密度标）**——特定短语重复或堆叠时标记：
> "The integration of" · "Decentralized compute" · "In the realm of"

### 49个模式分类（部分精选）

| 类别 | 示例 |
|:---|:---|
| 聊天机器人开场 | "Certainly!" "Absolutely!" "Great question!" |
| 夸张修饰 | "vibrant ecosystem" "thriving community" |
| 意义膨胀 | "watershed moment" "paradigm shift" |
| 空洞结论 | "the future looks bright" "only time will tell" |
| 模糊归因 | "experts believe" "studies show"（不引用具体来源） |
| 过度统一 | 段落长度/句式过于均匀（人类写作天然参差） |
| Hashtag堆砌 | 社交媒体帖子塞满标签 |
| 裸名词短语列表 | 无动词的bullet list（AI特征） |
| UTM参数残留 | AI从网上抓取内容时留下的跟踪参数 |
| 引用标记残留 | "[1]" "[citation needed]" |

### 效果演示

**输入（AI味爆表）：**
> Certainly! Acme Analytics, a vibrant startup nestled in the heart of Boulder's thriving tech ecosystem, has secured $40M in Series B funding — marking a watershed moment for the observability landscape. The platform serves as a unified hub, featuring real-time dashboards, boasting sub-second queries, and presenting a seamless integration layer. Moreover, experts believe Acme is poised to disrupt the market. In conclusion, the future looks bright!

**输出（人类口吻）：**
> Acme Analytics raised a $40M Series B led by Sequoia. The Boulder-based startup makes an observability platform that runs queries in under a second and plugs into existing monitoring stacks without custom integration work.

**一段话抓出15+个AI痕迹**：Certainly! / vibrant / nestled / thriving / watershed moment / serves as / featuring / boasting / presents / seamless / Moreover / experts believe / poised to disrupt / In conclusion / the future looks bright。

### 安装方式
```bash
# Claude Code
git clone https://github.com/conorbronsdon/avoid-ai-writing ~/.claude/skills/avoid-ai-writing

# Hermes Agent
git clone https://github.com/conorbronsdon/avoid-ai-writing ~/.hermes/skills/avoid-ai-writing
```

### 对你有什么用？
- 你已有 `humanizer` Skill——功能重叠。`avoid-ai-writing` 更系统化、更可验证（109项词汇表+49个模式有明确的检测逻辑，不是纯prompt）
- 如果你发布公众号/小红书/知乎内容，写完后过一遍这个Skill确保读起来像人
- ⚠️ 注意：**以英文检测为主**。中文AI痕迹（"总而言之""值得注意的是""综上所述"）需要额外适配。但核心检测逻辑（段落均匀度、空洞结论、模糊归因）跨语言适用

---

## 📊 五者关系全景

```
           ┌──────────────────────────────────────┐
           │         GBrain（知识管理层）           │
           │   「给Agent真正的长期记忆系统」         │
           │   知识图谱 + 合成答案 + 夜间巡航        │
           └──────────────┬───────────────────────┘
                          │ 需要个人数据才能工作
                          ▼
  ┌────────────────────────────────────────────────┐
  │              Hermes Agent（核心引擎）            │
  │         持久记忆 + Skill进化 + 多平台接入        │
  └──┬──────────────┬──────────────┬───────────────┘
     │              │              │
     ▼              ▼              ▼
  ┌────────┐  ┌──────────┐  ┌──────────────┐
  │ 橙皮书  │  │优化手册   │  │superpowers-zh│
  │ 学原理  │  │调到生产级  │  │20个实战Skill  │
  └────────┘  └──────────┘  └──────────────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │ avoid-ai-writing │
                      │  产出人性化把关   │
                      └──────────────────┘
```

---

## 🎯 给你的行动建议（按优先级）

| 优先级 | 项目 | 行动 | 理由 |
|:---:|:---|:---|:---|
| 🥇 | **superpowers-zh** | 立即装 | 一条命令20个Skill到位，中文原生。直接提升每次跟Hermes交互的质量 |
| 🥈 | **橙皮书** | 下载PDF翻第③④章 | 理解记忆系统和Skill进化原理——帮你更好地「调教」Hermes |
| 🥉 | **avoid-ai-writing** | 若发公众号/小红书就装 | 比humanizer更系统化，产出内容前过一遍 |
| 4 | **gbrain** | 先不装，读设计文档 | 需要大量个人数据才有价值。但设计理念（合成答案+已知缺口）值得学 |
| 5 | **优化手册** | 需要时查阅 | 偏DevOps部署，本地用不太需要。若要部署云服务器再来翻 |

---

## 🔧 技术复盘

| 步骤 | 耗时 | 备注 |
|:---|:---|:---|
| xhslink短链重定向 | ~1s | GET + header dump（HEAD返回404） |
| 页面抓取+JSON解析 | ~1s | JS undefined→null修复 |
| 封面图下载 | ~1s | 装饰图，无额外信息 |
| Vision识图 | ~2s | 确认封面无实质内容 |
| 5个GitHub API查询 | ~12s | 含README解码（gbrain的base64编码有控制字符，需清理） |
| 文件结构拉取 | ~8s | gbrain 43个skill目录遍历 |
| **总计** | **~25s** | |
