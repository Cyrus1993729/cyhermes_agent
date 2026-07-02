# Windows .bat 脚本编写规范

> 来源：2026-06-21 升级脚本 5 轮迭代 + Claude 双审

## 铁律
1. 纯英文 + chcp 65001（中文 GBK 乱码→被当命令执行）
2. Get-Process 无 CommandLine → 用 Get-CimInstance Win32_Process
3. %date% 中文含空格 → 用 for /f 提取安全日期
4. xcopy 不可靠 → 用 robocopy /E /COPY:DAT
5. start 嵌套引号导致静默失败 → 变量直接展开
6. 损坏 git 仓库 → rm .git + git fetch --depth 1
7. enabledelayedexpansion 未使用时移除（! 字符风险）
8. 关键错误不禁用 2>nul
