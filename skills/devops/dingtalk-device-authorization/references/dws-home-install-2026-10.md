# DayflowHome / dws 设备授权实测记录（2026-10-21）

## 安装布局

```
%LOCALAPPDATA%\DayflowHome\
├── tools\dws\dws.exe, tools\pwsh7\pwsh.exe
├── releases\sites29-afdf902-home1\
│   ├── deployment\Authorize-DingTalk.ps1      # 读 calendar-automation.json 的 dwsConfigDir，跑 dws auth login --device --no-browser
│   └── runtime\.local\
│       ├── calendar-automation.json           # dwsConfigDir / dwsExe / pwshExe / httpProxy(127.0.0.1:10808) / intervalMinutes
│       ├── dws-config\                        # DWS_CONFIG_DIR 本体（含 logs\dws.log）
│       ├── launch-authorize-<ts>.ps1          # 起后台进程的启动器（照抄改时间戳）
│       └── dingtalk-authorize-<ts>.stderr.log # 码/链接/轮询全在这里；stdout 恒 0 字节
```

## 时间线（2026-10-21）

| 时刻 | 事件 |
|:--|:--|
| 07:19:33 | 第 1 轮发起，码约 600s 后被服务端判过期，进程自退 |
| 07:36:01 | 第 2 轮发起（pwsh 65484 → dws 64984，子 63056），用户扫码时页面提示过期 |
| 07:42:08 | `dws auth status` → `{"authenticated": false}`；第 2 轮已轮询 363s |
| 07:42:23 | 杀掉 64984/65484/63056，第 3 轮发起（pwsh 63084 → dws 64752） |
| 07:45:07–07:45:32 | `hermes send --to telegram:8938729624` 成功，`message_id=6882`（上一轮同类消息 msg_id=6881） |
| 07:47:43 | 第 3 轮仍 `[62] 轮询中 (316s)`；mtime 07:47 与启动 07:42:25 一致 = 活着在等码，不是被杀 |
| 07:47:55–07:49:00 | 对端 agent（妈妈端 A2A）转达「用户已在手机完成授权」，但 `auth status` 连查 5 次全是 `authenticated:false` → 回状态即停：未重发、未下载补丁 ZIP、未跑 verify/smoke/preflight |
| 预计 07:52 前后 | 该轮码按 600s 判过期自行退出（若始终未扫到） |

第 2 轮（0736）日志停在 363s、无过期/退出行 = 07:42:23 被我们 kill 掉的那一轮，别当成「授权成功」。

## 关键命令

```bash
# 认 PID
taskkill /PID 64984 /T /F; taskkill /PID 65484 /T /F
# 重发（照抄旧 launcher，只改时间戳）
powershell -NoProfile -ExecutionPolicy Bypass -File ...\runtime\.local\launch-authorize-20261021-0742.ps1
# bash 会挂到超时，但进程已起 —— 验证（必须按 Name 过滤，否则把自己的查询进程也算进来）：
powershell -NoProfile -Command "Get-CimInstance Win32_Process | ? { (\$_.Name -eq 'pwsh.exe' -and \$_.CommandLine -match 'Authorize-DingTalk\.ps1') -or (\$_.Name -eq 'dws.exe' -and \$_.CommandLine -match 'auth login') } | Select Name,ProcessId,ParentProcessId,CreationDate"
# 取码/链接前先脱敏再看尾巴
head -12 ...\dingtalk-authorize-20261021-0742.stderr.log   # 发给用户本人私聊用
```

## 发送用文本模板（要点齐全即可）

- 只认这条最新链接，旧链接/旧码已失效
- 组织选**原来的公司组织**（不是个人组织）
- 授权范围里**日历**和**邮箱**读取都点允许
- 有效期约 10 分钟（截止时刻写具体时间）
- 授权完不用回，后台在轮询；若又提示过期就说一声再发
