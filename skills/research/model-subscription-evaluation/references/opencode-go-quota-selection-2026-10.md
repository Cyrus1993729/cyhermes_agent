# OpenCode Go 额度与模型选型实测（2026-10-08）

本次任务：用户问"opencode go 套餐最新的额度，用哪个模型性价比高"。本文件是可直接复用的数据 + 方法。

## 0. 数据新鲜度证据（涉及价格/额度的结论必须能自证新鲜）

```bash
cd ~/AppData/Local/hermes
curl -s --max-time 40 -x http://127.0.0.1:10808 \
  -H "User-Agent: curl/8.0.0" -D go_headers.txt \
  https://opencode.ai/docs/go/ -o go_docs.txt
grep -i '^date:' go_headers.txt          # 服务器时间戳，证明不是缓存
```

- 本次证据：`Date: Thu, 08 Oct 2026 02:05:18 GMT`（北京 10:05），HTML 含 `Off-Peak/Peak` 价格列 + `Go Plus` 计划 → 确认新版
- 🔴 **不要用 web_extract 抓 opencode 文档**——会返回旧版缓存（2026-08-17 已踩过一次，代价是给出错误结论被用户纠正）。一律 fresh curl 原始 HTML
- 表格解析：`<table>` → `<tr>` → `<t[hd]>` 正则剥标签。该页共 9 张表（计划 / 客户端 session 支持 / 价格 Go / 价格 Go Plus / 请求数估算 Go / 请求数估算 Go Plus / 端点 / 模型 ID / 训练+保留政策），**每张都要看**，ZDR 表在最后一张

## 1. 套餐结构（2026-10-08）

- **Go $10/月**；**Go Plus $40/月**——单价**完全相同**，只是每模型月额度翻倍
- 额度 = **每模型独立的月度 $ 池**；拆分规则：**5h = 月额度 20%、周 = 50%、月 = 100%**
- 单价按每 1M token；console 开 `Use balance` 后撞限回退 Zen 余额；不开启则撞限后只能继续用免费模型
- 峰段：**UTC 01:00-04:00 和 06:00-10:00 周一~周五** = 北京时间 **09-12 / 14-18**；其余时段含周末全 Off-Peak（仅 DeepSeek 系分峰谷）
- DeepSeek 系 **ZDR 协议有效期 2026-10-31**（此前手记的 8/31 已过时）
- 免费档：`LongCat 2.5 Preview Free` — $0、不限量（限时）

## 2. $10 Go 计划全模型价格表（$/1M tokens）

| 模型 | Input | Output | Cached Read | 月额度 |
|---|---|---|---|---|
| GLM-5.3-Flash | 0.15 | 0.50 | 0.03 | $60 |
| GLM-5.3 | 1.40 | 4.40 | 0.26 | $15 |
| GLM-5.2 | 1.40 | 4.40 | 0.26 | $60 |
| Kimi K3 | 3.00 | 15.00 | 0.30 | $15 |
| Kimi K2.7 Code | 0.95 | 4.00 | 0.19 | $60 |
| Kimi K2.6 | 0.95 | 4.00 | 0.16 | $60 |
| LongCat-2.0 | 0.30 | 1.20 | 0.006 | $60 |
| LongCat 2.5 Preview Free | Free | Free | Free | 不限量（限时） |
| MiMo-V2.6-Flash | 0.14 | 0.28 | 0.0028 | $60 |
| MiMo-V2.6-Pro | 0.435 | 0.87 | 0.003625 | $15 |
| MiMo-V2.5 | 0.14 | 0.28 | 0.0028 | $60 |
| MiMo-V2.5-Pro | 0.435 | 0.87 | 0.003625 | $15 |
| MiniMax M3 | 0.30 | 1.20 | 0.06 | $60 |
| MiniMax M2.7 | 0.30 | 1.20 | 0.06 | $60 |
| Muse Spark 1.3 Contributor | 0.10 | 0.20 | 0.002 | $60 |
| Muse Spark 1.2 Contributor | 0.10 | 0.20 | 0.002 | $60 |
| Qwen3.8 Max | 2.00 | 6.00 | 0.25 | $15 |
| Qwen3.8 Flash | 0.15 | 0.47 | 0.016 | $30 |
| Qwen3.7 Plus (≤256K) | 0.40 | 1.60 | 0.04 | $60 |
| **DeepSeek V4.1 Flash (Off-Peak)** | **0.15** | **0.60** | **0.003** | **$60** |
| DeepSeek V4.1 Flash (Peak) | 0.30 | 1.20 | 0.006 | $60 |
| DeepSeek V4 Pro (Off-Peak) | 0.66 | 1.98 | 0.022 | $15 |
| DeepSeek V4 Pro (Peak) | 1.32 | 3.96 | 0.044 | $15 |
| DeepSeek V4 Flash (Off-Peak) | 0.15 | 0.60 | 0.003 | $30 |
| DeepSeek V4 Flash (Peak) | 0.30 | 1.20 | 0.006 | $30 |
| DeepSeek V4 Flash Vision Exp | 0.15 | 0.60 | 0.003 | $15 |
| Hy4 preview | 0.834 | 2.501 | 0.042 | $30 |
| Hy3 | 0.14 | 0.58 | 0.035 | $60 |
| Space Bunny | 0.15 | 0.60 | 0.03 | $30 |
| Grok 4.7 / 4.6 (≤200K) | 2.00 | 6.00 | 0.50 | $15 |
| GPT 6 Luna (≤272K) | 0.10 | 0.50 | 0.01 | $15 |
| GPT 5.6 Luna (≤272K) | 0.20 | 1.20 | 0.02 | $15 |
| Claude Haiku 5.5 (≤100K) | 0.10 | 0.50 | 0.01 | $15 |

**Go Plus（$40/月）**：单价同上，月额度 ×2 — 便宜模型 $60→$120、旗舰 $15→$60、Kimi K3 $15→$60。我们用量下**完全不需要**。

> 模型 ID 与控制节点：Qwen / MiniMax 走 `https://opencode.ai/zen/go/v1/messages`（Anthropic 协议），Grok / GPT Luna / Muse Spark 走 `/v1/responses`，其余（DeepSeek / GLM / Kimi / MiMo / LongCat / Hy3 / Space Bunny）走 `/v1/chat/completions`。**跨协议切换要换 provider（opencode-go vs opencode-go-anthropic）**，见 skill hermes-china-providers。

## 3. 本机用量画像（state.db，近 30 天，billing_provider='opencode-go'）

```sql
SELECT SUM(api_call_count), SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens)
FROM session_model_usage
WHERE first_seen > <now-30d> AND billing_provider='opencode-go';
```

- 2,602 次调用 / 非缓存输入 12.80M / 输出 2.60M / **缓存读 109.65M**
- 单次均值：**非缓存 4,921 · 缓存 42,157 · 输出 998** → 缓存占输入 **89.5%**
- 活跃日 ~123 次/天（30 天窗口里 20 个活跃日；9/26–10/6 停摆）
- 历史最重的一天：9/1，222 次调用，按 V4.1 Flash Off-Peak 价 = **$0.79**
- ⚠️ 30 天口径 vs 活跃日口径差别大：30 天实付 $3.81，**活跃日外推 30 天 = $6.73（Off-Peak）/ $13.45（全 Peak）**。给用户结论时说清用的是哪个口径

## 4. 逐模型性价比排名（按上面用量折算）

`月成本 = (12.80M×In + 2.60M×Out + 109.65M×Cache) / 1e6`，占用% = 月成本 / 该模型月额度。

| 模型 | 月成本 | 月额度 | 占用% | 月可支撑调用数 |
|---|---|---|---|---|
| Muse Spark 1.3 Contributor | $2.02 | $60 | 3.4% | 77,308 |
| MiMo-V2.5 / V2.6-Flash | $2.83 | $60 | 4.7% | 55,220 |
| **DeepSeek V4.1 Flash (Off-Peak)** | **$3.81** | **$60** | **6.3%** | **40,989** |
| GLM-5.3-Flash | $6.51 | $60 | 10.9% | 23,976 |
| Hy3 | $7.14 | $60 | 11.9% | 21,865 |
| DeepSeek V4 Flash (Off-Peak) | $3.81 | $30 | 12.7% | 20,494 |
| DeepSeek V4.1 Flash (Peak) | $7.62 | $60 | 12.7% | 20,494 |
| LongCat-2.0 | $7.62 | $60 | 12.7% | 20,494 |
| Qwen3.8 Flash | $4.90 | $30 | 16.3% | 15,939 |
| Space Bunny | $6.77 | $30 | 22.6% | 11,528 |
| MiniMax M2.7 / M3 | $13.54 | $60 | 22.6% | 11,528 |
| Qwen3.7 Plus | $13.67 | $60 | 22.8% | 11,422 |
| Claude Haiku 5.5 / GPT 6 Luna | $3.68 | $15 | 24.5% | 10,615 |
| GPT 5.6 Luna | $7.87 | $15 | 52.5% | 4,957 |
| MiMo-V2.6-Pro | $8.23 | $15 | 54.9% | 4,744 |
| Kimi K2.6 | $40.11 | $60 | 66.9% | 3,892 |
| Kimi K2.7 Code | $43.41 | $60 | 72.3% | 3,597 |
| GLM-5.2 | $57.89 | $60 | 96.5% | 2,697 |
| DeepSeek V4 Pro (Off-Peak) | $16.01 | $15 | **106.7%** ⛔ | 2,438 |
| GLM-5.3 | $57.89 | $15 | 386% ⛔ | 674 |
| Qwen3.8 Max | $68.63 | $15 | 458% ⛔ | 569 |
| Grok 4.6/4.7 | $96.06 | $15 | 640% ⛔ | 406 |
| Kimi K3 | $110.31 | $15 | 735% ⛔ | 354 |
| LongCat 2.5 Preview Free | $0 | 不限量 | 0% | — |

**结论**：主力 = `deepseek-v4.1-flash`（同价双倍额度、缓存读 $0.003/M 除 MiMo 外最便宜、带推理、已磨合）。唯一值得试的更便宜项 = `mimo-v2.6-flash`（4.7%，工具调用已实测通过，中文质量/长链路稳定性未验）。免费档 LongCat 2.5 Preview Free 适合看门狗类零风险任务。**Muse Spark 虽然最便宜但训练用数据，已排除。**

## 5. 工具调用探针（换主力前必做）

实测 6 个候选**全部正确触发 tool_call**（含免费档），没有"只会聊天"的：

| 模型 | 延迟 | 结果 |
|---|---|---|
| glm-5.3-flash | 1.7s | ✅ `get_weather({"city": "苏州"})` |
| deepseek-v4.1-flash | 2.4s | ✅ 同上（带 reasoning_content） |
| mimo-v2.5 | 2.8s | ✅ 同上 |
| longcat-2.0 | 3.2s | ✅ 同上 |
| longcat-2.5-preview-free | 5.0s | ✅ 同上 |
| mimo-v2.6-flash | 9.1s | ✅ 同上 |

探针写法（**踩过两次坑**，照抄）：

```bash
cd ~/AppData/Local/hermes            # ① 必须 cd 到目录用相对路径
KEY=$(grep -m1 '^OPENCODE_GO_API_KEY=' .env | cut -d= -f2-)
for M in deepseek-v4.1-flash mimo-v2.5; do
  printf '{"model":"%s","messages":[{"role":"user","content":"帮我查一下苏州今天天气"}],"tools":[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],"tool_choice":"auto","max_tokens":300}' "$M" > probe.json
  curl -s -o "probeout/$M.json" -w "%{time_total} %{http_code} $M\n" --max-time 90 \
    -x http://127.0.0.1:10808 \
    -H "Authorization: Bearer $KEY" -H "User-Agent: curl/8.0.0" \
    -H "x-opencode-session: hermes-script-model-probe" -H "Content-Type: application/json" \
    -X POST https://opencode.ai/zen/go/v1/chat/completions -d @probe.json
done
# ② 把响应落到文件再用 Python 解析
python -c "import json,glob,os;[print(os.path.basename(f), json.load(open(f,encoding='utf-8'))['choices'][0]['message'].get('tool_calls')) for f in glob.glob('probeout/*.json')]"
```

三个必踩的坑：

1. 🔴 **`-d @/tmp/x.json` 在 MSYS bash 下必失败**（`curl: option -d: error encountered when reading a file`）——原生 curl 不认 MSYS 虚拟路径。**`cd` 到目录用相对路径 `-d @probe.json`**，或传 `C:/...` 正斜杠 Windows 绝对路径
2. 🔴 **别把 JSON 响应拼进 `python -c` 字符串再 json.loads**——响应里的引号会把 shell 引号规则炸掉，得到 `Expecting ',' delimiter` 之类的假解析错误（本次 6 个模型全"解析失败"，其实 6 个返回值都正常）。**`curl -o 文件` → Python 读文件**
3. 🔴 **请求必须带 `x-opencode-session`**，否则返回 `{"type":"error","error":{"type":"MissingSessionID"}}`（2026-09-06 起 opencode 强制；Hermes 主链路已自动带，**独立脚本必须自己加**）

## 6. 顺手发现（未处理，留给用户决策）

- **DeepSeek 官方 API 现在只提供 `deepseek-flash` 和 `deepseek-v4-pro`**（`GET https://api.deepseek.com/v1/models`）——`deepseek-v4-flash` 这个模型名已不在官方列表里；而 `fallback_providers[0]` 正是 `provider: deepseek / model: deepseek-v4-flash`
- 实测该账号返回 `{"error":{"message":"Insufficient Balance"}}` → **第一层 fallback 真触发时会直接失败**（余额是状态不是配置，别写进 skill 当规则，报给用户即可；本次用户选择"暂时不用管"）
- 排查姿势：`hermes config get model`、`grep -n 'v4-flash\|v4\.1-flash' config.yaml`、`python -c "json.load(open('cron/jobs.json'))"` 看每个 job 的 `model` 字段（本次全部为 None → 都吃 `cron.model` 这一处配置）
