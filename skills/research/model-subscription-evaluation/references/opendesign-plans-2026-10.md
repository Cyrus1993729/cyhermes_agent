# OpenDesign 档位与额度（2026-10-25 fresh curl 实抓）

来源：`https://open-design.ai/pricing/`、`https://open-design.ai/model-credits/`（中文版 `/zh/model-credits/`）。
归属：Powerformer, Inc.；项目本体是 nexu-io/open-design（Apache-2.0），套餐是它的托管云。
触发场景：用户问「OpenDesign 套餐能不能用 XX 模型 / 和 Claude 官方比额度」。

## 一、四档真实价格与额度

| 档位 | 月付 | 年付折月 | 每月总额度 | 套餐模型额度（无 5h/7天窗口） | Design Plan 月额度 | Design Plan 7天窗口 | Design Plan 5h 窗口 |
|---|---|---|---|---|---|---|---|
| Go | $10 | $7（$84/年） | $120 | **$0** | $120 | $30 | $10 |
| Plus | $20 | $14（$168/年） | $180 | **$20** | $160（赠送） | $40 | 不设 |
| Pro | $100 | $60（$720/年） | $480 | **$120**（限时加赠 20%，原 $100） | $360（赠送） | $90 | 不设 |
| Max | $200 | $98（$1,176/年） | $900 | **$300**（限时加赠 50%） | $600（赠送） | $150 | 不设 |

校验规律：Design Plan 7 天窗口 × 4 ≈ 月额度（Go 30×4=120、Plus 40×4=160、Pro 90×4=360、Max 150×4=600）。看到不相符就是解析串列了，回去重解表格。

## 二、哪些模型在哪个档位（决定性事实）

**Go**：套餐模型额度 $0 → 所有套餐模型一律不可用，只有 Design Plan 那 12 个便宜模型（Haiku 5.5 / GPT-6 Luna / DeepSeek V4.x / GLM-5.3 / MiMo / Hunyuan H4 / Kimi K2.7 Code）。

**Plus ($20)**：卡片上明确 `Not included` 的三个 ——
- GPT-6 Astra
- Claude Fable 5.1
- **Claude Opus 5.5** ← 用户最常问的就是这个

Plus 实际能用：GPT-6 Sol、Muse Spark 1.3、Gemini 4 Argon、Kimi K3、Grok 4.7、Gemini 3.8 Flash、Claude Sonnet 5.5、Seedream 5 Lite/Pro、Nano Banana 2、GPT Image 2（图像类 Plus 上限 Up to 1K）。

**Pro ($100) / Max ($200)**：上表 13 个套餐模型全含，无 `Not included`。

→ **想用 Opus 5.5 的最低门槛 = Pro，$100/月（年付 $60/月）**。$20 档做不到。

## 三、额度怎么扣

- 套餐模型：**直接按套餐模型额度扣，不受 5 小时 / 7 天窗口限制**，按计费周期发放与重置。
- Design Plan 模型：先扣 Design Plan 赠送额度，用尽后自动转扣套餐模型额度；额度全空则停（除开启自动充值）。
- Design Plan 有倍率：DeepSeek V4.1 Flash 0.5×（限时谷价 0.25×，2026-10-20 18:00 至 10-27 18:00 UTC+8）；MiMo/Hunyuan/DeepSeek V4 Flash/V4 Pro/GLM-5.3 Flash/Kimi K2.7 Code 1×；Claude Haiku 5.5 2×；GLM-5.3 Flash-X、GPT-6 Luna 4×。**倍率只作用于 Design Plan 额度**。
- 额度非现金余额、非固定请求数；OpenDesign 站内用量与 API Key 外部调用共用同一份额度，外部调用不额外发放、不重置窗口。
- 支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种协议，可接 Codex、Claude Code、OpenCode、Hermes。

**推断（文档未明说，需标注）**：套餐模型按官方 API 价 1:1 消耗额度（无倍率）。若成立，Pro 的 $120 ≈ $120 的 Opus 5.5 API 用量。

## 四、Opus 5.5 换算（官方价 $4 输入 / $20 输出 / $0.20 缓存读，$/1M）

| 额度 | 纯未缓存输入 | 纯输出 | 典型 agent 调用（200K 上下文 / 98% 缓存命中 / 1K 输出 ≈ $0.075/次） |
|---|---|---|---|
| $20（Plus，但 Opus 不可用） | 5M tok | 1.0M tok | ~266 次 |
| $120（Pro） | 30M tok | 6.0M tok | ~1,600 次 |
| $300（Max） | 75M tok | 15.0M tok | ~3,990 次 |

## 五、对照：Claude 官方 Pro（$20/月）

- Opus 5.5 **直接包含**（2026-09-22 起；Free 档不含，只有 Sonnet/Haiku 级）。
- 官方**不公布** token/金额额度。结构 = 滚动 5 小时窗口 + 每周上限，与网页版/Claude Code 共用同一池；Opus / Fable 有单独的周上限。
- 相对锚点只有：Pro ≥ 5× 免费版每会话；Max 5x = 5× Pro；Max 20x = 20× Pro。
- 第三方实测（口径差很大，均非官方）：博客园 2026-06 用 Sonnet High 测得 5h 窗口约 **$18** API 等值、一周约 10 个窗口 ≈ **$180/周**；另一份 GitHub 实测记录推出 5h ≈ $100、周限 ≈ $1,000。
- Anthropic 自述：Opus 5.5 典型工作负载比 Opus 5 便宜约 40%，同一订阅可多用约 25%。

## 六、结论模板（同预算比较）

1. 先纠正前提：$20 档拿不到 Opus 5.5。
2. 给出真实门槛：Pro $100/月（年付 $60）＝ $120/月套餐模型额度，无窗口。
3. 正面 $20 对比：Claude Pro 在模型档位上完胜（Opus/Fable/Claude Code 全有），OpenDesign Plus 只给替代模型 + $160 Design Plan。
4. 说明口径差异，别硬凑一个数字：订阅＝不透明但 API 等值远超月费；聚合站＝明码可预算、无 5h 墙。
5. 最后问是否要按 state.db 真实用量折算「够跑多少天」，把决策权交回用户。

## 七、🔴「1:1 是不是官方 API 原价」——官网查不到，只能实测（2026-10-26 用户追问）

用户会接着问：**「那 $120 是按官方 API 的价格去算用量吗？」**

**答案分两半，缺一不可：**

**① 官网所有页面都没有套餐模型的单价。**（已穷尽：`/pricing/`、`/model-credits/`、`/zh/model-credits/`、`/faq/`、`sitemap-pages-0.xml`、`sitemap-blog-0.xml`）
→ 推 API 端点想拿模型表也全是 404：`/api/v1/models`、`/v1/models`、`/zen/v1/models`、`/api/models`。
→ **能给用户的肯定性事实只有：额度是美元计价、Design Plan 有倍率、套餐模型无倍率。**

**② 推理链可以给，但必须标「推断」：**
- 额度体系全部美元计价（$480 = $120 + $360 对得上）
- 文档原话「倍率越低，同等**模型使用金额**消耗的 Design Plan 额度越少」——底层量纲就是「模型用量美元」
- 套餐模型**不列倍率** → 1× → 直扣
- 同类平台（OpenCode Zen、Kilo Gateway）都是按官方 API 价扣、不加价不打折

**③ 给用户一个 5 分钟、不到一毛钱的自测法（比任何推断都可靠）：**

```
1. 用 API Key 对目标模型发一次最小请求，记下返回的 input/output/cache token 数
2. 去控制台看这次扣了多少额度
3. 单价 = 扣费金额 ÷ token 数，拿去对官方价（Opus 5.5 是 $4 / $20 / $0.20 per 1M）
   对得上 = 1:1 原价；对不上就知道加了多少价
```

> **这才是判断「值不值」的真正依据。** 纯靠官网推断最多只能定方向，不能定价格。

## 八、抓取方法复盘

- 定价页与额度页都是 Astro 站，**数据就在 HTML 里**，`curl -sL` 即可，不必用浏览器。
- 🔴 **表格必须按 `<tr>`/`<t[hd]>` 逐格解析**。直接把标签剥成纯文本会让列串位：
  本次英文页与中文页都曾把 Plus 的「套餐模型额度 $20」显示成 $160（$160 其实是 Design Plan 额度），
  靠「7 天窗口 × 4 ≈ 月额度」这条自检才发觉得到纠正。
- **文案拷贝与实情可能冲突**：hero 区写 `PRO $20 / MAX $100 / +$20 / +$100`，看着像降价，
  实际是「限时加赠 $20/$100 credits」。要抓相邻的 `Limited-time bonus credits` 才定得死。
- 中文页 `/zh/` 一般更完整（英文页偶尔漏列几行）。

