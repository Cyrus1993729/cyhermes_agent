# 备份读取器兼容性核验（实测记录）

场景：A2A 对端要求「只核验现有最近每日备份能否被已更新的读取器读取」，
明确禁止：创建/恢复正式数据、改配置/调度、发 Telegram、回传正文。

## 对端给的那种一行命令为什么跑不通

对端下发的是这种形状（PowerShell，`-e` 里塞 ES module）：

```powershell
& $n --input-type=module -e 'import fs from "node:fs"; const{validateBackup}=await import(...); ...' $lib $backup
```

在 Windows PowerShell 下必崩，两层原因：

1. **内部双引号被剥**：PowerShell 解析 `-e` 参数时吃掉 JS 里的 `"`，`from "node:fs"` 变成 `from node:fs`，
   node 报 `SyntaxError: Unexpected identifier 'node'`（位置指向 `C:/Users/.../[eval1]:1`）。
2. **报错信息被截断**：脚本里若有 `$ErrorActionPreference='Stop'` 且 `& cmd 2>&1`，stderr 会变成 ErrorRecord
   直接抛，`$_.Exception.Message` 只留第一行 → 只看到 `file:///C:/.../[eval1]:1`，看不到真正的 SyntaxError。

把 stderr 落文件后，真实报错是：

```
import fs from node:fs;import{pathToFileURL}fromnode:url;...
               ^^^^
SyntaxError: Unexpected identifier 'node'
```

## 可用做法（已验证）

JS 落成 `.mjs` 文件，路径当 argv 传，一次 `terminal` 调 `powershell -File` 即可满足「单个终端调用」要求：

- runner: `scripts/verify-backup-readable.mjs`（本 skill 自带）
- 参数：`node <runner> <runtime/lib/backup.ts> <backup.json>`（脚本文件模式下 `argv[2]`、`argv[3]`；
  若留在 `-e` 模式则是 `argv[1]`、`argv[2]`）
- 临时文件落 `$LOCALAPPDATA/Temp`，原生程序才认得到该路径

PowerShell 包装骨架（单次调用、全程只读）：

```powershell
$ErrorActionPreference = 'Continue'
$r   = '<deploy-root>/releases/<active-release>'
$n   = '<deploy-root>/tools/node24/node.exe'
$dir = $r + '/runtime/.local/automatic-backups'
$lib = $r + '/runtime/lib/backup.ts'
$b = Get-ChildItem -LiteralPath $dir -File -Filter 'dayflow-*.json' |
     Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $n $runner $lib $b.FullName 1> $out.txt 2> $err.txt
$code = $LASTEXITCODE
Get-Content -LiteralPath $out.txt -Raw
if ($code -ne 0) { Get-Content -LiteralPath $err.txt -Raw }
```

对每条可能缺失的路径先 `Test-Path` 并原样报出，不自行改目录、不补跑备份（对端明确禁止）。

## 回执形状（实测通过）

```json
{"valid":true,"backupVersion":5,"exportedAt":"<iso>","requiredFeatures":[],"items":37,"goals":2,"reviews":1,"newReaderUsed":true,"noRestore":true}
```

附元数据：`backupCount`（候选份数）、`latestFile`、`lastWriteUtc`、`sizeBytes`。
不给条目正文、不给邮件/复盘原文、不给密钥；`requiredFeatures: []` = 无特性门槛，不是缺失。

## 附加判据

- 读取器与格式模块同目录（例：`backup.ts` / `backup-format.ts` / `backup-parts.ts`）时，
  只需 import 主模块，别自己去解析格式。
- 若对端说「上条 lastBackup=null 只是日志窗口里没有事件，不需要补跑」，
  就**只做兼容性核验**，不要顺手去看日志区间或触发补跑。
- 文件名/mtime 可报（对端需要对齐是读的哪一份），但正文、哈希盐、密钥一律不给。
