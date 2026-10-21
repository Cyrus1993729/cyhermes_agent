# v2rayN 上位与双代理并存（2026-09-04）

## 本机代理环境实测（诊断完成;切换方案当时待用户确认,未执行）
- **双代理并存**:Clash Verge (verge-mihomo, 7897 mixed) 与 v2rayN 便携版 (xray, 10808 mixed) 同时在跑
  - 系统代理注册表 `ProxyServer=127.0.0.1:7897` + 用户环境变量 `HTTP(S)_PROXY=127.0.0.1:7897` → **全机实际只走 Clash**,v2rayN 的 10808 没有任何程序使用(用户以为"换了代理软件",实际切换从未生效)
- v2rayN 便携版 `D:\v2rayN-windows-64-SelfContained\`;内核 `bin\xray\xray.exe run -c config.json`
  - 实际监听 **10808 (mixed,http+socks 同端口)**:`curl -x http://127.0.0.1:10808` 通(实测 TG 302 1.3s / gstatic 204 0.75s)
  - 10809 (http) 未监听;配置文件里 10829 是残影不可用 → **以 netstat 实测端口为准**
  - GUI 配置 `guiConfigs\guiNConfig.json`:`Inbound[0]/LocalPort=10808`、`SysProxyType=0`(未接管系统代理)、`AutoRun=False`(无开机自启)

## 侦察命令
- 进程:`wmic process get Name,ProcessId,CommandLine /format:list | grep -iE "clash|v2ray|xray"`
- 端口:`netstat -ano | grep LISTENING | grep -E ":(7897|10808)"`
- 系统代理:`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"` (ProxyEnable/ProxyServer)
- 单端口连通(只读):`curl -x http://127.0.0.1:<端口> -o /dev/null -s -w "%{http_code} %{time_total}\n" https://api.telegram.org/`

## 7/13 失联时间线(误判案例)
```
07:13:07.372  sidecar 最后一条日志:api.telegram.org 走 mm[美国888-JUST] → 内核进程消失
07:13:09      gateway.log:Telegram 轮询 ConnectError (attempt 1/10)
07:13:18~14:35 连续失败(7897 无人监听),退避 5/10/20/40/60s
07:14:50      verge-mihomo.exe 新进程 (wmic CreationDate) → 7897 恢复
07:15:36      gateway.log:Telegram 恢复 (generation 8),积压补发
```
- **mm 组从头到尾 = 美国888-JUST,没切过** → 失联=Clash 内核重启,与换节点无关;用户"切回旧节点才恢复"是巧合
- 新节点本身无问题:本机 10808 socks 走新节点测 TG 302 (1.3s)、妈妈端同样顺畅

## 7897 硬编码全清单(切主代理必改)
1. Hermes `config.yaml` 4 处:platforms.telegram.proxy_url、另一平台 proxy_url、mcp_servers.x.env 的 HTTPS_PROXY/HTTP_PROXY
2. 用户环境变量 HTTP_PROXY/HTTPS_PROXY(setx 持久化)→ 改后**必须重启 gateway**(进程启动时继承环境)
3. TrendRadar 采集:`D:\Workspace\Projects\TrendRadar\crossborder_fetcher.py`、`fetch_summaries.py`、`output/update_pushed_five.py`
4. cron jobs.json(黄金周报 prompt 内引用,视上下文)
5. 系统代理注册表 ProxyServer → 127.0.0.1:10808
6. Clash Verge:退出进程 + 禁用其开机自启

## 安全切换顺序(当时定的方案)
v2rayN 多目标验证(10808 测 TG/gstatic/模型 API)→ 改配置文件 → 改环境变量 → 改系统代理 → 重启 gateway → 验证全链路(TG/X/模型API/日报采集/出口 IP)→ **最后才退 Clash**(保证兜底,不出现全网断窗口)

## 用户 GUI 动作(v2rayN 界面,直改 json 会被 GUI 退出时覆盖)
- 勾选「开机自启」(AutoRun)
- 系统代理选「自动配置系统代理」(由 v2rayN 管理,替代手改注册表)
