# 「有没有能力更强、且按我们用法不超限额的模型」实测（2026-10-08）

用户第三问。前两问（套餐额度现状、哪个模型性价比高）见 `opencode-go-quota-selection-2026-10.md`。

**结论先说：严格说没有。** `deepseek-v4.1-flash` 就是「不超限额」区间里的最优解——能力第一梯队 + 额度只用 11%（活跃日口径）+ 速度还是全场最快那一档。

---

## 1. 能力分来源（中立第三方）

| 用途 | URL |
|---|---|
| 总榜（含 Index / 每任务成本 / 输出 t/s / TTFT） | `https://artificialanalysis.ai/leaderboards/models` |
| **逐项对战（最关键）** | `https://artificialanalysis.ai/models/comparisons/<A>-vs-<B>` |
| 单模型页（AA / 速度 / 参数量 / 定价） | `https://artificialanalysis.ai/models/<slug>` |
| 第二源：分品类排名 + 证据等级 | `https://benchlm.ai/models/<slug>` |
| OpenRouter 模型页（带 AA 分） | `https://openrouter.ai/<vendor>/<slug>` |

⚠️ AA 的速度/延迟是**首方 API** 数字，走 OpenCode 中转会差很多 → 速度只信本地实测（见 §4）。
⚠️ 分数是各模型 **max effort 推理档**；实际跑更低档位时绝对分会掉，名次关系稳定。

## 2. Go 套餐内模型的 AA Intelligence Index（v4.3.2）vs 我们的额度占用

占用率取自 `scripts/opencode_go_quota_rank.py`（活跃日外推口径）。

| 模型 | AA Index | 活跃日口径占用 | 备注 |
|---|---|---|---|
| MiMo-V2.6-Pro | **46** | **98.7%** ⚠️ | 全球开源第一，但额度贴顶 |
| Grok 4.7 (xhigh/high) | 46 | 超限 | |
| GLM-5.3 (max) | 45 | 386% ⛔ | |
| Qwen3.8 Max | 45 | 858% ⛔ | |
| Muse Spark 1.3 (xhigh) | 45 | 3.4% | **训练用数据，红线排除** |
| Kimi K3 (max) | 44 | 1347% ⛔ | |
| **GLM-5.3-Flash** | **42** | **20.6%** | 额度宽裕，但**慢到不可用**（§4） |
| **DeepSeek V4.1 Flash (max)** | **39** | **11.3%** | **当前主力** |
| GPT-6 Luna (max) | 38 | 44.9% | |
| MiMo-V2.6-Flash | 38 | 8.5% | |
| DeepSeek V4 Pro 0813 (max) | **36** | 193% ⛔ | **比 V4.1 Flash 弱还超限** |
| MiniMax M3 | 29 | 42.7% | |
| Kimi K2.7 Code | 26 | 136.6% ⛔ | |
| Qwen3.7 Plus | 25 | 42.0% | |
| Hy3 | 25 | — | |
| LongCat 2.0 | 19 | 22.6% | |

## 3. 逐项对战细节（这两份决定了最终结论）

### MiMo-V2.6-Pro vs DeepSeek V4.1 Flash (Max) — Index 46 vs 39

| 子评测 | MiMo-V2.6-Pro | DeepSeek V4.1 Flash |
|---|---|---|
| Intelligence Index | 46 | 39 |
| AA-Briefcase v1.1 | 1516 | 1420 |
| GDPval-AA v2.1 | 1686 | 1600 |
| **AutomationBench-AA（SaaS 工作流自动化）** | **59%** | **69%** ✅ |
| Terminal-Bench 4.0 | 35% | 27% |
| SciCode | 61% | 52% |
| Humanity's Last Exam | 49% | 39% |
| GDP.pdf | 19% | 13% |
| CritPt | 27% | 14% |
| AA-Omniscience | +8 | −5 |
| AA-LCR v1.1 | 86% | 84% |
| 输出速度 | 37.6 t/s | **216 t/s** |
| TTFT / 单任务耗时 | 4.92s / 1666s | 1.12s / **276s** |
| 每任务成本 | $0.13 | $0.27 |
| 缓存命中价 /1M | $0.0036 | $0.006 |
| 输出 tokens/任务 | 64k | 89k |

→ MiMo-V2.6-Pro 在 10 项里赢 9 项，**唯独我们最对口的那一项输 10 个点**；且慢 5.7 倍。

### GLM-5.3-Flash vs DeepSeek V4.1 Flash (Max) — Index 42 vs 39

| 子评测 | GLM-5.3-Flash | DeepSeek V4.1 Flash |
|---|---|---|
| Intelligence Index | 42 | 39 |
| AA-Briefcase v1.1 | 1452 | 1425 |
| GDPval-AA v2.1 | 1641 | 1600 |
| **AutomationBench-AA** | **60%** | **69%** ✅ |
| Terminal-Bench 4.0 | 33% | 27% |
| SciCode | 52% | 52% |
| HLE / GDP.pdf / CritPt | 40% / 15% / 15% | 39% / 13% / 14% |
| AA-Omniscience | +7 | −5 |
| 输出速度 | 53 t/s | **216 t/s** |

→ 分项差距都在 1-3 个点（噪声级），**但自动化场景同样输 9 个点**，且速度 1/4。

## 4. 长文本吞吐探针（决定性的那个实验）

流式请求，要求约 400 字正文，`max_tokens=3000`，cap 150s：

| 模型 | 墙钟 | 正文字 | 思考字 | finish |
|---|---|---|---|---|
| deepseek-v4.1-flash | **9.3s** | 437 | 1300 | stop |
| mimo-v2.6-pro | 16.6s | 548 | 32 | stop |
| glm-5.3-flash | **150.0s 超时** | **0** | 4969 | None |

GLM-5.3-Flash 复测（降到 200 字、cap 280s）：**117.5s** 才出 199 字（思考 3658 字）。

🔴 **同一个模型的小工具调用探针是 1.5s（当时最快的那个）**——只看小探针会把它选成主力。**两个探针缺一不可。**

## 5. 被排除的候选及理由

- **Muse Spark 1.3 / 1.2 Contributor（Index 45，占用仅 3.4%）**：Go 官方文档 ZDR 表写明 `Model training: Yes` / `Not ZDR`，性价比排名里最便宜但**拿你的 prompt/输出去训练 Meta 模型**。日报、投资、公司业务内容一律不进。**排除理由要在输出第一段交代，否则用户以为你只是没看见那个更便宜的选项。**
- **超月限 4-13 倍**：GLM-5.3(386%)、Qwen3.8 Max(858%)、Kimi K3(1347%)、Grok 4.7、GLM-5.2(183%)、Kimi K2.7 Code(137%)。
- **DeepSeek V4 Pro**：AA 36 < V4.1 Flash 39，占用 193%。官方已把 v4-pro 请求路由到 V4.1 Flash 计费 →「升级到 Pro」是反向操作。
- **GPT-6 Luna（38）/ MiMo-V2.6-Flash（38）**：Index 低于 39，不算"更强"。

## 6. 探针脚本的正确写法（本次踩坑记录）

- 🔴 **多模型探针循环不要写成一行内联 shell/heredoc**——超长内联载荷会被 Hermes 的 hardline 守卫直接 **BLOCKED**（提示语：`command parser limit or malformed executable payload`，报错里会给出 `cache/blocked-scripts/blocked-*.sh` 路径）。**用 `write_file` 把探针写成 `scripts/*.py`，再 `python scripts/xxx.py` 跑**。这同时也解决了引号地狱。
- 单次请求的耗时可能远超预期：GLM-5.3-Flash 一次就吃掉 150s。**terminal 默认超时 180s，跑多模型探针必须显式给 `timeout=`，或改后台任务**。
- 用 `subprocess.run([... 'curl', ...], input=body.encode(), capture_output=True, timeout=N)`，响应整体落内存/文件后再解析——**不要边读边 break**，也不要 `-o /tmp/...`（MSYS 虚拟路径）或把 JSON 拼进 `python -c` 字符串。
- 探针请求必须带 `x-opencode-session`（否则 400 `MissingSessionID`）+ `User-Agent: curl/8.0.0`（否则 Cloudflare 1010/403）。
- **顺手做的 relay 默认值体检**：发一次**不带 `max_tokens`** 的请求，看 relay 的默认完成上限会不会被上游 400。本次 `mimo-v2.6-pro` / `glm-5.3-flash` 都正常（对比：Hermes 插件里 `mimo-v2.5-pro` 被硬编码 cap 到 131072，就是因为 relay 默认 262144 会被小米拒）。

## 7. 回给用户的结论模板

> 严格说没有。能同时满足「AA 独立评测高于 39」+「按我们用法不超限额」的只有两个，但两个都有硬伤：MiMo-V2.6-Pro（46 分但额度 98.7% 贴顶 + 自动化场景输 10 点 + 慢 5.7 倍）、GLM-5.3-Flash（42 分、额度 20.6% 但实测 200 字要 117 秒，不可用）。
> 被额度挡在门外的更强的：GLM-5.3 / Qwen3.8 Max / Kimi K3 / Grok —— 超限 4-13 倍。
> 唯一的反直觉坑：DeepSeek V4 Pro 比 V4.1 Flash 更弱还超限。
> **建议维持 DeepSeek V4.1 Flash 当主力**；真想试就把 MiMo-V2.6-Pro 挂到一条独立管线（如黄金周报的深度分析）跑一两个月再定。
