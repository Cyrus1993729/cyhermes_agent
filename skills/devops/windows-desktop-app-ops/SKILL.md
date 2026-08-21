---
name: windows-desktop-app-ops
description: 启动 Windows 桌面应用并诊断"能启动但功能异常"(如远程连接失败)时使用。
---

# Windows 桌面应用启动与故障诊断

用户要求"启动某桌面软件"(如向日葵/AweSun 远程控制)或"XX软件为什么连不上"时触发。这是一类**可复用**的运维任务，不是一次性杂活。

> 具体案例见 `references/awesun-sunflower-case.md`（向日葵实测诊断路径、命令、路径）。

## 核心心态
- "启动应用" ≠ "应用正常"。启动只是让进程/窗口起来，**功能是否可用/能否连接是要另行验证的**。
- 用户报"以前能连，现在连不上"时，以"以前能连"为基准，找**现在哪里变了**，而不是从头猜。

## 第一步：精确找到并启动软件
1. 定位可执行文件（常见安装路径 + 按厂商名 grep）：
   ```bash
   ls -d /c/Program*/Oray* /c/Program*/Sunlogin* 2>/dev/null
   find "/c/Program Files/<厂商>" -maxdepth 2 -iname "*.exe" 2>/dev/null
   ```
2. 启动（MSYS bash 下用 cmd 启动 GUI，避免阻塞）：
   ```bash
   cd "/c/Program Files/<厂商>/<子目录>" && cmd //c start "" "App.exe"
   ```
3. 用 `tasklist` 确认进程起来了（注意：`ps aux` 在 MSYS 下可能漏报 Windows 原生 GUI 进程，**用 tasklist 更可靠**）。

## 第二步：识别"陈旧残留进程"（关键坑）
启动前必须先查进程**启动时间**。远程控制/常驻类软件长期运行极易僵死——界面显示"在线"但新会话/鉴权/中继通道没重建，别人就永远连不上。
```bash
# 看创建时间，对比当前日期
wmic process where "ProcessId=<pid> or ProcessId=<pid>" get ProcessId,CreationDate
date "+%Y-%m-%d %H:%M:%S"
```
- 若进程已跑多天(如 4 天)而用户刚让我"启动"，说明**你启动的其实是陈旧僵死实例**——"启动"只是把旧进程唤起。
- 遇此 → 建议**彻底重启**（结束全部相关进程包括守护进程，再重新拉起），而不是只跑一次启动命令。

## 第三步：诊断"为什么连不上"
按序排查，每步给结论：
1. **网络连通性** —— 应用对端服务器通不通：
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" --noproxy '*' -m 8 https://<厂商官网>
   ```
   （国内软件官网可能走 GFW，视情况 `--noproxy '*'` 直连。）
2. **厂商中继服务器的 ESTABLISHED 连接** —— 客户端是否真正连上了中继/登录服务器：
   ```bash
   netstat -ano | grep ESTABLISHED | grep -wE "<pid1>|<pid2>"
   ```
   对向日葵：ESTABLISHED 指向 443 端口 = 连到了阿里云中继，说明客户端→服务器通道是通的。
3. **登录/配置目录是否为空** —— 判断是否登录、凭据是否保存：
   ```bash
   ls -la /c/Users/<user>/AppData/Roaming/<App>/   # 空 = 未登录或凭据未落盘
   ```
4. **进程是否有对外活动连接**（纯 LISTENING 本地端口 ≠ 已接入服务）。

## 第四步：给出方案并等待确认
- 结束进程类操作（会中断用户正在用的东西）**必须先征得同意**。
- 用户有"改配置/结束进程前须同意"的偏好，若涉及杀进程，给出明确要执行的 PID 清单再动手。

## Pitfalls
- MSYS bash 下 `ps aux` 常漏报原生 Windows GUI 进程 → 用 `tasklist`。
- `netstat` 按进程名过滤无效（显示的是 PID），用 `grep -wE "<pid>"`。
- 结束进程禁止 `taskkill /F /IM python.exe`（会杀 Agent 自身）；桌面软件用 `taskkill /PID <pid>` 逐个结束。
- 判断"连不上"时，进程在跑 + 有到服务器的连接 ≠ 一切正常，还要看进程是不是陈旧僵死 + 是否登录。
