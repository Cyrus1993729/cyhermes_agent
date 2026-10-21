# Claude Code Access Diagnosis — 2026-06-29

## 事件

6/29 早上，所有 `claude` 命令返回 403：
```
Failed to authenticate. API Error: 403 Request not allowed
```

同一账户 6/16→6/27 连续 11 天正常使用。

## 排查过程

### 第一轮（误判）

1. `claude -p "hello" --model opus` → 403
2. 直接调 Anthropic API（裸连）→ 403
3. `claude login` → 403
4. 查 `~/.claude.json` → `passesEligibilityCache: forbidden`
5. 删 `.claude.json` 重来 → 403

**错误结论**：Google Play 订阅不含 API 权限，Anthropic 后端封了。

### 第二轮（根因）

发现 6/16→6/27 所有成功调用都有 `export HTTP_PROXY=...` 前缀，6/29 漏了。

```bash
# 失败（漏代理）
claude -p "hello" --model opus → 403

# 成功（带代理）
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" && claude -p "OK" --model opus --max-turns 1 → OK
```

## 根因

**Claude Code CLI 没有继承系统代理**（Node.js 的 `https` 模块不自动走系统代理设置）。Clash Verge 的"系统代理"只写入了当前终端的环境变量，未写入 Windows 用户级注册表。

- 已有代理的终端 → claude 走代理 → 正常
- 新终端/未 export → claude 直连 → 被区域封锁 → 403

## 修复

1. 每次调 claude 前 export 代理变量（内存已写入 🔴 红线）
2. `setx HTTPS_PROXY "http://127.0.0.1:7897"` 写入注册表，新终端自动生效

## 实际可用路径

| 路径 | 状态 | 条件 |
|------|------|------|
| Claude Code CLI | ✅ | 必须带代理 |
| Anthropic 直接 API | ❌ | Google Play 订阅不含 API key 权限 |
| Hermes Nous Provider | ❌ | OAuth 已配，余额不足 |

## 教训

1. 排查故障时先对比"成功调用 vs 失败调用"的命令差异，而非直接下结论
2. `passesEligibilityCache: forbidden` 可能是区域封锁伪装成权限错误
3. Google Play Claude Pro 订阅**确实包含 Claude Code CLI 权限**——之前的"不含 API"是误判
