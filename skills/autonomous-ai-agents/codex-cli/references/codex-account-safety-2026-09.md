# Codex 账号安全审计（2026-09-09 实测）

评估"Codex 封号风险 / 该不该装某工具"时，先审计本机真实使用面，别凭印象。

## 如何确认 OpenAI 账号的"唯一使用面 = 官方 Codex CLI"
```bash
# 1) config.toml 有无 base_url/provider 覆盖？无=直连 OpenAI 官方端点
grep -in "base_url\|provider\|wire_api" ~/.codex/config.toml   # 期望无输出(model 项除外)

# 2) auth.json 是否为真实官方 OAuth？
python -c "import json,os;p=os.path.expanduser('~/.codex/auth.json');d=json.load(open(p));print(list(d.keys()))"
# 期望含 tokens/id_token/access_token/refresh_token/account_id = 官方登录态，非中转 key

# 3) hermes config.yaml 里 gpt-*/openai 只出现在 tts/stt 备用段(api_key 空)，别误读为主模型走 OpenAI
```

## 封号风险判断要点（结论来自 2026-09 社区对大量封号案例归纳）
- 头号触发：**网络/支付**（共用机房 IP、地域跳变、支付失败）+ **脚本自动化 / key 分发**（把订阅额度当中转 API 用）。
- 本机 OpenAI 账号既无中转 key 分发（opencode 链路全走国内模型 deepseek/qwen/minimax 经 opencode 网关），出口又固定自建 VPS 独享 IP → 不在高危面上。
- 红线（跨机/多用）：① 不把 auth.json 复制到另一台机（同账号多地活跃=滥用特征）；正确=codepx login 扫码重新登录。② 不在地域不一致的 IP 间跳（同一账号美国 IP ↔ 中国 IP 直连）。两机都用同一 VPS 节点即无此问题。

## 工具评估：碰凭证的 Codex 辅助工具（如 CodexFF）
- 检查它会不会改 ~/.codex/config.toml 的 base_url 指向第三方中转——改了就违反上述红线（把官方订阅当中转用）。
- 信任机制看源码实现：凭证如何存（明文/Keychain/加密 vault）、默认监听 127.0.0.1 还是 0.0.0.0、有无遥测外发、自动审批是否代答。
- 结论基准："防封号"类卖点不成立——本地工具影响不了 OpenAI 服务端风控；唯一沾边是防凭证被盗后异地盗用（防偷≠防封）。
```
