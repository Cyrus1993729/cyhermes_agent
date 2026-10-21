# 加密回填 + 设备码授权 实操（Dayflow Home 交接，牛来端 2026-10-21）

## 0. 现场事实（判断用，别再用全盘 find 重查）

- 解压根：`%LOCALAPPDATA%\DayflowHome\`（= `C:\Users\<u>\Local Settings\DayflowHome`，`Local Settings` 是 `AppData\Local` 的兼容 junction，**同一个目录**）
- **版本化安装的真正工作目录**：`releases\<bundleId>\`（本次 `sites29-afdf902-home1`）；顶层 `runtime\.local` 是模板，可能**根本不存在** —— 只查顶层会误判成"状态丢失"
- 状态/凭据/授权日志全在 `releases\<bundleId>\runtime\.local\`
- 工具在解压根的 `tools\{node24,pwsh7,dws}`（**不在** release 目录），native 程序一律传 `C:/...` 绝对路径
- 实测版本：node v24.22.0 / pwsh 7.6.7 / dws v1.0.63

## 1. 回填前核对（必做）

```python
req = json.load(open(rf"{local}\connection-request.json", encoding="utf-8-sig"))
req["homeId"], req["nonce"], req["expiresAt"]   # 与来件逐字比对
```

`expiresAt` 是 UTC（`Z`），本机 `date` 是 `+0800`，比较走 epoch，汇报两种写法。本次 request 于 07:15 生成、`2026-10-20T23:45:37Z` 过期（= 次日 07:45:37 +08:00）。

## 2. 加密信封回填（stdin，不落参数/不回显）

```python
import json, os, subprocess
local = rf"{release}\runtime\.local"
tmp   = os.path.join(local, "connection-envelope-tmp.json")
json.dump(envelope, open(tmp, "w", encoding="utf-8")); os.chmod(tmp, 0o600)
with open(tmp, "rb") as fh:
    r = subprocess.run([NODE, "deployment/home.mjs", "connection-import"],
                       cwd=release, stdin=fh, capture_output=True, text=True, encoding="utf-8")
print(r.returncode, r.stdout.strip())      # → 0 {"configured":true,"credentialsPrinted":false}
if r.returncode == 0: os.remove(tmp)
```

- 先跑 `node deployment/home.mjs verify`（纯本地，51 文件 manifest 校验）再回填。
- 成功后台会删 `connection-request.json` + `connection-request-private.pem`；`hermes-cloud-connection.json` 生成。
- 已有**不同**连接时程序自己拒绝（`A different connection already exists`）—— 遇到就停，别手工覆盖。

## 3. 隐藏启动设备授权（关键：别让父进程捕获管道）

`<local>\launch-authorize.ps1`：

```powershell
$ErrorActionPreference='Stop'
$p = Start-Process -FilePath '{pwsh}' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','{release}\deployment\Authorize-DingTalk.ps1') `
  -WindowStyle Hidden -RedirectStandardOutput '{local}\dingtalk-authorize-{ts}.stdout.log' `
  -RedirectStandardError  '{local}\dingtalk-authorize-{ts}.stderr.log' -PassThru
@{ pid=$p.Id; startTime=$p.StartTime.ToString('o') } | ConvertTo-Json -Compress
```

启动这一步**必须不捕获输出**，否则孙子进程占住管道，`communicate()` 永远等不到 EOF：

```python
subprocess.run([pwsh,"-NoProfile","-ExecutionPolicy","Bypass","-File",launcher],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
```

本次踩坑：用了 `capture_output=True` → 隐藏进程已起来、调用方却卡满 300 s 被内核杀掉，状态全丢。**超时后第一动作是查进程+查日志，不是重跑**（重跑会起第二个 dws 轮询、第二套设备码）。

## 4. 解析官方链接与设备码

输出在 **stderr**（`stdout.log` 0 B 是正常现象）：

```
● Step 1: 请求设备授权码...
  授权码: NSXG-WHXK
  授权码将在 900 秒后过期。
  授权链接（已填入授权码）：
https://login.dingtalk.com/oauth2/device/verify.htm?caller=dws&callerUmt=<...>&user_code=NSXG-WHXK
● Step 2: 等待用户授权...  ● [n] 轮询中... (Ns)
```

注意实际页是 `device/**verify**.htm`（不是 `authorize.htm`），同页附"手动输入授权码"链接。有效 900 s，从 Step 1 起算。

进程核对：

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dws.exe' -or ($_.Name -eq 'pwsh.exe' -and $_.CommandLine -like '*Authorize-DingTalk*') } |
  Select-Object ProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Depth 3
```

本次：外层 pwsh 65008（07:19:34.115）、内层 dws 65052（07:19:35.404）、码 `NSXG-WHXK` 07:34:35 过期。

## 5. 权限面：`ls -l` 的 600 是假的

Node 里 `fs.writeFileSync(..., {mode:0o600})` 在 NTFS 上不生效，MSYS `ls -l` 显示 `-rw-rw-rw-`。真实证据用 ACL：

```
icacls <local>\hermes-cloud-connection.json
→ NT AUTHORITY\SYSTEM:(I)(F)  PC-...\Administrator:(I)(F)     # 仅此两行 = 已收紧
```

## 6. 汇报形态（对协调端 A2A）

1) 回填原始回执 `{"configured":true,"credentialsPrinted":false}`（附 verify 的 bundleId/sourceCommit/files）
2) 官方链接原文 + userCode + 生成/过期时刻 + 剩余分钟
3) 外层/内层 PID + 各自启动时间 + 日志绝对路径
4) 明确边界：未 activate、未 Install-HomeTask、未注册计划任务、未改系统代理/模型/A2A
5) 一句"码过期了怎么办"（dws 非零退出 → 重新发起取新码）
