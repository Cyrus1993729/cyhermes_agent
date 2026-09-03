# 双机 A2A IP 监控 watchdog 部署 runbook（2026-09-02 牛来/妈妈双机实测 ✅）

## 背景

A2A 双机直连（牛来 192.168.0.112 ↔ 妈妈 192.168.0.106，各绑 :9900）靠 `a2a_agents.<对方>.url` 硬编码 IP。DHCP 换 IP 后不告警就会静默失联。两机各跑一个只监控本机 IP 的 watchdog，变化即告警。

## 脚本（已部署 C:/Users/Administrator/AppData/Local/hermes/scripts/ip_monitor.py）

关键结构（全文模板见 templates/ip_monitor.py）：

- `BASE_IP = "192.168.0.112"` — **每台机改成自己的 IP**，告警文案提示对端改 url。
- `get_lan_ip()`：`subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='utf-8', errors='replace')`，逐行找含 `IPv4`/`IP Address` 的行提取 IP，优先 192.168./10./172.; 无匹配兜底全文本 regex `192\.168\.\d{1,3}\.\d{1,3}`。
- 顶部兜底：`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`（防 GBK 管道编码崩溃，见坑2）。
- main()：ip 为 None → 打印检测失败告警 + ipconfig 片段前 400 字符；ip != BASE_IP → 打印 `⚠️ 本机局域网 IP 变了: {BASE_IP} → {ip}` + 对端需改的 url 提示。一致 → 不打印（退出 0）。

## cron 创建参数（cronjob create）

```
action=create, name=IP监控(<本机名>), schedule=every 30m, no_agent=true,
script=ip_monitor.py (相对 hermes/scripts), deliver=telegram, prompt=任意占位
```

空输出不投递；非零退出/超时发错误告警。

## 验证步骤（必做，双路径）

```bash
cd C:/Users/Administrator/AppData/Local/hermes/scripts
# 1. silent 路径: 应零输出, exit=0
python ip_monitor.py; echo exit=$?
# 2. alert 路径: 临时把 BASE_IP 改成假 IP(如 192.168.0.999) 再跑
#    应看到 ⚠️ 告警全文(验证 emoji/中文编码), 然后 patch 改回真实 IP
# 3. 改回后复测 silent, 确认零输出后再建 cron
```

顺序：正常路径 → 临时改 BASE_IP 测告警 → 改回 → 复测 → 建 cron。

## 坑

1. **ipconfig 是 UTF-16 输出**：MSYS `ipconfig | grep -iE "ipv4"` 报 `Binary file (standard input) matches`；`cat` 也是乱码/二进制。解析一律走 python subprocess + `encoding='utf-8', errors='replace'`。
2. **GBK 管道编码**：cron 捕获 stdout 时用系统 ANSI 代码页（中文系统=cp936）。`print("⚠️ ...")` 中 ⚠️ (U+26A0) 不在 GBK → UnicodeEncodeError，脚本崩溃且不投递 = 监控静默失效。必须 reconfigure 成 utf-8。
3. no_agent 脚本的 error alert 是「非零退出或超时」，不是 stderr——所以让脚本 print 告警后 `sys.exit(0)` 正常退出即可，别 exit(1)。

## 联动约定（两机都需在 memory 存）

- 本机 IP 变 → cron 自动告警 TG；**并主动发 A2A 消息**通知对方机（对方 agent 提醒用户改配置）。
- 对方 IP 变 → 用户转告 → 改本机 `a2a_agents` 里对方 url（`hermes config set a2a_agents.<名>.url http://<新IP>:9900 --force` 或 python yaml，参考改名节姿势）。
