---
name: clash-proxy-operations
description: Clash/mihomo 运维：节点查询/切换、断连与卡死诊断。触发：换线路、代理瘫痪排查。
---

# Clash 代理运维（Clash Verge Rev / mihomo）

## 环境事实（2026-09-04 更新：主代理已切换）
- 🔴 **当前主代理 = v2rayN（xray）127.0.0.1:10808（mixed http+socks 同端口）**：系统代理、Hermes gateway（启动脚本 Hermes_Gateway.cmd/.vbs 显式写死 HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:10808）、用户环境变量、TrendRadar 脚本、cron 均已指向 10808。Clash 已停用（自启本就是关的）。⚠️ 曾踩坑：setx 环境变量对已运行进程不生效；gateway 实际代理来源=它的启动脚本
- 以下 Clash Verge(7897, mm 组) 细节保留作备用/回滚参考（2026-09-01 实测）
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

## 双代理并存（2026-09-04 实测）
- **本机曾同时跑两套代理**：Clash Verge(7897,mixed) + v2rayN 便携版(xray 内核,10808 mixed)。系统代理注册表+用户环境变量 HTTP(S)_PROXY 全指向 7897 → Clash 是实际命脉;v2rayN 换了新节点也全程闲置(无程序用它的端口)
- **"换了代理软件/节点但没生效"排查顺序**：① `wmic process get Name,ProcessId,CommandLine /format:list | grep -iE "clash|v2ray|xray"` 找代理进程 ② `netstat -ano | grep LISTENING` 看监听端口(以 netstat 实测为准,配置文件可能残留旧端口) ③ `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"` 看系统代理 ④ `env | grep -i proxy` 看环境变量 ⑤ `curl -x http://127.0.0.1:<端口>` 对 api.telegram.org/gstatic 逐端口实测(只读,不切任何配置)
- 切主代理(7897→v2rayN 10808)全链路改动清单+安全执行顺序：`references/proxy-switch-v2rayn-2026-09.md`

## Hermes 进程代理残留死端口（2026-09-05 实锤:opencode/TG 连接错误真凶）

**症状**：opencode-go 大量 `APIConnectionError`（HTTPX 栈到 `connect_tcp` 撞墙）+ `send_message: Telegram send failed: httpx.ConnectError` 同时出现；用户报"线路 100% 稳定"。**诊断顺序决定成败**——先在 Hermes 内部查实际走哪个代理，别赖网络/线路：

1. 🔴 **先验证线路本身——别凭 memory 代理拓扑当基准**（本次实踩被用户两次纠正）：我拿已退役的 Clash 7897 当"主线路"测连通性，Clash 死→误判"线路抖动"。**必须先 `netstat -ano | grep LISTENING` + `wmic process get Name,ProcessId` 确认哪个代理真活着**（本次=v2rayN xray 10808），再测。线路本身用 `curl -x http://127.0.0.1:<活端口>` 连续多次测（本次 10808 连测 5 次全 200，说明线路根本没病）
2. **看 Hermes 进程实际代理**（`psutil` 读 gateway 进程 env）：`p.environ()['HTTPS_PROXY']`——**进程环境是启动快照**，改 config 只对后来启动的进程生效
3. **看 config.yaml mtime vs gateway 重启时间**：本次 config 09-04 07:35 改成 10808、gateway 07:41 重建，但 **20:30 日志仍走 7897** → 一批带旧环境路径（独立投递/cron 子进程）没被那次重启覆盖
4. **铁证 = `routed through proxy` 日志**：`grep "routed through proxy" agent.log* | sed 's/.*\(routed through proxy [^ ]*\).*/\1/' | sort | uniq -c`——本次 45 条 send_message **全部打 7897（死端口）**一条 10808 都没有，Hermes 根本没走 v2rayN 在发
5. **归因后验证现状已干净**：`grep -c "API call failed" agent.log` 时段内失败数 vs 成功数（本次切换后 0 失败/12 成功=已恢复）

**防复发核心规则**：🔴 **代理切换后必须重启全部 Hermes 实例（含独立投递/cron 进程，不是只重启 gateway）**——进程环境是启动快照。共享代理引用的路径（send_message 独立路径、cron 子进程）是残留重灾区。

## 断连归因三查（2026-09-04 实锤:切节点≠断连原因）
用户"切新节点后 TG 失联 2.5 分钟",真相=Clash 内核无故重启,mm 组选择器从头到尾没变。判定三步:
1. **sidecar_latest.log 尾部**最后一条路由记录 → 证明选择器是否真变过(案例:最后一条=api.telegram.org 走 mm[美国888-JUST],随即进程消失)
2. **verge-mihomo.exe 的 wmic CreationDate** → 内核重启时刻(案例:07:14:50 起新进程,旧内核 07:13:07 消失 → 7897 断供)
3. **gateway.log Telegram 重连时间戳 ↔ sidecar 时间戳对齐** → 因果链闭合(07:13:09 断 → 07:15:36 恢复)
- Telegram 轮询重连:指数退避 5/10/20/40/60s、最多 10 次,断供 ~2.5 分钟;期间消息囤在 TG 服务器,恢复后补发**不丢**
- 教训:用户归因"切节点导致断连"时,先验证选择器是否真变了再下结论——内核重启/Verge 崩溃自愈也是常见真凶

## 相关
- 代理是 TG/日报/模型 API 的命脉：v2rayN(10808) 断 = 日报采集+投递+告警全断（trendradar-operations 有 8/29-30 事故归档，Clash 时代同源教训）；Codex/chatgpt.com 也依赖代理环境（新终端才拿到新代理变量）
- 代理健康监测：现有 cron api_probe 只测模型 API；"代理存活看门狗"已讨论未实施（看门狗告警必须有不依赖 TG 的兜底通道）