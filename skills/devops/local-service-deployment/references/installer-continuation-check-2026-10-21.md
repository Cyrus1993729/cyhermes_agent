# 安装包型部署 · 断点续作核查实录（2026-10-21，Dayflow 家庭同步）

背景：2026-10-20 完成解压/安装/三项工具安装后，协调端（另一台机的 agent）模型额度耗尽中断；次日经 A2A 接续，任务书要求**只核查 + 刷新过期公钥请求**，不重复安装。

## 定位锚点（续作时先确认，别猜）
- 解压根：`C:/Users/Administrator/AppData/Local/DayflowHome`
- 实际安装目录（releases 版式）：`.../DayflowHome/releases/sites29-afdf902-home1`
- `tools/`（node24 / pwsh7 / dws / dws-skills）留在解压根，**不在 release 目录里** → 命令在 release 跑、工具用绝对路径
- homeId `7d4b5206-0989-4ca6-9e29-f817197b6414`；bundleId `sites29-afdf902-home1`；sourceCommit `afdf902a44700cdbc5e45bb9c748f43f901338a5`（verify 回执 51 files）
- 私有状态目录：`<release>/runtime/.local/`（calendar-automation.json / work-host.json / home-deployment.json / connection-request*）

## 核查命令
```bash
N="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
cd "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1"
"$N" deployment/home.mjs verify    # {"verified":true,"bundleId":...,"sourceCommit":...,"files":51}
"$N" deployment/home.mjs smoke     # {"importsComplete":true,"node":"v24.22.0","noNetwork":true}
"$N" deployment/home.mjs connection-request   # 幂等：请求件仍有效原样返回，过期则重新生成
```
状态批量查：
```bash
D="<release>/runtime/.local"
ls -la "$D" | grep -E "connection|home-enabled|lock"   # 全无 = 未配置/未激活/无运行中进程
schtasks /Query /FO CSV | grep -i dayflow              # 无输出 = 未注册任务
find "C:/Users/Administrator/AppData/Local/DayflowHome" -maxdepth 4 \
  -name home-enabled.json -o -name hermes-cloud-connection.json -o -name work-sync.lock
```

## 第三方 CLI 授权状态只读探针（dws 示例，只输出布尔）
```bash
"$N" -e "
const fs=require('fs'),{spawnSync}=require('child_process');
const cfg=JSON.parse(fs.readFileSync('runtime/.local/calendar-automation.json','utf8').replace(/^\uFEFF/,''));
const r=spawnSync(cfg.dwsExe,['auth','status','--format','json'],
  {env:{...process.env,DWS_CONFIG_DIR:cfg.dwsConfigDir},encoding:'utf8',windowsHide:true,timeout:60000});
let v=null;try{v=JSON.parse((r.stdout||'').replace(/^\uFEFF/,''))}catch{}
console.log(JSON.stringify({exit:r.status,authenticated:v?v.authenticated===true:null,
  hasCorp:!!(v&&v.corp_id),hasUser:!!(v&&v.user_id),
  stderrTail:(r.stderr||'').slice(-200).replace(/[A-Za-z0-9_-]{20,}/g,'<redacted>')}));
"
```
本次结果：`authenticated=false, hasCorp=false, hasUser=false` → 钉钉未授权，按约定不发起扫码、不做 preflight。

## 公钥请求（过期刷新）
- 旧件 nonce `dc59a981-24db-41f6-bcb4-4761769fc992`，`expiresAt 2026-10-20T14:52:42Z`（北京时间 22:52，已过期）
- 重跑后新件 `expiresAt 2026-10-20T23:45:37.246Z`（北京时间 2026-10-21 07:45:37）；RSA-3072 SPKI 公钥只进请求 JSON，私钥固定落 `runtime/.local/connection-request-private.pem`（0600，不回传）
- 回填：`connection-import` 从 stdin 读 `{wrappedKey,iv,tag,ciphertext}`，校验 nonce/homeId/bundleId/url 后写连接文件并自删请求件与私钥，返回 `{configured:true,credentialsPrinted:false}`
- 已有连接文件且 key 不同时脚本拒绝替换（`A different connection already exists`）→ 遇报错别删文件，先报告

## 归档哈希（本次实测，与随包校验源逐字一致）
| 归档 | 实测 SHA256 | 官方来源 |
|---|---|---|
| node-v24.22.0-win-x64.zip | `f9683a19877e12a9b167305c8db71040d812876359de21f0d2e97c3f321f80c3` | https://nodejs.org/dist/v24.22.0/node-v24.22.0-win-x64.zip |
| PowerShell-7.6.7-win-x64.zip | `d2f952ebdbf24386cb8923553aa58e41a846db35a6155ea04c58142a4b16dbb7` | https://github.com/PowerShell/PowerShell/releases/download/v7.6.7/PowerShell-7.6.7-win-x64.zip |
| Dayflow-Home-Deployment-sites29-home1.zip | `0b9c7ebbdc9270d61585c3934c57dfaadd9ecfcdd882b73ee48a1326ac908b6a` | 协调端给定值，实测一致 |

交叉验证：Node 归档比对随包 `node-SHASUMS256.txt` 同名条目；pwsh 比对 `download_manifest.json`；再核已安装运行时版本（`tools/node24/node.exe -v` → v24.22.0、`tools/pwsh7/pwsh.exe -Command '$PSVersionTable.PSVersion'` → 7.6.7）。

## 后续顺序（本轮结束时四项皆空）
connection-import → 钉钉扫码 → preflight（DWS 已授权 + 身份与云端已选源匹配）→ activate（30 分钟内 preflight + 签名 permit）→ 注册 `Dayflow-Work-Sync`。
