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

---

# ai-models69-v1（2026-11-04，技能追加型小补丁）

和 fix66 是同一套 driver，但补丁形状不同，值得对着看：

- zip 只有 6 个文件（9079 字节）：`apply.mjs` `patch.json` `skill-append.md` `upgrade.ps1` +
  `runtime/scripts/hermes-client.mjs`、`hermes-request.mjs`。**只换 2 个文件 + 追加 1 段技能**，不碰 `runtime/lib/`。
- `patch.json` 与 fix66 不同：没有 `newManifestSHA256`，只有 `oldManifestSHA256`、`marker`、`homeId`、`bundleId`、
  `changes[]`（`before`/`after` 都是实哈希，没有 `before:null`）——新 manifest 哈希由 apply 自己算出来回传。
- `apply.mjs` 新增两处判断：manifest 已含 marker 就 `alreadyApplied` 退出（可重复执行）；调用前用
  `powershell.exe -Command` 检查任务 `Enabled`/`Running`，**未暂停就直接 throw**（所以必须先过 `upgrade.ps1`）。
- 技能段是**追加型**：`fs.writeFileSync(skill+'.ai69-tmp', oldSkill + '\n' + section)` + rename，
  再断言 `startsWith(oldSkill)`。所以核验是「前缀零改动 + marker 恰好 1 次」，不是开/闭成对。

实测核对值（同一 release `sites29-afdf902-home1`）：

| 项 | 值 |
|---|---|
| 安装前 manifest | `d06c902d…f049`（= patch.json `oldManifestSHA256`） |
| 安装后 manifest | `1772c065…a5c6`（apply 回传，非对端预先给定） |
| files[] | 55 条，missing 0 / mismatch 0；`verifyManifest()` 独立复核 OK |
| hermes-client.mjs | `b5bf5e81…369ec4` |
| hermes-request.mjs | `2e8d9244…656c6310` |
| SKILL.md | 21843 → 24268 字节（+1097），前缀 preserved，marker ×1，`name: dayflow-personal-planner` 保留 |
| 任务 | State=Ready、Enabled=true、导出 XML 与备份 `task.xml` 逐字节同（各 2233 字符） |
| 私有文件 | 7 项前后哈希一致（mtime 都早于安装时刻） |

执行细节：`pwsh7 -File <patch>/upgrade.ps1 -ReleasePath "C:/…/releases/sites29-afdf902-home1"`，
terminal `timeout=300`，实测数秒完成（无在途锁时不会真等 120s）。收到 `installed:true` 后立刻：
`tail -c 1200 <backupDirectory>/install.log` 取 apply 那行 JSON，再用 python 循环 + `verifyManifest` 双重核验 55 文件。

两个备份目录别搞混：`runtime/.local/ai-models69-upgrade-<ms>/`（task.xml、install.log、receipt.json）
和 `runtime/.local/ai-models69-backup-<ms>/`（旧 manifest、旧两脚本、旧 SKILL.md，回退用）。

---

# ai-models69-reader-v1（2026-11-04，第三种形状：改读取器 + 新增 schema，不碰技能）

同一套 `upgrade.ps1` driver，但补丁形状与上两次都不同，值得单独记：

- zip 24271 字节 / 9 个文件（4 个 `runtime/lib/` 模块 + `apply.mjs` + `upgrade.ps1` + `check-reader.mjs` +
  `reader-fixture.json` + `patch.json`）。**不含 skill-append**，`patch.json` 只有 `oldManifestSHA256`、
  `marker`、`homeId`、`bundleId`、`changes[]`（3 条实哈希 + 1 条 `before:null` 新增）。
- `apply.mjs` 的新动作：每个改动文件写完 `node --check`（node24 默认类型擦除，`.ts` 也能 check）；
  改完 manifest 后调 `check-reader.mjs` 做**纯内存虚构恢复演练**（`isolatedBackupDrill(fixture)`），
  结果作为 `readerDrill` 字段嵌在 apply 的 JSON 里回传；失败进 catch → 拷回 backup、删掉 `before:null` 的新文件、
  还原 manifest，再 rethrow。
- `check-reader.mjs` 只读 `reader-fixture.json`（虚构 1 条事项、日期 2099-01-02、`requiredFeatures` 含
  `ai-models-v1`、`coach` 3 条模型记录），断言 `status==='complete'` 与 `nonemptyRestore===true`；
  回执里必看 `realModelCalls:0` / `productionWrites:0`——这是「没碰真实数据和模型」的证据。

实测核对值（同一 release `sites29-afdf902-home1`）：

| 项 | 值 |
|---|---|
| 安装前 manifest | `1772c065…a5c6`，55 条（= 上轮 ai-models69 装完的产物，也是对端给的基线） |
| 安装后 manifest | `b89e81e6…97bd`，56 条，missing 0 / mismatch 0 |
| backup.ts / coach-records.ts / persistence.ts | `1e793552…0900` / `e90da7a8…181f` / `17e36616…8e35` |
| ai-model-schema.ts（新增 1528B） | `779a2d73…be86` |
| manifest 顶层 | 16 个旧键全在 + 新增 `aiModels69ReaderSourceCommit`；`patches` 追加 `DAYFLOW-AI-MODELS69-READER-20261104`，旧 CLI marker `DAYFLOW-AI-MODELS69-20261104` 与其 sourceCommit 未动 |
| 任务 | 装后 Enabled=true；`enabledRestored`/`taskDefinitionUnchanged`/`privateConfigurationsUnchanged` 均 true（私有 7 项） |
| readerDrill | `complete` / `isolated:true` / `nonemptyRestore:true` / `items:1` / `modelRecords:3` / 写 0 调用 0 |

执行命令（一次调用、`timeout=600` 更稳）：

```bash
"<root>/tools/pwsh7/pwsh.exe" -NoLogo -NoProfile -NonInteractive \
  -File "<root>/patches/ai-models69-reader-v1/extract/upgrade.ps1" \
  -ReleasePath "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1"
```

坑与习惯：

- **PATH 里没有 pwsh**：`which pwsh` 空、`ls "/c/Program Files/PowerShell"` 也不存在（本机没装系统级 PS7），
  自带的那份在 `<root>/tools/pwsh7/pwsh.exe`（7.6.7）。`find /c -maxdepth 5 -name pwsh.exe` 全空是深度不够，
  别据此判断「没 PowerShell 7，跑不了」。
- **回执只要两段原文**：upgrade 末尾 receipt JSON + `<backupDirectory>/install.log` 末尾的 apply JSON（含
  `readerDrill`），再加 2–3 行 56 文件核验；对端明说「不要长篇验收」就别输出日志正文与整份清单。
- **备份目录两套命名**：`ai-models69-reader-upgrade-<ms>/`（task.xml、install.log、receipt.json）与
  `ai-models69-reader-backup-<ms>/`（旧 manifest、旧 3 模块、回退用）；后者路径在 apply JSON 的 `backupDirectory`。
- 核验用 python 一次算完 56 条哈希 + 打印 manifest 键数与 `patches` 尾部，比逐个 `sha256sum` 快且能一眼看出
  「旧字段是否被删」。

---

# ai-models69-wrapper-v1（2026-11-04，第四种形状：只换一个包装文件）

最简的一种：zip 5288 字节 / 4 个文件（`apply.mjs` `patch.json` `upgrade.ps1` +
`runtime/scripts/hermes-local.mjs`），`changes[]` **只有 1 条且无 `before:null`**，不含技能追加、
不含新文件。对端明确要求「两个已装 CLI 文件和读取器都不要重装，只更新这一个原有包装文件」。

- `apply.mjs` 的 `allowed` 白名单就 1 条，并加了三重形状断言：`changes.length===1`、
  path 去重后仍 1 条、且全在 `allowed` 内 → 否则 `Patch scope mismatch`。
- manifest 变更只有两处：`patches` 末尾追加 `DAYFLOW-AI-MODELS69-WRAPPER-20261104`，
  顶层新增 `aiModels69WrapperSourceCommit`；旧 CLI/READER marker 与两个 sourceCommit **逐字保留**。
- 语义修复内容（供识别同类包装器 bug）：`hermes-local.mjs` 里「哪些子命令读 stdin」的名单
  原本把 `models` / `models-catalog` / `models-test-status` 也算作写命令，交互终端里会挂住等输入；
  修法＝把这 3 个加进**免读 stdin 名单**（`state/items/due/categories/category-delete` 同类），
  写命令仍走 `fs.readFileSync(0)`。用「保持 stdin 打开的 5 种实际子进程用例」验证是关键——
  单跑 `node --check` 证明不了这个。

实测核对值（同一 release `sites29-afdf902-home1`）：

| 项 | 值 |
|---|---|
| 包 | 5288 字节 / `bf500c22…97d33` / 4 文件 |
| 安装前 manifest | `b89e81e6…97bd`，56 条（= 上轮 reader 装完的产物） |
| 安装后 manifest | `54c067fc…b014`，仍 56 条，missing 0 / mismatch 0 |
| wrapper | `c36b3610…9384`(1780B) → `41924713…e8420`(1957B) |
| diff vs 升级备份清单 | 仅 `CHANGED runtime/scripts/hermes-local.mjs 1780->1957`，其余 55 条 path+bytes+sha256 零差异 |
| manifest 顶层 | 旧键全在，新增仅 `aiModels69WrapperSourceCommit`；`patches` 三段 marker |
| 任务 | 装后 Enabled=true / State=Running / LastResult=267009 / NextRun 正常续 |
| receipt | installed/originalEnabled/enabledRestored/taskDefinitionUnchanged/privateConfigurationsUnchanged(=7 项) 全 true |

坑与习惯：

- **预检时锁存在不要停**：本次 20:31:20 `Test-Path` 为 true，20:31:24 已消失（那轮自己收尾）。
  driver disable 后轮询 120s，锁只是短命文件。
- **driver 超时给 180s 够用**（内含 120s 等锁上限 + 秒级安装）；对端明说「单次时限 180 秒」时就不要
  照旧习固定 300s；超时就回报、不重跑。
- **单文件补丁的「未动其它文件」证据只能靠备份清单 diff**，receipt 只给布尔。别用 `find -type f` 计数
  （release 里还有 `.local/` 的备份目录，数字会离谱）。
- 装完额外查一件事：`find <release> -name "*.ai*-tmp"` 应为 0（原子写残留检查）。
- 回执形状（对端点名要的）：upgrade receipt JSON + `install.log` 里的 apply JSON + 「N 文件哈希自检」
  三行 + 任务已恢复（含 `267009` 的中文解释），最后一句声明「未调云端路由、未做模型请求、未发 Telegram」。

