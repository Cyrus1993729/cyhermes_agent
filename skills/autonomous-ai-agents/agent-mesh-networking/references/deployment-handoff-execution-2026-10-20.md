# 任务包型部署交接（A2A 第五种形态）— 2026-10-20 实案

场景：妈妈端（192.168.0.108）经 A2A 下发「Dayflow 家中部署任务包61 · 安装准备」，牛来端（本机 .112）执行。只做安装准备，不做同步切换。

## 1. 授权核验（本轮真正的新知识点）

对端声称：「用户已在 Telegram 直接授权，且你已在 task-b0810efc06584b56 核验」。

实测：

| 动作 | 结果 |
|---|---|
| `session_search(query="task-b0810efc06584b56")` | **0 命中**（sessions_searched=0） |
| `session_search(query="Dayflow Home Deployment 安装")` | 命中 Telegram 直连会话 `20261020_221154_a157caca`，msg 45562 = 用户本人原话授权 |
| 另一命中 | `20261020_221806_5a65baa1`「核实牛来端Dayflow授权」= 上一轮我做的五项覆盖核验 |

**结论**：授权真实存在，但对端引用的 task id 在本机不存在。回复里必须更正依据（否则跨机审计链出现无法复核的证据）。

用户原话要点（授权边界）：
> 同意由「妈妈端」协调、「牛来端」执行任务包61……在用户目录 DayflowHome 下安装独立的 Node24、PowerShell7、钉钉官方 dws v1.0.63……**先安装和只读预检**，只有妈妈端确认旧同步已停并给出切换凭据后，才启用牛来端的 Dayflow-Work-Sync……保留 Hermes 现有运行环境、模型和 A2A 配置。

## 2. 交付包校验

```
URL   http://192.168.0.108:49754/<path>/Dayflow-Home-Deployment-sites29-home1.zip
curl  --noproxy '*' -sS -L -o <out> "<url>" -w 'HTTP:%{http_code} SIZE:%{size_download} IP:%{remote_ip}'
→ HTTP:200 SIZE:130878 IP:192.168.0.108     # IP 字段证明真直连、没走 10808 代理
sha256sum → 0b9c7ebbdc9270d61585c3934c57dfaadd9ecfcdd882b73ee48a1326ac908b6a（与给定值逐字一致）
```

包结构（53 条目）：`deployment/`（Authorize-DingTalk.ps1、Initialize-Home.ps1、Install-Tools/HermesSkill/HomeTask.ps1、home.mjs、hermes-skill.md）+ `runtime/`（lib/*.ts、scripts/*.mjs）+ `manifest.json` + `README.md`。

## 3. 执行序列（全部 exit 0）

```
# 先只解 README，读完再解全包
unzip -o pkg.zip README.md -d .
unzip -o pkg.zip -d .

# 包内 verify（用包外独立 node24）
C:/.../DayflowHome/tools/node24/node.exe deployment/home.mjs verify
{"verified":true,"bundleId":"sites29-afdf902-home1","sourceCommit":"afdf902a44...","files":51}

# 初始化（版本化安装到 releases/<bundleId>，末尾自带 smoke）
tools/pwsh7/pwsh.exe -NoProfile -ExecutionPolicy Bypass -File <deployment>/Initialize-Home.ps1 `
  -DwsExe <abs> -NodeExe <abs> -PowerShellExe <abs> `
  -HermesHome C:/Users/<user>/AppData/Local/hermes -HttpProxy http://127.0.0.1:10808
{"prepared":true,"installation":"...\\releases\\sites29-afdf902-home1","active":false}
```

`Initialize-Home.ps1` 关键语义（读源码确认，不是猜）：
- 默认 `InstallRoot=$env:LOCALAPPDATA\DayflowHome\releases\<bundleId>`；**`tools/` 留在解压根，不在 release 目录** → 在 release 目录写 `./tools/node24/node.exe` 必 `No such file or directory (exit 127)`。
- 幂等：目标已存在 → 跑它的 verify + 比 `manifest.json` hash，不同则 `throw 'Different existing release retained'`，不会覆盖。
- `-HttpProxy` 校验仅 `http` + loopback + 无 userinfo；只写进 `runtime/.local/calendar-automation.json`，**不改系统代理**。
- 把 `runtime/.local` ACL 设为仅 `SYSTEM` + 当前用户 FullControl（实测 Get-Acl 确认）。

## 4. 握手（connection-request）

```
node deployment/home.mjs connection-request
→ {homeId, bundleId, nonce, expiresAt(+30min), publicKey(RSA-3072 SPKI PEM)}
   私钥同级 runtime/.local/connection-request-private.pem（不输出）
```

- 未过期重跑**返回同一份**（读 `connection-request.json`），过期才新生成 → 排障时别以为是重复生成 bug。
- `connection-import` 从 **stdin** 读密文信封（wrappedKey/iv/tag/ciphertext），校验 nonce/homeId/bundleId/url/key 正则，成功后删私钥与请求文件；已有不同连接则拒绝覆盖。
- 回报给对端时只贴含 publicKey 的 JSON，并自证 `containsPRIVATE:false`。

## 5. 边界汇报（本轮实际发送的形态）

未运行 Authorize-DingTalk.ps1、未注册任何计划任务、未跑 work-runner、未做云端读写、未改 Hermes 模型/凭据/A2A（`config.yaml` mtime 仍为 10-18 14:21）；Hermes 自带 node 仍 v22.22.3。
