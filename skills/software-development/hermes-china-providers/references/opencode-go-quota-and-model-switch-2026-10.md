# OpenCode Go 额度快照 + 换主模型实录（2026-10-08）

数据源：**fresh curl 原始 HTML**（`curl -x http://127.0.0.1:10808 -H "User-Agent: curl/8.0.0" https://opencode.ai/docs/go/`），不是 web_extract。
（web_extract 有返回缓存旧版的实踩记录，核实定价/额度一律 fresh curl。）

## 本次任务

用户："帮我把模型切到 deepseek v4.1 flash（作为主模型）"。
执行结果：`model.default: deepseek-v4-flash → deepseek-v4.1-flash`（provider / base_url 不动），
端到端验证通过（新会话 `20261008_095615_a5c301` 在 state.db 中记为
`model=deepseek-v4.1-flash, billing_provider=opencode-go, billing_base_url=https://opencode.ai/zen/go/v1`）。

## Go $10 档额度表（2026-10-08 抓取，单位：token 价 $/1M；额度 = 该模型的月 $ 上限）

| 模型 | Off-Peak in | Off-Peak out | cache read | Peak in | Peak out | cache read | 月额度 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| DeepSeek V4.1 Flash | $0.15 | $0.60 | $0.003 | $0.30 | $1.20 | $0.006 | **$60** |
| DeepSeek V4 Flash | $0.15 | $0.60 | $0.003 | $0.30 | $1.20 | $0.006 | **$30** |
| DeepSeek V4 Flash Vision Exp | $0.15 | $0.60 | $0.003 | $0.30 | $1.20 | $0.006 | $15 |
| DeepSeek V4 Pro | $0.66 | $1.98 | $0.022 | $1.32 | $3.96 | $0.044 | $15 |

**V4.1 Flash 与 V4 Flash 单价逐列相同，但月额度翻倍。**

## 请求数估算（Go $10 档，文档"典型 Go 用量模式"折算）

| 模型 | 5 小时 | 每周 | 每月 |
|:--|:--|:--|:--|
| DeepSeek V4.1 Flash | 26,000 | 65,000 | **130,000** |
| DeepSeek V4 Flash | 13,000 | 32,500 | **65,000** |
| DeepSeek V4 Flash Vision Exp | 6,500 | 16,250 | 32,500 |

典型 token 模式（文档给出）：V4.1 Flash / V4 Flash 均为 **410 input + 71,300 cached + 310 output** tokens/请求。
同一模式也适用于 V4 Pro，但 Pro 是 750 input + 82,000 cached + 290 output。

## 峰谷时段

文档原话：Peak hours are **01:00-04:00 and 06:00-10:00 UTC, Monday through Friday**；
其余时间（含整个周末）为 Off-Peak。
→ 北京时间 **09:00-12:00 + 14:00-18:00 工作日** 为 Peak（价格 ×2）。
注意这与早期记录的"北京 9-12/14-18"一致，但**周末全 Off-Peak** 值得利用。

## 网关模型目录（2026-10-08 实测，Go key 可用）

`GET https://opencode.ai/zen/go/v1/models` 返回 36 个模型，本次相关的新面孔：
`deepseek-v4.1-flash`、`deepseek-flash`、`deepseek-v4-flash-vision-exp`、`grok-4.7`、
`gpt-6-luna`、`glm-5.3-flash`、`mimo-v2.6-flash` / `mimo-v2.6-pro`、
`longcat-2.5-preview-free`、`minimax-m2.7`、`qwen3.8-flash`、`muse-spark-1.3-contributor`。

**目录会变**——指定模型名前先拉一次，别照抄旧清单。

## 兜底渠道体检（同日实测，发现隐患）

```bash
KEY=$(grep -m1 "^DEEPSEEK_API_KEY=" ~/AppData/Local/hermes/.env | cut -d= -f2-)
curl -s --noproxy '*' -H "Authorization: Bearer $KEY" https://api.deepseek.com/v1/models
# → ['deepseek-flash', 'deepseek-v4-pro']   ← 没有 deepseek-v4-flash
```

对 `deepseek-v4-flash` 和 `deepseek-flash` 各发一次 chat/completions，两个都返回：

```json
{"error":{"message":"Insufficient Balance (request_id: ...)","type":"unknown_error",
 "param":null,"code":"invalid_request_error"}}
```

结论：`fallback_providers[0]`（provider: deepseek，model: deepseek-v4-flash，内联 api_key）
**当前不可用**——账号余额为 0，且引用的模型名已不在官方目录。8/16 配置时它验证通过，
之后官方改名 + 余额耗尽，静默失效。

🔴 通用教训：**fallback 是"薛定谔的备胎"**——没有触发告警时，配错/失效的第一层会被第二层
静默接住或直接失败在故障当天才暴露。定期对兜底渠道发一次真实请求，比检查配置存在性有效得多。

## 本次踩到的操作坑

1. **漏 `x-opencode-session` → 400 MissingSessionID**：临时 ad-hoc curl 也必须带（`hermes-check-<ts>` 之类固定值即可），不只是仓储里的 5 个脚本。
2. **MSYS 路径**：`curl -d @/tmp/t41.json` 报 `curl: option -d: error encountered when reading a file`——原生 curl 不认 MSYS 路径。`cd` 到目标目录用相对文件名即可。
3. **`hermes -z ... --cli < /dev/null` 不写 `logs/agent.log`**：跑完 agent.log 里没有它的 API call 记录，容易误判"没生效"。真相源是 `state.db` 的 `session_model_usage`。
4. **config 缓存键 = (mtime_ns, size)**（`hermes_cli/config.py:3883`）→ 改配置无需重启 gateway；但已建好的 agent 实例仍持旧模型，需 `/reset`。

## 后续：全量换名实操（同日，用户拍板"把所有原来用 v4flash 的地方都改成 v4.1flash"）

两个未决项当天都拍了：
- ✅ `cron.model` → `deepseek-v4.1-flash`（同价双倍额度，纯白赚）
- ✅ fallback 的**余额问题不动**（用户明确"暂时不用管"），但模型名改了 → 见下

### 实际改了 8 处（清单比"四步换主模型"里列的更长）

| # | 位点 | 改成 |
|:--|:--|:--|
| 1 | `config.yaml` `model.default` | `deepseek-v4.1-flash` |
| 2 | `config.yaml` `cron.model` | `deepseek-v4.1-flash`（4 个 agent 型 cron 全跟） |
| 3 | `config.yaml` `fallback_providers[0].model` | **`deepseek-flash`**（官方 ID，不是 `deepseek-v4.1-flash`） |
| 4 | `scripts/api_probe.py`（注释 + model） | `deepseek-v4.1-flash` |
| 5 | `scripts/api_healthcheck.py`（注释 + model） | `deepseek-v4.1-flash` |
| 6 | `scripts/usage_watch.py`（注释 + SQL + 文案 + **价格表 + 档位**） | `deepseek-v4.1-flash` / 现价 / `$60` |
| 7 | `cron/jobs.json`（**prompt 正文文本** 6 处） | `deepseek-v4.1-flash` |
| 8 | `models.json`（桌面端自定义模型）+ `D:\Workspace\Projects\TrendRadar\config\config{,.en}.yaml` | `deepseek-flash` / `deepseek/deepseek-flash` |

### 新挖出的三类位点（原有的扫描清单没覆盖）

1. **`cron/jobs.json` 的 prompt 散文** —— 不只是 model 字段。日报 prompt 里写着"用当前模型（deepseek-v4-flash）生成"，漏改会把旧模型名灌回模型上下文。改法：备份 → 纯文本 replace → `json.load` 校验 + 逐 job 打印行数（本次 14 个 job 无损）。
2. **监控脚本里硬编码的价格表** —— `usage_watch.py` 还是 8/17 那版价格（比 10/8 现价高 1.5×，**缓存读高 2.3×**）和 `$30` 档。这类数字不会自己过期报错，会静默让预警失真。**换模型时顺手 fresh curl 官方价表核对一次**。
3. **`model LIKE '%flash%'` 这类模糊 SQL** —— 新模型多了会连带统计 `mimo-v2.6-flash` / `qwen3.8-flash` / `glm-5.3-flash`。收窄成显式 `model IN ('deepseek-v4-flash','deepseek-v4.1-flash')`（保留旧名以纳入历史行）。

### 官方 API 模型 ID（本次硬核结论）

- 官方现行 ID：**`deepseek-flash`**（= DeepSeek-V4.1-Flash）与 `deepseek-v4-pro`
- 官方文档原话：`deepseek-v4-flash` / `deepseek-v4-flash-vision-exp` "are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price"
- 官方侧**不存在** `deepseek-v4.1-flash` —— 网关名不能照抄
- 🔴 **余额为 0 时探针无法验证模型名**：余额校验先于模型名校验，瞎编的模型名也返回同一句 `Insufficient Balance`。判据 = 假名与真名报错完全相同 ⇒ 探针无效，改查 `/v1/models` 或官方文档页

### 验证结果（都实跑过）

- `python scripts/api_probe.py` → `OK 1.6`
- `python scripts/api_healthcheck.py` / `usage_watch.py` → 静默（正常态）；强制打印用量得 **$3.9–7.9 / $60 = 7%–13%**
- 独立会话 `20261008_111945_b44d59` → state.db 记 `deepseek-v4.1-flash / opencode-go`
- **正在进行的那个会话自己就切过去了**：state.db 同一 session_id 下早期 3 次调用记 `deepseek-v4-flash`、之后的记 `deepseek-v4.1-flash` ⇒ 实测坐实"config 缓存按 mtime 失效，无需重启 gateway"
- `hermes config get model.default` / `cron.model` 均返回 `deepseek-v4.1-flash`
- cron 侧首个真实生效点 = 当晚 20:30 跨境日报（agent 型），21:00 投递检查一并确认

### 遗留（下次接手先看）

- `skills/video-understand-core/scripts/pipeline.py` 等技能附属脚本**本次未扫到**（扫描被 `head -20` 截断）——用 `scripts/scan_model_references.py` 复核
- MoA 的 aggregator/reference 仍是 `deepseek-v4-pro`（AA 分 36 < V4.1 Flash 的 39，且是 $15 档）——建议改，用户未拍板
- DeepSeek 官方账号余额仍为 0，fallback 第一层依旧不可用
