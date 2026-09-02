---
name: clash-proxy-operations
description: Clash/mihomo 运维：节点查询/切换、断连与卡死诊断。触发：换线路、代理瘫痪排查。
---

# Clash 代理运维（Clash Verge Rev / mihomo）

## 环境事实（本机 2026-09-01 实测）
- 客户端：Clash Verge Rev，内核 verge-mihomo（进程 `verge-mihomo.exe`）
- 运行配置：`C:\Users\Administrator\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml`（Verge 合并后的运行配置，~985 行）
- **控制面 = 命名管道**：`\.\pipe\verge-mihomo`（mihomo 启动参数 `-ext-ctl-pipe`）；配置里 `external-controller: ''`（**无 HTTP API**），secret=set-your-secret（无效）
- 代理端口 7897；TG/模型 API/热榜采集全走代理（Clash 死=全网出境断）
- 主选择组名 **mm**（type: select）；"自动选择"组 = url-test（interval 86400）；其余组：故障转移等
- 节点清单：clash-verge.yaml `proxy-groups:` 下 `- name: mm` 的 `proxies:` 列表
- 节点现状（2026-09-01）：OVH（美国111-OVH）已由用户移除；当时选中 美国444-MEL；亚太候选仅 新加坡111-MEL、日本1200-MEL-ipv6（无香港节点）。⚠️ 节点/选中项是易变状态，动手前重新查询

## 查询当前选中节点（✅ 已验证 2026-09-01）
mihomo 命名管道：PowerShell `NamedPipeClientStream` → 发 HTTP 请求 `GET /proxies/mm` → 响应 JSON 的 `"now"` 字段 = 当前节点。

```powershell
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', 'verge-mihomo', [System.IO.Pipes.PipeDirection]::InOut, [System.IO.Pipes.PipeOptions]::None)
$pipe.Connect(3000)
$req = [System.Text.Encoding]::UTF8.GetBytes("GET /proxies/mm HTTP/1.1`r`nHost: localhost`r`nConnection: close`r`n`r`n")
$pipe.Write($req, 0, $req.Length); $pipe.Flush()
$reader = New-Object System.IO.StreamReader($pipe, [System.Text.Encoding]::UTF8)
$resp = $reader.ReadToEnd(); $pipe.Close()
[System.IO.File]::WriteAllText('C:\ProgramData\clash_pipe_resp.json', $resp, [System.Text.Encoding]::UTF8)
```
实测响应 ~777 字节，含 `"now": "美国444-MEL"` 与 `"all": [...]` 节点数组。`GET /proxies` 可拿全部组。

**坑（全部实踩）**：
- 🔴 stdout 输出含中文会 GBK 乱码（subprocess 解码炸）→ **响应写 UTF-8 文件，再用 python 读**（`errors='replace'`）
- 🔴 **管道流不支持 ReadTimeout**（报"此流不支持超时"）→ 用 `StreamReader.ReadToEnd()` 等 EOF（mihomo 响应后关闭连接）；不要设 ReadTimeout、不要裸同步 Read 循环
- `cache.db` **不是 sqlite**（Verge 缓存格式非 sqlite，sqlite3 打开报 "file is not a database"）——别浪费时间解析
- PowerShell 脚本含中文 → 存 UTF-8 BOM（PS 5.1 GBK 解析 bug，见 windows-desktop-app-ops）

## 切换节点（⚠️ 未验证 + 用户红线）
- 🔴 **用户红线：禁止自动切换 Clash 节点**——卡死时人工重启；只有用户明确说"换掉/切换"才可操作，且列候选节点让用户拍板
- 原理（未实测，2026-09-01 用户中途叫停）：同管道姿势发 `PUT /proxies/mm`，body `{"name":"<节点名>"}`；切完必须验证：`curl -x http://127.0.0.1:7897 https://api.ip.sb/ip`（或类似）出口 IP 变化 + TG/模型 API 连通
- 执行前先列候选与推荐（参考延迟/稳定性：亚太 > 美国 > 欧洲；避开 OVH 欧洲线——8/29-30 事故源）

## 故障诊断（8/29-30 44h 事故 + 本会实验证）
- **SYN_SENT 挂起 = 节点线路问题证据**：`netstat -ano | grep SYN_SENT`（2026-09-01 实测 Clash 对 OVH 51.91.250.79:443 挂起；8/29 同源"美国111-OVH"线路不稳——先怪线路，再怪客户端）
- **sidecar 进程卡死特征**：进程活着 + sidecar 日志静止（`C:\Users\Administrator\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\logs\sidecar\sidecar_latest.log` 无新行）+ 全网出境断
- **TG 收不到任何消息 = 代理死的硬证据**（TG 必须走代理）；告警也走 TG → 故障时告警一起失明
- 诊断顺序：先问用户屏幕/重启状态（8/30 教训：Event 41/6008 ≠ 系统崩溃，手动断电也记）→ netstat SYN_SENT → sidecar 日志时间戳 → 恢复验证
- "断流的观感"分层：单次断流/节点不稳 = 线路问题；进程级长时卡死 = mihomo 客户端问题（Hiddify/sing-box 内核一般不进程级僵死，可作对比参考）

## 相关
- 代理是 TG/日报/模型 API 的命脉：Clash 断 = 日报采集+投递+告警全断（trendradar-operations 有 8/29-30 事故归档）
- 代理健康监测：现有 cron api_probe 只测模型 API；"代理存活看门狗"已讨论未实施（看门狗告警必须有不依赖 TG 的兜底通道）