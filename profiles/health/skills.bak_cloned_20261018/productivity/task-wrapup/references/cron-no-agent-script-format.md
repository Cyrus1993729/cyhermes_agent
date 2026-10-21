# Cron no_agent 脚本格式坑

## 问题

Hermes cronjob 的 `no_agent` 模式通过 Python 执行脚本，不是通过 bash 或 cmd.exe。

## 踩坑记录（2026-07-03 备份 cron 修复）

| 尝试 | 脚本格式 | 结果 | 错误 |
|:---|:---|:---|:---|
| 1 | `.sh` (bash) | ❌ | Windows 路径反斜杠被 bash 当转义符吞掉：`C:UsersAdministrator...` |
| 2 | `.bat` (batch) | ❌ | Python 直接解析批处理语法，非 ASCII 字符（如 emoji）报 SyntaxError |
| 3 | `.py` (Python) | ✅ | 正常运行 |

## 规则

- **no_agent cron 脚本必须用 `.py` 格式**
- 不可用 `.sh`（路径问题）和 `.bat`（语法解析问题）
- 脚本通过 `subprocess.run()` 调用外部命令（如 git），不依赖 shell
- 成功时 `sys.exit(0)` 且不输出任何内容（静默 = 成功）
- 失败时 `print()` 错误信息 + `sys.exit(1)`（cron 自动通过微信通知用户）

## 脚本路径

- 脚本放在 `~/AppData/Local/hermes/scripts/` 下
- cron 的 `script` 参数只需写文件名（如 `backup_git.py`），cron runner 自动查找

## 示例

```python
import subprocess, sys
r = subprocess.run(["git", "push"], capture_output=True, text=True)
if r.returncode != 0:
    print(f"FAILED: {r.stderr}")
    sys.exit(1)
```
