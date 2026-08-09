# Hermes v0.20 / A2A 平台笔记 (2026-08)

## 拉取 Hermes 版本 release notes（GitHub 网页 404 时的正确姿势）

- Hermes 的 GitHub tag 是 **`v2026.8.3`** 这类日期格式，不是 `v0.20.0`。
  release 页面直接 web_extract 会拿到登录墙/404，**用 GitHub API + 代理**：
  ```bash
  export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897
  curl -s --max-time 30 "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=3" \
    | python -c "import json,sys; [print(r['tag_name'],'|',r['name'],'|',len(r['body'] or '')) for r in json.load(sys.stdin)]"
  # 取正文保存本地精读：
  curl -s "https://api.github.com/repos/NousResearch/hermes-agent/releases/tags/v2026.8.3" \
    | python -c "import json,sys; open('release.md','w').write(json.load(sys.stdin)['body'])"
  ```
- 本地代码是否已含新版本：`cd $HERMES_HOME/hermes-agent && git log -1 --format=%ci`（8/3 之后 = 已含）。
  pyproject.toml 版本号可能滞后于代码。

## A2A v1.0 — Agent 间通信（v0.20 主打，关闭 issue #514）

- 实现：**内置插件** `plugins/platforms/a2a/`（stdlib only，无 a2a-sdk），实现 Google
  主导的开放 A2A 协议（a2a-protocol.org）。可与其他 Hermes / LangChain / CrewAI /
  Google ADK / OpenClaw 等互通。完整说明在插件内 `README.md` / `DESIGN.md`。
- **入站（被调用）**：启用后服务 Agent Card 于 `/.well-known/agent-card.json`，
  JSON-RPC `message/send`、`message/stream`(SSE)、`tasks/*`、推送通知配置。
  入站任务注入**当前实时会话**（带完整记忆上下文，非克隆体）。
- **出站（调用别人）**：5 个工具 `a2a_discover` / `a2a_call` / `a2a_list` /
  `a2a_history` / `a2a_orchestrate`（按 capability 扇出 all/first/best）。
- **启用**（config.yaml；`hermes gateway setup` 也可选 A2A）：
  ```yaml
  gateway:
    platforms:
      a2a:
        enabled: true
        extra:
          port: 9900
  # 出站对端（可选）
  a2a_agents:
    researcher: { url: "http://localhost:9999", auth: {type: bearer, token: "sk-..."}, timeout: 120 }
  ```
- **安全默认**：无 token 只绑 `127.0.0.1`（配 token 后才可设 `A2A_HOST` 放开）；
  per-peer token `A2A_PEER_TOKENS="name:tok,…"`；入站跑防注入过滤（/ 前缀命令被拒）；
  推送 HMAC-SHA256 签名（`X-A2A-Signature`）；审计 `~/.hermes/a2a_audit.jsonl`；
  对话持久化 `~/.hermes/a2a_conversations/`（压缩/重启后仍可 `a2a_history` 调回）。
- 关键 env：`A2A_PORT` 9900、`A2A_REPLY_TIMEOUT` 300s、`A2A_MAX_PINGPONG_TURNS` 5、
  `A2A_ALLOW_ALL_USERS` false、`A2A_RATE_LIMIT` 60/min。
- 单机单用户自用场景（Telegram+微信）暂无必要启用；多 Hermes 实例互通或接外部
  agent（Claude Code/OpenClaw）时启用，先只绑 127.0.0.1 最安全。

## v0.20 其他亮点（一句话版）
实时语音（流式 TTS+打断+唤醒词）、grounded-citations 可验证引用、出站 HMAC webhook、
桌面 artifacts/插件 SDK、CLI `!` shell 模式与 /init /diff /context /focus、中途纠偏
redirects、工具自恢复（截断落盘、patch 自诊断）、迭代上限 90→500、冷启动 14s→1.8s。
