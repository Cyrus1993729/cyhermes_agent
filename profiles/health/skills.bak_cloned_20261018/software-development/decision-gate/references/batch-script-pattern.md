# 批处理脚本模式：安全执行通道中断操作

## 触发条件

当需要执行的操作会中断当前通信通道（如 `gateway stop`、升级 Hermes、更换 venv），且
通过微信执行存在「确认→执行」窗口被网关重启吞掉的风险时，使用此模式。

## 模式：为用护编写 .bat 脚本 → 用护手动双击执行

```
  你（Agent）写入脚本 → 发送 MEDIA 给用护 → 用护双击运行 → 窗口输出每一步结果
```

- ✅ 完全绕过微信通道
- ✅ 失账自动回滚
- ✅ 用护看窗口输出，不需要懂代码
- ✅ 出问题截图发你

## 脚本必须包含

1. **Step 0: 环境验证** — 检查目录存在、Python 存在、git remote 可达
2. **完整备份** — robocopy 整目录，保留回滚路径
3. **停止 Gateway** — Get-CimInstance Win32_Process（非 Get-Process）
4. **主操作**
5. **启动 Gateway** — 新窗口，start /MIN
6. **:rollback 标签** — 任何一步失败跳到此处，恢复备份 + 重启

## 审查流程

1. 写脚本
2. 让 Claude（Sonnet）审查
3. 修复问题
4. 让 Claude 再審一次
5. 确认 PASS → 发给用护

## 已知坑（Claude 审查发现）

- `Get-Process` 没有 `CommandLine` 属性 → 用 `Get-CimInstance Win32_Process`
- `%date%` 中文 Windows 含空格和斜杠 → `for /f` 提取安全日期
- `start` 命令嵌套引号会导致路径含空格时闪退 → 变量直接用 `%VAR%`，不包额外引号
- `robocopy /COPYALL` 需要管理员权限 → 用 `/COPY:DAT`
- `enabledelayedexpansion` 如果不使用 `!var!` 就别开——会吞掉路径中的 `!`
