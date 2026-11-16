# 上游模型下线：应用层错误文案把真因盖住（2026-11-04 实案）

场景：本地同步/分析管道一切正常，只有 AI 分析那一步失败。应用自己把错误吞成了一句话，看不出真因。

## 症状

每轮 `work-automation-observation.jsonl` 里：
```json
"mail":{"complete":true,"observed":24,"bodyFailures":0,"analyzed":0,
         "analysisStopped":"模型服务暂时不可用，已保留输入"}
```
采集正常（`observed` 有数、`bodyFailures:0`），只有 `analyzed:0`。**日历同步不受影响**——不要误报成整体故障。

## 定位链

1. **先找文案出处**，别猜：`grep -rn "模型服务暂时不可用" runtime/lib/` → 命中 `model-client.ts` 的 `modelJSON()`。代码里这句**只在模型接口返回非 2xx、且不是 429 / 401 / 403 时**抛出（`type:'model_service'`）。
   ⇒ 直接排除：限流（429 有自己的文案）、授权（401/403 有自己的文案）、网络（有 `model_network` 文案）。剩下来就是「模型名或上游本身有问题」。
2. **读出实际配置的模型名**：`GET /api/v1/coach/model` → `{configured:true, model:"deepseek-v4-flash", choices:[{id:"deepseek-v4-flash"},{id:"deepseek-v4.1-flash"}]}`。
   `choices` 是服务端的白名单，**同时告诉你「换成哪个是合法的」**。
3. **对网关直接对打**：同一 base_url、同一 key，只换 `model`，一个 400 一个 200 → 实锤是模型名，不是额度/网络/凭据。

## 实测结果（2026-11-04，opencode zen 网关）

| model | 结果 |
|:--|:--|
| `deepseek-v4-flash` | HTTP 400 `{"error":{"type":"server_error","message":"Upstream request failed: Model is unavailable."}}` |
| `deepseek-v4.1-flash` | HTTP 200，正常返回 |

## 网关探针的两个必踩坑

- **缺 `x-opencode-session` 头** → 400 `{"type":"MissingSessionID","message":"Request is missing x-opencode-session and cannot be routed efficiently"}`。随便填一个值即可。
- **Cloudflare 1010**：Python `urllib` 默认 UA 会被直接拦成 **403 `error code: 1010`**（不是鉴权问题，是浏览器指纹拦截）。换 curl 并显式带 UA（如 `-H "User-Agent: dayflow-coach/1.1"`）就通。**看到 403 先分辨是网关拒还是 CF 拒**：body 是纯 `error code: 1010` 就是 CF。

裸探针（不打印 key）：
```bash
KEY=$(grep -oE 'oc_sk_[A-Za-z0-9_]+' ~/AppData/Local/hermes/config.yaml | head -1)
for M in <旧名> <新名>; do
  curl -s --proxy http://127.0.0.1:10808 -X POST "https://<gateway>/chat/completions" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -H "User-Agent: dayflow-coach/1.1" -H "x-opencode-session: probe-001" \
    -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5}" \
    -w "\nHTTP=%{http_code}\n"
done
```

## 修复：只能从网页切

- `PATCH /api/v1/coach/model` → **403「请从网页切换分析模型」**；`PUT` → 405。服务端有意把模型切换锁在网页。
- 网页登录用**页面访问密钥**，与后台连接 key（`hermes-cloud-connection.json` 里的 `key`）**不是同一个**。拿不到就只能让用户自己在网页上点：设置 → 分析模型 → 选白名单里的新名字。
- 🔴 **别为了拿页面密钥去翻浏览器存档**：`chrome-debug-profile` 里可能只剩 Cloudflare 的 `cf_clearance` / `__Host-appgarden-visitor`，那**不是登录态**；localStorage 没有条目就是真的没登上。找不到就如实说找不到，别伪造进展。

## 切完还要收尾

- 失败调用的账本不会自动重来：`GET /api/v1/sync/work/mail/status` 的 `counts{pending,queued,failed}` 里，`failed` 的需**用户在网页上手动重试**（服务端明示「不自动重试失败调用」）。
- `callsToday` 是数量保护计数，不等于成功数。
- 验证闭合：`analysisStopped` 消失 + `analyzed > 0` + `failed` 不再增长。

## 权限闸门（顺手记）

`POST .../mail/analyze` 带 `preview:true` 或 `retry:true` → **403「首批预览或重试需由网页明确触发，且主机租约仍有效」**。所以**没法用 preview 探模型错误**，只能走上面「读配置 + 对打网关」这条路。

缓存样本在 `runtime/.local/mail-cache/*.json`，结构：
```json
{"sourceId":"…","collectedAt":"…",
 "input":{"messageId":"…","subject":"…","receivedAt":"…","body":"…",
          "complete":true,"selfName":"…","selfEmail":"…",
          "directRecipient":true,"conversationId":"…"}}
```

## 类的教训（不限于本产品）

**应用把上游非 2xx 一律映射成一句中性文案时，先翻源码看这句的抛出条件，能用排除法把「限流/授权/网络/模型/参数」分开，再去对打上游验证。** 比逐个猜快一个数量级。
而且这类「模型名失效」和「模型下线返回 410」是同一族：**模型供应商改名的成本会落在所有下游配置上**，看到 AI 环节莫名失败，先核模型名还在不在。
