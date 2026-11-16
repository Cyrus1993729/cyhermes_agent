# `runtime/scripts/hermes-local.mjs` 包装器实测（2026-11-04）

场景：另一个 agent 通过 A2A 派活，要求在「不改任何有效配置」的前提下验证
Dayflow 云端 `ai/models` 的写读链路（把 mail 从跟随默认 pin 成独立但同型号）。
只做配置读/写，不发模型调用、不改日程、不重启、不发消息。

## 1. 入口与档案

```bash
NODE="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
SCRIPT="C:/Users/Administrator/AppData/Local/DayflowHome/releases/<active>/runtime/scripts/hermes-local.mjs"
CONN=".../releases/<active>/runtime/.local/hermes-cloud-connection.json"   # 私有连接文件，内容不可外泄
"$NODE" "$SCRIPT" --connection "$CONN" models
```

`--connection` 会被包装器从 argv 里摘掉，转成子进程的
`DAYFLOW_URL / DAYFLOW_API_KEY / DAYFLOW_SITE_TOKEN`，然后 `spawnSync` 调同目录
`hermes-client.mjs`。不传 `--connection` 时默认用 `../.local/hermes-connection.json`。

- `models`、`models-catalog`、`models-test-status`、`state/items/due/categories/*-delete`
  **免 stdin**；其余子命令（`models-set` 等）会 `fs.readFileSync(0)` 读 JSON。
  用 `cat payload.json | node ... models-set --request-id <uuid>` 最稳。
- 请求 ID 走 `--request-id`（包装器再塞进 `DAYFLOW_REQUEST_ID`）。env 直传不生效，见主 SKILL.md。
- 输出仍是**两行**：业务 JSON + `{"requestId":...,"operation":...,"durationMs":...}` 诊断行。

## 2. 🔴 首次调用必撞的 pwsh 坑（19ms 秒挂）

```
{"requestId":"","operation":"models","attempt":1,"durationMs":19,"totalMs":19,
 "errorType":"runtime_missing","phase":"startup","recoverable":false}
{"error":"读取未完成，请稍后重试","code":"result_unconfirmed","requestId":""}
```

原因：`http-request.mjs` 在 win32 上 `spawn('pwsh', …)` 跑 `http-request.ps1`，
**裸 `pwsh` 取 PATH**；本机 PowerShell 7 只装在 `DayflowHome/tools/pwsh7/pwsh.exe`，
不在系统 PATH。`child.on('error')` 直接把 spawn 失败包装成 `runtime_missing`。

修法（每次调用前前置目录即可，不改系统环境、不改任何配置）：

```bash
export PATH="/c/Users/Administrator/AppData/Local/DayflowHome/tools/pwsh7:$PATH"
```

判别口诀：**durationMs < 100 + `phase:startup` + `runtime_missing` = 环境缺 pwsh，不是接口/凭证问题**，
别去怀疑 key、网络或 release 版本。

## 3. 「同型号 pin」写读验证法（不动有效行为的写操作怎么证）

要求：证明写链路通，同时保证四个用途的 effectiveModel 与 default 一个都不变。

```bash
# ① 只读基线
node ... models                      # 记 version / epochDigest / 四用途 selection+effective
# ② 写入：把某用途 pin 成它当前的 effectiveModel
cat payload.json | node ... models-set --request-id <新UUID>
# ③ 立刻回读
node ... models
```

payload：
```json
{"version":0,"epochDigest":"e3b0c442…b855","overrides":{"mail":"deepseek-v4-flash"}}
```

成败判据（三条同时满足才算通过）：

| 观察点 | 期望 |
|:--|:--|
| 该用途 `source` | `default` → `independent` |
| 该用途 `effectiveModel` | 与 before **完全一致** |
| 其余三用途 + `defaultModel` | 全部一字不变 |
| 全局 `version` | +1（0 → 1） |
| `epochDigest` | 不变 |

`version` 从 0 起，写完变 1；`epochDigest` 在没有任何 override 时等于
`sha256("")` = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`，
pin 之后仍返回同一值 —— 它不是 override 的摘要，别拿它当变更信号。

回滚方式：同一份 payload 把该用途写回 `null` + 届时最新 `version`。

## 4. 汇报口径（A2A / 跨机协作时）

只回脱敏 DTO + 事实：before/after 的 version、epochDigest、defaultModel、四用途
selection/source/effectiveModel；写入的 requestId、起止时间戳、退出码、HTTP 状态、attempt 数。
**不输出**连接文件内容、key、Authorization 头、邮件正文。
发现「当前 effective 恰好是已知失效型号」时照实说一句、不动手 —— 派活方要求的是链路验证，不是修型号。

## 5. 本次实例数字（可作对照基线）

- before：`version=0`, default `deepseek-v4-flash`, mail/review/capture 跟随默认，coach 独立 `deepseek-v4.1-flash`
- write：requestId `1e35d588-fed5-4fee-a224-d6b1d4e2dd95`，20:47:06→20:47:10，exit 0，HTTP 200，attempt 1，3268ms
- after：`version=1`, mail `source=independent`，四用途 effective 与 default 全不变
