---
name: hermes-windows-ops
description: "杀进程、路径参数报错、需重启 gateway 时用（Windows/MSYS 运维）。"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [windows, msys, git-bash, process, gateway, ops]
---

# Windows / MSYS 运维（Hermes 本机）

本机环境：Windows 10 + `terminal` 工具走 **git-bash / MSYS**（不是 PowerShell、不是 cmd.exe）。
下面三类坑都是在真机踩过的，从 memory 移入本 skill（2026-10-18）。

---

## 一、🔴 杀进程红线（最高优先级）

**绝对禁止** `taskkill /F /IM python.exe`。

Hermes Agent 自己是 python 进程，这条命令会**杀掉 Agent 自身**，直接断掉会话。

### 正确做法

```bash
# 1) 先排查，拿到 PID
tasklist | grep -i python        # 或
ps aux | grep -i <关键词>          # MSYS 下推荐这个

# 2) 按 PID 精确杀
taskkill /PID <pid>
taskkill /PID <pid> /T /F          # 连子进程一起，必要时才加 /F
```

### MSYS 下的两个坑

- **`//PID` 双斜杠会报错**。MSYS 的路径转换会把 `/PID` 当成路径，写成 `//PID` 试图转义——同样不行。
  写法：`TASKKILL.EXE /PID <pid> /F`（用 `.EXE` 后缀 + 单斜杠）
- **`cmd //c ...` 会开交互**，不要用来包 taskkill。直接用 `TASKKILL.EXE`。

### 排查进程

用 Python 更可靠（避免把自己的诊断命令也算进去——脚本正文里若含 `psutil`、`process_iter`、
目标关键词等字面量，`psutil.process_iter` 会匹配到自己）：

```python
import psutil, os
me = os.getpid()
for p in psutil.process_iter(['pid','name','cmdline']):
    try:
        if p.info['pid'] == me:      # 排除自身
            continue
        cl = ' '.join(p.info['cmdline'] or [])
        if 'process_iter' in cl:      # 排除同类诊断脚本
            continue
        ...
    except Exception:
        pass
```

---

## 二、MSYS 路径参数坑

**原生程序（curl / python / node / git / rg …）不认 `~/` 和 `/tmp` 路径参数。**

MSYS 只对 bash 内建命令（`cd`、`ls`）做路径翻译；传给原生程序的参数**不做转换**，
于是 `/tmp/a.py` 会被解释成 `C:\tmp\a.py`，报 `No such file or directory`。

### 三种解法

1. **先 cd 再用相对路径**（最稳）
   ```bash
   cd /c/Users/Administrator/AppData/Local/Temp && python script.py
   ```
2. **传 Windows 绝对路径**（正斜杠）
   ```bash
   python "C:/Users/Administrator/AppData/Local/Temp/script.py"
   ```
3. **用 `$LOCALAPPDATA/Temp` 代替 `/tmp`** 作为临时文件位置

> `cd /c/Users/...` 这类 **bash 内建**没问题；出问题的是**把它们当参数传给原生程序**。

---

## 三、Hermes gateway 重启姿势

### 🔴 消息平台会话内禁止直接 stop/start

**在 Telegram / 微信等消息平台的会话里，绝对不能执行 `hermes gateway stop` / `start`。**
gateway 就是你的通信通道，stop 会当场把通道切断；如果后续 start 失败，
Agent 还活着但**彻底联系不上**。"先确认再执行"的往返也会因为中途断线而丢失执行意图。

而且 gateway 进程内有安全防护，会直接 **BLOCKED** 掉这类命令。

### 可靠做法

| 场景 | 做法 |
|---|---|
| 最可靠（全自动） | 杀 gateway PID + `schtasks /run /tn Hermes_Gateway` |
| 用户在桌面端（Hermes.exe）内 | 可用内置 `/restart` 斜杠命令（优雅重启） |
| 用户在 CLI 里 | 退出重进即可 |

`/restart` 在消息平台会话里**也是可行的**——它是 gateway 自己处理的重启，不是外部 kill。
让用户发一句 `/restart` 往往比自己杀 PID 更稳。

### ✅ 换 `.env` 里的 key **不需要**重启 gateway

`cron/scheduler.py` 每次 tick 都会重新读 `.env` 和 `config.yaml`（源码注释：
*"Re-read .env and config.yaml fresh every run"*），所以新 key 最多 30 分钟内自动生效。

⚠️ **但适配器持有的凭据不会重载**：平台适配器（如微信）在 `__init__` 里把 token 读进实例属性，
换 token 必须重启 gateway。详见 skill `hermes-wechat-delivery`。

### 进程数核对

```bash
hermes gateway list      # 列出所有 profile 及其 gateway 状态
hermes gateway status    # 当前 gateway 状态
hermes profile list      # 所有 profile
```

本机正常形态：`gateway run` 呈现 supervisor → worker 两层，**不是**一个进程；
统计时别把 supervisor/worker 对算成"重复实例"。
