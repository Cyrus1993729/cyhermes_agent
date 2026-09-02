# qwen-bailian 直连 → OpenCode 网关迁移（2026-09-01 实踩全记录）

## 为什么迁

- 用户报"千问直连 API 一直有费用"：`qwen_review.py`（黄金周报 L1 审查，每周 4-6 次）+ `report_gen_qwen.py`（日报备用引擎）直连阿里云百炼 MaaS 专属端点（`ws-xxx.maas.aliyuncs.com`），按实例/调用计费
- OpenCode Go 订阅里同一模型 `qwen3.7-max` 的 $60/月配额几乎没用（8/31 实测 $0.10 = 0.2%）→ **同模型换网关，质量不变、费用近乎归零**，之后可彻底停阿里云
- 用户决策（方案 A）：先迁移验证、再停阿里云实例，避免下周一黄金周报 L1 审查在故障窗口挂掉

## 改动点（三处，已验证）

### 1. config.yaml `providers.qwen-bailian` 段改指向（脚本零逻辑改动）

保留段名 `qwen-bailian:`（两个脚本用 `txt.split("qwen-bailian:", 1)[1]` 解析它），只改值：

```yaml
providers:
  qwen-bailian:
    api_key: <OPENCODE_GO_API_KEY 的值>      # 从 .env 读，不是旧的 sk-ws-* 百炼 key
    api_mode: chat_completions                 # 不变（openocode 网关 OpenAI 格式端点支持）
    base_url: https://opencode.ai/zen/go/v1    # 原 ws-xxx.maas.aliyuncs.com/compatible-mode/v1
```

- key 来源：`~/.hermes/.env` 的 `OPENCODE_GO_API_KEY`（**不在** config `model.api_key`，也**不在** auth.json credential_pool——后者 opencode-go 是空 dict，实测）
- 改法：execute_code 里读 config/.env → re.sub 替换 → 写回；改前备份 config + 两个脚本（`.bak_<时间戳>`）
- 为什么能共用段名：两个脚本只读该段的 api_key/base_url 两个字段

### 2. 两个脚本的 urllib 请求必须加 UA 头（🔴 关键坑）

opencode.ai 网关的 Cloudflare 会拦 urllib 默认 UA（`HTTP 403 Forbidden, error code: 1010`，连 deepseek-v4-flash 也 403——不是认证问题）。必须：

```python
headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
         'User-Agent': 'curl/8.0.0'}   # qwen_review.py / report_gen_qwen.py 各一处
```

- 阿里云端点不拦默认 UA（所以迁移前没这问题）；`requests` 库不受影响；Hermes 内部走 httpx 也不受影响——**只有这两个手写 urllib 脚本要改**
- 探测 opencode 网关时同样要带 UA：`urllib.request.Request(url, headers={..., "User-Agent": "curl/8.0.0"})`

### 3. 模型可用性已验证

- `GET https://opencode.ai/zen/go/v1/models`（带 key + UA）→ 33 个模型，含 `qwen3.7-max`/`qwen3.8-max`/`qwen3.8-flash` 等
- `POST /chat/completions` `{"model":"qwen3.7-max",...}` → 200，**qwen3.7-max 在 OpenAI 兼容端点直接可用**（不需要走 anthropic_messages 的 opencode-go-anthropic）
- `response_format: {"type":"json_object"}`（qwen_review.py 用了）在网关上也正常（实测出裁决）

## 验证流程（ad-hoc 规范）

1. `python -c "import report_gen_qwen; print(report_gen_qwen.call_qwen('回复OK'))"` → 返回 OK
2. `python qwen_review.py --contract <最小契约> --deliverable <最小交付物> --force` → 输出 `L1 裁决: PASS/CONDITIONAL/FAIL` 且 exit 0（exit 2 = API 错误）
3. 规范验证：写 `Temp/hermes-verify-*.py` 临时脚本（tempfile + 两断言 + review_log 行数回滚）→ 运行 → 删除
4. 清理：qwen_review 测试会往 `reviews/review_log.jsonl` append 一条（task 名 = contract 文件名 stem），要删掉保持审计日志干净

## 事后收尾

- 更新引用"qwen-bailian 直连"的 skill 描述：l1-review（description + 超时段）、trendradar-operations（report_gen_qwen 行）——已改，指出走 OpenCode 网关 + UA 坑
- **用户侧操作（agent 够不到）**：去阿里云百炼控制台释放/停用专属服务实例——脚本停调用没用，如果实例按小时计费，实例在线就持续扣费
- 回滚：config + 脚本有 `.bak_<时间戳>` 备份；恢复 = 还原 config 段 + 去掉 UA 头（或还原整个脚本）

## 可复用结论

- 判断"某模型是否在某网关 OpenAI 端点可用"：`/models` 列表 + 一次真实 `chat/completions`，**必须带 UA**（否则 1010 误判成认证失败）
- 迁移"贵的直连 API → 已有订阅网关"的通用姿势：保持配置段名/脚本解析逻辑不变，只换 base_url + api_key + 补 UA——改动面最小、验证点最少