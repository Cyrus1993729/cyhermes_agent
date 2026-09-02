# 向日葵 (Oray AweSun) 实测案例 — 2026-08-20

操作系统：Windows 10。用户报告"启动向日葵后无法远程连接，以前能连"。

## 关键路径（Windows）
- 可执行文件：`C:\Program Files\Oray\AweSun\AweSun.exe`
- 进程名：`AweSun.exe`(主程序，可能多个) + `awesun_guard.exe`(守护)
- 配置目录：`C:\Users\<user>\AppData\Roaming\AweSun\`
  - 只有 `libCachedImageData.json` + `shared_preferences.json` = **未保存登录凭据**（登录状态可疑的信号）
- 数据目录：`C:\ProgramData\Oray\` `C:\ProgramData\OrayClient\`

## 诊断命令（验证有效）
```bash
# 找进程 + PID
tasklist | grep -i awesun
# 判断是否陈旧残留（关键）：看创建时间 vs 当前
wmic process where "ProcessId=4380 or ProcessId=6252 or ProcessId=2848" get ProcessId,CreationDate
date "+%Y-%m-%d %H:%M:%S"
# 网络连通性（直连官网）
curl -s -o /dev/null -w "%{http_code}\n" --noproxy '*' -m 8 https://sunlogin.oray.com
# 客户端到中继服务器的 ESTABLISHED 连接（对向日葵指向 443 = 通）
netstat -ano | grep ESTABLISHED | grep -wE "2848|4380"
```

## 本次诊断结论
- 网络到官网 200 通；进程有 ESTABLISHED 连接指向阿里云 443 = 中继通道通。
- 但**进程创建时间是 4 天前**(20260816)，早已僵死：界面看似在线，实际新会话/鉴权/中继通道没重建 → 别人连不上。
- 正确动作：彻底重启（结束全部 AweSun.exe + awesun_guard.exe，再重新拉 AweSun.exe），而非只启动一次。
- **杀进程前须用户确认**（用户偏好：改配置/结束进程前须同意）。

## 启动命令
```bash
cd "/c/Program Files/Oray/AweSun" && cmd //c start "" "AweSun.exe"
```

---

# 向日葵 (Oray AweSun) 实测案例二 — 2026-09-01（Session 0/1 陷阱）

用户报告"远程连接显示不在线"，随后要求核对识别码（用户称 390138142）。

## 时间线
1. 杀净 3 个陈旧实例（8/30 22:40 开机自启叠加）→ 从 Hermes 用 `Start-Process` 重新拉起 → 进程活了、连上中继（多条 443 ESTABLISHED）→ **但用户仍连不上**。
2. 查 `query session`：用户已登录 console（Session 1）；`(Get-Process AweSun).SessionId` = **0** → **AweSun 被拉进了 Session 0（服务会话）**！GUI 应用在 Session 0 无可见桌面、注册态异常 → 手机端"不在线/连不上"。
3. 修复：`TASKKILL.EXE /PID` 杀净 → schtasks 交互任务（`/it /ru Administrator`）在 Session 1 拉起 → 验证 SessionId=1（注意服务组件会再拉 Session 0 实例，以 Session 1 为准）。
4. 截屏验证：Session 0 里 `CopyFromScreen` 报"句柄无效"→ 用 schtasks /it 交互任务跑截屏 ps1（存 `C:\ProgramData\Oray\screen_probe.png`）→ Session 0 读图 + vision_analyze。
5. GUI 实读：识别码 **447420158**（与 sys_config.ini `fastcode=k447420158` 一致）、账号"崔宇"、🟢在线、验证码 6 圆点隐藏（需点"眼睛"）；历史识别码 1761807119。用户报的 390138142 在 GUI/配置中均不存在 → 不是本机码（可能是账号下另一台设备）。

## 本案例新经验
- **从 Hermes 启动 GUI 应用 = Session 0 陷阱**（详见 SKILL.md Pitfalls）。
- **schtasks /it 交互任务**在这台机器（用户已登录 console）可靠执行，可用来：① 在 Session 1 启动 GUI 应用；② 在 Session 1 截屏（CopyFromScreen 探针）。
- 向日葵识别码：`sys_config.ini fastcode`（k+9 位）与 GUI 一致；免费版重初始化后识别码可能变，以 GUI 实读为准，不武断说用户记错。
- 验证码是 GUI 动态显示（圆点隐藏），配置文件里 `fastcodepsw`/`sunloginaccesspassword` 是加密的固定访问密码，不是临时验证码；同账号直连免验证码。
- 截屏 ps1 模板见 SKILL.md（第五步相关）；输出路径必须选 Session 0 可读的共享位置（ProgramData 优于用户 AppData）。
