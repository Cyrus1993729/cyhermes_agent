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
