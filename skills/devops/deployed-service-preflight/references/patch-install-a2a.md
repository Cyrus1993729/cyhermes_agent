# 补丁安装实测流程（DayflowHome category-fix66-v1，2026-10-22）

场景：A2A 对端（妈妈端 PC-A）下发升级 zip，要求只更新家中读取器/客户端，不写正式数据、不重启、
不改 Hermes 配置。活动 release：`releases/sites29-afdf902-home1`。

## 1. 验包（不解压）

```powershell
# C:/Users/Administrator/AppData/Local/Temp/dl_fix66.ps1 —— 写 .ps1 用 -File 跑，不用 -Command
$url = 'http://<peer-ip>:61234/<token>/Dayflow-Home-Fix66-v1.zip'
Invoke-WebRequest -Uri $url -OutFile $out -NoProxy -TimeoutSec 150 -UseBasicParsing
"bytes="  + (Get-Item $out).Length
"sha256=" + (Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
```

```bash
"<root>/tools/pwsh7/pwsh.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "C:/.../Temp/dl_fix66.ps1"
```

实测：71068 字节 / `6577cc24…93fd`，与对端口述逐字节一致才继续。

## 2. 解到独立目录

`Expand-Archive -DestinationPath <root>/patches/category-fix66-v1`；目录已存在则先报 `already_exists` 退出（`exit 3`），
不要 `-Force` 覆盖既有 patch。解出 21 个文件：`apply.mjs` `manifest.json` `patch.json` `skill-append.md`
`upgrade.ps1` + `deployment/` 2 个 + `runtime/lib/` 9 个 + `runtime/scripts/` 7 个。

## 3. 执行前读三件套

- `patch.json`：`oldManifestSHA256` / `newManifestSHA256` / `sourceCommit` / `changes[]`（path + before + after）。
  fix66：18 条 changes，其中 `before:null` 的 3 条 = 对端说的「三个新增运行时文件」
  （`runtime/lib/category-id.ts`、`runtime/scripts/hermes-arguments.mjs`、`runtime/scripts/hermes-request.mjs`）。
- `upgrade.ps1`（44 行）：`Export-ScheduledTask` 存 `task.xml` → 哈希 7 个私有配置 → `Disable-ScheduledTask` →
  轮询 `State -eq 'Running'` 或 `work-sync.lock`，120s 上限后 `throw`（不 kill、不删锁）→ 调 apply.mjs →
  校验新 manifest + 私有配置未变 → `finally` 复原 Enabled 并写 `receipt.json` + 打印压缩 JSON。
- `apply.mjs`（28 行）：校验 homeId/bundleId → 幂等（已是新 manifest 就 `alreadyApplied` 退出）→ 白名单 18 路径 →
  逐条比 before/after → 备份到 `runtime/.local/fix66-backup-<ms>` → 原子写（`.category-tmp` + rename）→
  verifyManifest → 追加技能段 → 内存冒烟（类别删除保护/历史引用备份）→ catch 里回滚。**无网络调用。**

## 4. 执行

```bash
export LOCALAPPDATA="${LOCALAPPDATA:-C:\Users\Administrator\AppData\Local}"; export USERPROFILE="${USERPROFILE:-C:\Users\Administrator}"
"<root>/tools/pwsh7/pwsh.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass \
  -File "<root>/patches/category-fix66-v1/upgrade.ps1" \
  -ReleasePath "<root>/releases/sites29-afdf902-home1"     # terminal timeout=300
```

实测耗时 <60s（在途那轮自己先结束）。输出单行 JSON（脱敏）：

```json
{"backupDirectory":"…/runtime/.local/fix66-upgrade-1792652050537","enabledRestored":true,"noCloudWrites":true,
 "at":"2026-10-22T06:54:46Z","privateConfigurationsUnchanged":true,"originalEnabled":true,"noReboot":true,
 "privateFilesCompared":7,"installed":true,"taskDefinitionUnchanged":true}
```

## 5. 装后核验（三项 + 可选）

```bash
sha256sum <release>/manifest.json                       # == 对端给的新哈希
"<root>/tools/node24/node.exe" scripts/verify-release-manifest.mjs   # {ok, bundleId, files:55, verified}
tail -3 <release>/runtime/.local/fix66-upgrade-*/install.log         # apply 的 patched/files/sourceCommit
grep -n "DAYFLOW-CATEGORY-FIX66-" <hermes>/skills/productivity/dayflow-personal-planner/SKILL.md  # 开/闭成对
schtasks /query /tn Dayflow-Work-Sync | iconv -f GBK -t UTF-8        # 已恢复、自然周期在跑
```

实测：新 manifest `776f82e9…5138` ✓、`files=55` ✓、标记在第 181/192 行成对 ✓、任务 14:55:58 起自然运行。

## 6. 回报与红线

- 只报脱敏 JSON + 三条核验；私有配置只给「7 个文件、未变」布尔，不给哈希/内容/凭据；复盘与邮箱正文一律不提。
- 主动交代「Enabled 复原后分钟级任务自己跑起来了，后续有它自身的常规云端同步，不是我发起的写入」。
- 对端说「先不做长验收」就真的不做，等它发布后再做客户端与自然调度验收。
