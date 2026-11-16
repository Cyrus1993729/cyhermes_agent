# Kilo Pass / OpenDesign Pro 的 Opus 5.5 换算实测（2026-11-09）

用户问题：「Kilo 的 pass 套餐和 OpenDesign 的 pro 套餐，买的话能用多少 Opus 5.5」。
本文件是那次现抓的全部数字，问聚合站 × 旗舰模型的同类问题时可直接复用，不必重新抓。

抓取时间 2026-11-09，来源：`kilo.ai/pricing/kilo-pass`、`kilo.ai/pricing`、`kilo.ai/models/anthropic-claude-opus-5-5`、`open-design.ai/pricing`、`go.open-design.ai`、`open-design.ai/help/billing`、`cloudzero.com/blog/claude-opus-pricing`（交叉验证）。

---

## 一、Opus 5.5 官方单价（2026-09-22 发布，是 Opus 5 的 20% 降价）

| 项 | $/1M tokens |
|---|---|
| 输入 | $4.00 |
| 输出 | $20.00 |
| 缓存读 | **$0.20**（比 Opus 5 的 $0.50 降 60%） |
| 缓存写（5 分钟） | $5.00 |
| 缓存写（1 小时） | $8.00 |
| Fast mode | $8 / $40 |
| Batch | $2 / $10 |

上下文 1M（无长上下文附加费），最大输出 128K，知识截止 2026-06。
模型 ID：`claude-opus-5-5`；OpenRouter/Kilo slug：`anthropic/claude-opus-5.5`。

⚠️ Opus 5 及 4.x 系列仍是 $5/$25 —— 拿旧文写"Opus $5/$25"会低估 5.5 的性价比。

---

## 二、本机用量画像（换算的分母，2026-11-09 从 state.db 取）

| 口径 | 调用次数 | 非缓存输入/次 | 缓存读/次 | 输出/次 | 单次 Opus 成本 |
|---|---:|---:|---:|---:|---:|
| **近 30 天（推荐用这个）** | 8,315 | 6,470 | 128,780 | 910 | **$0.070** |
| 全历史（23,691 次） | — | 4,800 | 114,850 | 863 | $0.059 |

🔴 **两个口径差 17%，别混用**。全历史含早期短会话，单次输入偏小；近 30 天是当前真实负载（长上下文 agent 常态）。做"套餐够不够"的结论时用近 30 天。

**关键结论：我们近 30 天全部换成 Opus 5.5 ≈ $581/月。** 这个数就是判断任何套餐"够不够"的分母。

计算式（可直接复用）：
```
单次成本 = (非缓存in×4 + 缓存读×0.2 + out×20) / 1e6
         = (6470×4 + 128780×0.2 + 910×20)/1e6 = $0.06984
```
注意缓存读 $0.20 便宜，我们这种高缓存命中画像下 Opus 只比 DeepSeek V4.1 Flash 贵约 10 倍（不是直觉的 30-50 倍）。

---

## 三、Kilo Pass（充值型，无价格折扣）

### 机制
- 订阅额 **1:1 转成 paid credits**（真美元，不是换算点数），按 provider list price 消耗，**零加价**
- 另送 bonus credits，但：
  - **必须先把这个月的 paid credits 用完才发放**
  - **月末作废**（不滚存）；paid credits 1 年后过期
  - 月付梯度：第 1 月 **10%** → 第 2 月 **50%** 欢迎奖（仅首次订阅）→ 第 3 月起按 tier+streak 爬升 → **第 8 个月封顶 40%**
  - 年付：**每月 50%**，无梯度
- **5% 处理费**（一次性充值、自动充值、月付/年付 Pass 都收；Teams/Enterprise 席位与对公转账不收）。例：$20 credits 实付 $21
- **无速率限制**：paid 模型没有 5 小时 / 周 / 月窗口，credits 花光为止
- 500+ 模型通用，含 Anthropic——Anthropic 2026-01 封的是**第三方 OAuth**（Claude Pro/Max 订阅令牌），Kilo 走 API key 计费不受影响

### 三档与 Opus 5.5 换算

| 档位 | 月费 | 月付封顶额度 | Opus 调用/月 | 占我们月用量 | 实付 | 杠杆 |
|---|---:|---:|---:|---:|---:|---:|
| Starter | $19 | $26.60 | ~380 次 | 4.6% | $19.95 | 1.33× |
| Pro | $49 | $68.60 | ~980 次 | 11.8% | $51.45 | 1.33× |
| Expert | $199 | $278.60 | ~3,990 次 | 48% | $208.95 | 1.33× |
| Expert 年付 | $199/mo（$2,388/年） | $298.50 | ~4,270 次 | 51.4% | — | **1.5×** |

> 杠杆 = 等效额度 ÷ 实付。年付无额外折扣，只把 bonus 从 40% 拉到 50%。

---

## 四、OpenDesign Pro（额度型，有真折扣）

### 档位与 Opus 5.5 可用性

| 档位 | 月付 | 年付（月均） | Design Plan 额度 | plan-model 额度 | Opus 5.5 |
|---|---:|---:|---:|---:|---|
| Go | $10 | $7 | $220 | **$0** | ❌ Not included |
| Go Plus | $20 | $14 | $290 | $20 | ❌ **Not included** |
| **Go Pro** | **$100** | **$60**（$720/年） | $360 | **$120**（限时 20% bonus，原值 $100） | ✅ |
| Go Max | $200 | $98 | $600 | $300（限时 50% bonus） | ✅ |

- **Opus 5.5 / Claude Fable 5.1 / GPT-6 Astra 三个旗舰在 Plus($20) 上明确标 `Not included`** —— 便宜档买不到，这是最容易踩的坑
- Opus 5.5 属于 **plan models**，只能用 plan-model 池；卡片上的 Design Plan $360 对它**无效**
- **plan-model credits 无 5 小时 / 7 天窗口**（有窗口的只有 Design Plan / Coding Plan 池）
- 两池**单向溢出**：Design Plan 花完可动用剩余 plan-model credits；反之不行
- `Design Plan multiplier` 只作用于 Design Plan credits，**不适用于 plan-model credits**（后者的 $ 值 1:1 按模型原价扣）
- 按账单周期清零，不滚存；API 与 App 共用同一池，换工具/换 key 不会多给额度

### Opus 5.5 换算（Pro 档）

| 购买方式 | 月均成本 | 月额度 | Opus 调用/月 | 占我们月用量 | 杠杆 |
|---|---:|---:|---:|---:|---:|
| 月付 | $100 | $120 | ~1,720 次 | 20.7% | 1.20× |
| **年付** | **$60** | $120 | ~1,720 次 | 20.7% | **2.00×** |

⚠️ 限时 20% bonus 结束后回落为 $100/月额度 → 年付杠杆变 1.67×（仍是最高的）。

---

## 五、结论口径（当时怎么回答的）

杠杆率排序：**OpenDesign Pro 年付 2.0× > Kilo 年付 1.5× > Kilo 月付 1.33× > OpenDesign Pro 月付 1.2×**

三句话：
1. 想多跑 Opus 5.5 → OpenDesign Pro 年付最优（$60/月拿 $120/月 ≈ 1,700 次），但只够我们月用量 1/5
2. 想全模型自由切换 + 零加价 + 无速率限制 → Kilo Expert 年付（$199/月拿 $298.50 ≈ 4,270 次，覆盖 51%）
3. 想覆盖日常全量（$581/月）→ 两家都给不了，只能官方 API 直连或 Claude Max 订阅

两条附注（答复必须带上）：
- Anthropic 称 Opus 5.5 完成同任务用的 token 比旧版少约 40% → 上面的次数是偏保守的下限
- 两家都能接进 Hermes：OpenDesign 支持 Anthropic Messages 协议，Kilo Gateway 是 OpenAI 兼容

---

## 六、HTML 解析要点（这两家的页面都不好抓）

- 两家都是 Next.js / Astro **客户端渲染**。`kilo.ai/pricing*` 整页 grep `opus` → **0 命中**，但这不代表模型不可用
- **拿单价** → 抓单模型详情页：`kilo.ai/models/<provider>-<model>`。价格在 `Model ID / Input Price / Output Price / Cache Read Price / Cache Write Price` 这组 `<dt>/<dd>` 里，另有 JSON-LD 的 `PriceSpecification` 可交叉验证
- **拿档位归属** → 按容器顺序切 block（OpenDesign 是 `<ul ... data-astro-cid-7hyp2lxo>`，先找起始标签再找匹配的 `</ul>`），然后看**前一个 block 的 header 文本**：`Plan models Not included` / `Standard · $20/month` / `6× · $120/month`。只看模型名列表会误判哪一档开放
- **拿额度表** → `go.open-design.ai` 的额度对比是**真 `<tr>` 表**，按格解析可靠；`open-design.ai/pricing` 的模型估算表是 div 结构，`<tr>` 返回 0，要去标签后按顺序读（GLM 行 = 三档 go/plus/pro/max 的估算请求数 + 额度）
- **FAQ/机制说明**在 `<script type="application/ld+json">` 的 `Question`/`Answer` 里（Kilo Pass 页有 21 条，含 5% 处理费、bonus 梯度、credits 过期规则）——比正文可靠，直接 `json.loads` 后 `walk()` 抽
- 额度条款的权威出处是 **help 页**（`open-design.ai/help/billing`），定价页只给数字不给规则
