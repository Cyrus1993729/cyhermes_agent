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

## 第五步：GUI 不可见时读取应用状态（向日葵类远程软件识别码/验证码）
- **识别码权威来源 = GUI 大字显示**（无头时退而求其次）：
  - 配置文件：向日葵 `C:\ProgramData\Oray\AweSun\sys_config.ini` 的 `fastcode=k447420158`（k+9 位数字=识别码；`sunlogincode` 是序列号不是识别码；`[history_record_info]` 有历史识别码）
  - 注册表：`HKLM\SOFTWARE\Oray\AweSun\AweSun` 的 `machine_code`（加密，不可直接读）
  - ⚠️ 免费版识别码在设备重新初始化（clientId 重生成）时**可能变化**；用户报的码与配置不符时，**以 GUI 实读为准**（截屏 vision_analyze），不要断言用户记错
- **验证码**：动态 6 位，只显示在 GUI 上且被圆点隐藏（需点"眼睛"图标）；配置文件里的 `fastcodepsw`/`sunloginaccesspassword` 是**加密的固定访问密码**，不是临时验证码
- **同账号直连免验证码**：被控端已登录账号（sys_config.ini 有 access_token）时，主控端登录同一账号即可从设备列表直连；识别码+验证码只在"非账号直连"时必需
- 设备名/主机名在安装目录 `config.ini`：`hostname=PC-xxx`、`macaddress=xx:xx...`

## Pitfalls
- MSYS bash 下 `ps aux` 常漏报原生 Windows GUI 进程 → 用 `tasklist`。
- `netstat` 按进程名过滤无效（显示的是 PID），用 `grep -wE "<pid>"`。
- 结束进程禁止 `taskkill /F /IM python.exe`（会杀 Agent 自身）；桌面软件用 `taskkill /PID <pid>` 逐个结束。
- 🔴 **MSYS bash 下 taskkill 的斜杠坑（2026-09-01 实踩）**：`taskkill //PID 4228 //F` 报"无效参数/选项 - '//PID'"（MSYS 路径转换把单斜杠转成了双斜杠）；**正确姿势：`TASKKILL.EXE /PID 4228 /F`（TASKKILL.EXE + 单斜杠直接可行，无需 MSYS_NO_PATHCONV）**。另一个失败姿势：`cmd //c "taskkill ..."` 会开交互提示符不执行。杀完用 `powershell "(Get-Process <App> -ErrorAction SilentlyContinue | Measure-Object).Count"` 确认归零。
- 🔴 **`cmd //c start` 可能静默失败（2026-09-01 实踩：AweSun 没起）**：cmd 返回提示符、无报错，但进程根本没起来（原因不定：路径/会话权限）。**失败时改用 PowerShell：`powershell -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\...\App.exe'"`**，睡眠 8-10 秒后必须用 `Get-Process` 验证进程真正存在。
- 🔴 **从 Hermes 启动的 GUI 应用会掉进 Session 0（2026-09-01 AweSun 实踩，本类问题最隐蔽的坑）**：Hermes 跑在 Windows **Session 0（services 会话）**，用 `Start-Process`/`cmd start` 拉起的 GUI 应用**继承 Session 0**——进程活着、能连服务器、但 GUI 不可见、注册/鉴权态异常，用户端看到"设备不在线/连不上"。**判定**：`powershell "(Get-Process <App>).SessionId"` 应为 1（用户交互会话）；为 0 即中招。**修复**：杀净进程 → 用 schtasks **交互任务**在用户会话（Session 1）重新拉起：
  ```bash
  # 用户必须已登录 console（query session 确认）
  MSYS_NO_PATHCONV=1 schtasks /create /tn "StartApp" /tr "\"C:\Program Files\...\App.exe\"" /sc once /st 23:59 /it /ru Administrator /f
  MSYS_NO_PATHCONV=1 schtasks /run /tn "StartApp"
  # 验证: Get-Process <App> | Select Id,SessionId  → SessionId=1 才算成功
  ```
  本机实测 schtasks /run 在 /it + 已登录用户下**可靠执行**（未遇"装睡"）。注意：杀完 Session 0 实例后，服务组件可能自动再拉 Session 0 客户端（AweSun 曾同时 3 个 Session 0 + 1 个 Session 1），以 Session 1 实例为准。
- 🔴 **Session 0 截屏必败（"句柄无效"），用 schtasks 交互任务在 Session 1 截屏**：Session 0 里 `CopyFromScreen` 抛 Win32Exception（无可见桌面）。**正确姿势**：写截屏 ps1 存到共享路径（如 `C:\ProgramData\<App>\probe.ps1`，输出 png 也存 ProgramData），`schtasks /create ... /it /ru Administrator` + `/run` 在 Session 1 执行，Session 0 读文件 + `vision_analyze` 看图。ps1 要点：`[System.Windows.Forms.Screen]::PrimaryScreen.Bounds` + `CopyFromScreen(0,0,0,0,$b.Size)` + `$bmp.Save(..., [ImageFormat]::Png)`。锁屏/无桌面时会失败（输出 SCREEN_FAIL），此时改走配置文件/注册表。
- 🔴 **ps1 含中文必须存 UTF-8 BOM（2026-09-01 实踩）**：PowerShell 5.1 按 ANSI(GBK) 读取无 BOM 的 UTF-8 .ps1，含中文（如 `-match '向日葵'`）的文件直接报"字符串缺少终止符"类解析错。**写 ps1 用 python `open(p,'w',encoding='utf-8-sig')`**（或其他工具加 BOM）。另：MSYS bash 下 `powershell -File` 的路径参数反斜杠会被吞（`C:ProgramDataOray...`）→ 用单引号包正斜杠路径 `-File 'C:/ProgramData/.../probe.ps1'`。
- 🔴 **schtasks 交互任务执行 powershell 会在桌面弹窗遮挡**：`/it` 任务跑 powershell 会弹出一个 PowerShell 窗口（每次都遮挡目标窗口）。**隐藏姿势**：`/tr` 里加 `-WindowStyle Hidden`；或写 vbs 包装 `ws.Run "powershell ... -File xxx.ps1", 0, False`（wscript 无窗口）。schtasks /run 偶发"装睡"（提示成功但没执行，本次 MISS 过一次）→ 无输出/无文件时**重跑一次**。
- 🔴 **置顶窗口用 FindWindow+SetWindowPos(HWND_TOPMOST)，不要依赖 SetForegroundWindow**：SetForegroundWindow 受前台锁限制不可靠（同脚本两次调用一次成功一次失败）；`EnumWindows` 按标题匹配（如 `-match '向日葵'`）+ `SetWindowPos(hwnd, [IntPtr](-1), 0,0,0,0, 0x43)`（HWND_TOPMOST + NOSIZE|NOMOVE|SHOWWINDOW）稳定置顶。窗口置顶后位置可能变化，**点击前重新截屏定位坐标**，不要用上一轮的旧坐标。
- 🔴 **Webview2 渲染的 GUI（向日葵新版）对合成鼠标/键盘事件免疫（2026-09-01 实踩）**：SendInput 网格点击（多坐标）、mouse_event、Ctrl+A/C 复制剪贴板**全部无效**——验证码这类被隐藏的动态内容**无法通过程序自动化读取**，只能人工在屏幕上点。**不要浪费时间反复尝试自动化点击**；改用真正可行的路径：同账号直连免验证码（见第五步）、或让用户在电脑前点一下。失败的尝试序列不要固化为"可重试的工作流"。
- 🔴 **常驻远程控制软件"进程在+已连服务器但设备离线"= 多实例/僵尸实例叠加（2026-09-01 AweSun 实踩）**：现象 = 3 个 AweSun 实例（同一次开机自启叠加产生）都在跑、且有 ESTABLISHED 到中继服务器（阿里云 443）的连接，但玩客端显示"不在线"。修复 = **杀净全部实例（TASKKILL.EXE /PID 逐个）→ Start-Process 重启单实例 → 验证新进程有 4-6 条新 ESTABLISHED 连接**（`netstat -ano | grep -E "ESTABLISHED" | grep <pid>`，连国内阿里云/腾讯云 IP:443 = 已注册上线）。判定"在线"不能只看进程存在或旧连接，要看**新实例**建立的新连接。
- 判断"连不上"时，进程在跑 + 有到服务器的连接 ≠ 一切正常，还要看进程是不是陈旧僵死 + 是否登录。
- 🔴 **用 `psutil` 按 cmdline 子串找进程时，诊断脚本自己也会被匹配到（2026-10-18 实踩）**：
  `python -c "...'hermes_cli.main'..."` 这类一行式诊断命令，**其自身 cmdline 就包含那些搜索字符串**，
  `process_iter` 会把诊断进程自己（以及同类的其他诊断调用）一起返回 → **报出虚高的进程数**。
  本次因此向用户报了"7 个 gateway 进程"，实际只有 4 个。
  **修法（三层都上）**：
  ① 开头 `me = psutil.Process()`，循环里 `if p.info['pid'] == me.pid: continue`；
  ② 把诊断脚本**落盘成文件**跑（`python pcheck.py`）而不是 `python -c`，更容易排除；
  ③ 再加一道字符串兜底 `if 'process_iter' in cl: continue`。
  **通用教训：任何按 cmdline 匹配得到的进程统计，报数前先自问"我自己是不是也被算进去了"。**
  另：MSYS 下 `python /tmp/x.py` 会报 `can't open file 'C:\tmp\x.py'`（原生程序不认 MSYS 路径）
  → 脚本写到 Windows 绝对路径（如 `%LOCALAPPDATA%\Temp\`）再 `cd` 过去用相对路径跑。

## 🔴 识别"到底是哪个应用"——读源码/翻安装目录之前必做

**2026-10-18 实踩：把用户用了很久的客户端认成了另一个同名软件**，用户直接回"你完全搞错了"。

同为 hermes-desktop 的两个不同软件同时存在于本机：

| 路径 | 是谁 |
|:--|:--|
| `%LOCALAPPDATA%\Programs\hermes-desktop` | 第三方，`package.json` author=fathah |
| `%LOCALAPPDATA%\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe` | **从仓库构建的，用户在用的那个** |

凭安装目录枚举或屏幕照片猜身份会翻车。**正确顺序：**

1. **先拿运行中进程的可执行体绝对路径** —— 这才是"用户在用的那个"：
   ```python
   import psutil
   for p in psutil.process_iter(['pid','name','exe','cmdline']):
       # 务必排除自身（见上方 psutil 自匹配坑）
   ```
2. **只读那个路径下的 bundle**，不要读别的目录
3. 拿不到进程时，才退回按安装目录枚举，并明确声明"未验证是运行中的那个"

**读 Electron 应用（app.asar）的两步：**

```python
import json, struct
head = open("app.asar","rb").read(32 << 20)   # 🔴 头可能 >4MB，别只读 4MB
json_size = struct.unpack("<I", head[12:16])[0]  # JSON 从 offset 16 开始
obj = json.JSONDecoder().raw_decode(head[16:].decode("utf-8","replace"))[0]
# 数据区起点 = 16 + json_size；文件绝对偏移 = 数据区起点 + entry["offset"]
```
先把渲染进程 bundle（`out/renderer/assets/index-*.js`）提取成独立文件再 grep，
比直接在 200MB+ 的 asar 上 grep 可靠（asar 里长行会让 `grep -o` 静默失手）。

🔴 **grep 界面文字前先想 CSS**：界面上显示的 `BOTS` 可能只是 `text-transform: uppercase` 渲染出来的，
源码里写的是 `Bots`/`bots`。**直接搜大写会 0 命中，并让你得出"这软件没这个功能"的错误结论。**
搜界面文字时大小写两种形式都搜，或搜它旁边的唯一标识串。

**结论句式要求**：断言"某软件没有某功能"之前，必须能说清你是从哪个**进程路径**下、哪份 bundle 里搜的。

