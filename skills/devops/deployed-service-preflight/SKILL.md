---
name: deployed-service-preflight
description: "只读预检/脱敏回执：打补丁升级在跑服务，或只核验现有备份能否被新读取器读时用。"
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [preflight, readonly, scheduled-task, manifest, desensitized, ops]
---

# 在跑服务的只读预检与脱敏汇报

适用：对一个**正在提供服务**的本机部署（Dayflow 家主机、TrendRadar、任何带定时任务的常驻服务）做
"打补丁前/后核对"。典型请求来自用户本人或 A2A 对端，措辞类似「核对活动目录/哈希/任务状态/在途锁，
只读，不暂停调度、不重启」。

## 铁律

1. **只读**：不改配置/数据、不停任务、不删锁、不重启。要写就先把发现汇报回去等授权。
2. **每条结论都来自真实命令输出**，不凭上一次预检的记忆填报。
3. **对端/群里只给脱敏结果**：版本号、计数、哈希、状态枚举、进程存活判断。
   **不给** URL、key/token、业务正文、配置正文。
4. 临时把某目录前置进 `PATH` 或给单次调用加 timeout 都**不需要**改全局 config.yaml。

## 预检六项（按序，能并行就并行）

| # | 核对项 | 怎么判 |
|---|---|---|
| 1 | 活动版本目录 | 列出 releases/，确认只有/只有一套在跑；别把根目录那份旧清单当活动清单 |
| 2 | 内容完整性 | 官方自带的 verify 子命令优先（`<node> <entry>.mjs verify`），不要手工逐个比哈希 |
| 3 | 定时任务 | `Enabled` / `State` / `LastResult` / `NextRun`；`LastResult` 要会翻译（Windows `267009`=实例在跑，不是失败） |
| 4 | 在途锁 | 锁文件里一般带 pid：读 pid → 判进程存活；**不删锁不停进程**；检查期间锁消失=那轮已正常收尾 |
| 5 | 最近一轮结果 | 服务自写的 status/observation 日志取末几条，比翻大日志快 |
| 6 | 远端状态版本 | 调一次只读 GET（state/status），只取 revision 与各类计数 + 最近成功时间 |

Windows 具体命令、Dayflow 家主机实测基准值、pwsh PATH 坑：见 `references/dayflow-home-preflight-ops.md`。

## Windows/MSYS 通用坑（会让预检本身出错）

- **`schtasks /query` 中文系统下 GBK 乱码**，`/FI "PID eq 123"` 还会被 bash 吃引号报
  `无效参数/选项 - 'eq'`。统一用 PowerShell `Get-ScheduledTask` + `Get-ScheduledTaskInfo`，
  只拼要的字段输出。
- **`icacls` 别经 `cmd /c`**：反斜杠+括号被 MSYS 吃掉，报「文件名、目录名或卷标语法不正确」
  （还会打印骗人的「成功 0 个」）。写 `.ps1` 用 `powershell -NoProfile -ExecutionPolicy Bypass -File` 跑，
  末尾 `Get-Acl` 回显当验证。
- **原生 CLI 内部 `spawn('pwsh')` / `spawn('node')` 走 PATH**：报 `PowerShell 7 is required`
  是 PATH 缺 pwsh，不是客户端坏。本次调用 `env['PATH'] = pwsh_dir + ';' + env['PATH']` 即可。
- **二进制位置常在部署根而不是 release 里**（如 `tools/node24/node.exe`）；在 release 目录写
  `./tools/...` 会 `No such file`。先 `find <root> -maxdepth 3 -name node.exe`。
- 服务自带单请求硬超时很常见（30–35s）；Hermes `terminal` 的 `timeout` 单次可给 100–300s，
  前台上限 600s，更长用 `background=true`。
- **对端给的 `node -e '...'` 单行校验命令在 PowerShell 下会塌**：PowerShell 解析 `-e` 时剥掉 JS 内部双引号，
  `from "node:fs"` 变成 `from node:fs`，报 `SyntaxError: Unexpected identifier 'node'`。
  别硬改写那一行，把 JS 落成 `.mjs` runner 传路径（已固化：`scripts/verify-backup-readable.mjs`）。
- **原生命令 stderr 被 `ErrorActionPreference='Stop'` 吞成一行**（只剩 `file:///...[eval1]:1`，
  真正的 SyntaxError 丢了）：原生调用期间用 `'Continue'`，加 `1> out.txt 2> err.txt` 重定向再 `Get-Content -Raw`。

## 备份 / 读取器兼容性核验（只读）

触发：对端说「只核验现有备份能不能被**更新后的读取器**读，不创建/恢复正式数据、不改配置/调度、不发 Telegram」。
这类任务不是「核对已知清单」，而是**证明兼容性**，所以：

1. 只取**最新一份**备份（`Sort-Object LastWriteTime -Descending | Select-Object -First 1`），读它、绝不写它；
   顺带报候选份数，避免「最新那份其实不是每日备份」的误判。
2. 调用前先确认导出名还在：`typeof m.validateBackup === 'function'`，不是就报「读取器导出变了」，不要让它崩在栈里。
3. 回执只给字段名与计数：`valid / backupVersion / exportedAt / requiredFeatures / items / goals / reviews /
   newReaderUsed / noRestore`，加元数据（文件名、mtime、候选份数）。**不给条目正文**、不给邮件/复盘原文、不给密钥。
4. `requiredFeatures: []` 是「无特性门槛」，不是缺失——别写成异常。
5. 结论里显式声明「未做 restore、未改配置/调度、未发 Telegram」，对端才认这条账。
6. 路径不存在：只报错（原话：不自行改造目录、不补跑备份）。

现成脚本 `scripts/verify-backup-readable.mjs`：`node <runner> <runtime/lib/backup.ts> <backup.json>`。
node ≥23 默认开类型擦除，`.ts` 可直接 `import()`，不需要额外 flag。
踩坑原文与 PowerShell 包装见 `references/backup-reader-verify.md`。

## 交付形状

1. 一段 JSON（分块：release / task / lock / sync / remote state / snapshot 路径），哈希只给前 8–12 位或全量但**不带正文**。
2. 3–6 行结论：哪些对上了、哪些是正常现象（例如旧清单哈希不同、`LastResult` 是在跑）。
3. 附一句操作痕迹：「未发消息、未做正式写入、仅 N 次只读 GET」。
4. 预检发现的**供补丁设计参考的事实**（如客户端单请求 35s 上限、总预算 70s 正好两次）单独列，不说成故障。

## 安装前对照快照

补丁前把「补丁后要能证明没被动过」的东西落盘到本机私有目录（不带正文、不发对端）：

- `SHA256SUMS.txt`：`config.yaml`、其中 `a2a_agents` / `model` 等关键块的**抽取后哈希**（抽出来算哈希，不落正文）、
  服务私有连接/主机/启用/切换配置文件、相关 skill 的 `SKILL.md`
- 受管文件原文备份（例如 skill 原文 `.orig`），补丁后好 diff
- 目录权限收口到本账户（见上 icacls 坑）

---

## 补丁安装（对端下发升级包，本技能的下半场）

触发：A2A 对端或用户给一个 zip + SHA256 + 字节数 + 新 manifest 哈希 + 期望文件数，要求「按这个范围安装」。
完整实测流程与字段见 `references/patch-install-a2a.md`；装完的核验探针可直接跑 `scripts/verify-release-manifest.mjs`。

1. **先验包，再解包。** 下载后立刻比字节数与 SHA256，任一不符就停，不解压不安装。内网下载绕代理：
   `Invoke-WebRequest -NoProxy`（只对这一条命令，不动全局代理配置）。
2. **解到独立新目录** `patches/<patchId>/`。绝不覆盖既有 patch 目录或 old release；目标目录已存在就先问/换名。
3. **读 `patch.json` + `upgrade.ps1` + `apply.mjs` 再执行**（三者都小，读得起）。至少确认：
   - `changes[]` 的 `before` 哈希 == 活动 release 现文件哈希；`before:null` 的条数 == 对端口述的「新增文件数」；
   - 安装器里的 `allowed` 白名单 == `changes` 路径集（白名单多出路径就是不守范围）；
   - 只有 disable → 轮询等在途自然结束 → apply → `finally` 复原 `Enabled`；**没有**网络请求、重启、kill、删锁；
   - 失败路径有回退（拷回 backup、删掉新增文件）。
4. **一条终端调用跑完 driver**，别拆成多步（中途超时更麻烦）：
   `<root>/tools/pwsh7/pwsh.exe -NoProfile -ExecutionPolicy Bypass -File <patch>/upgrade.ps1 -ReleasePath "<活动 release>"`，
   `timeout` 给 300s（等待在途上限 120s + 安装）。先 `export LOCALAPPDATA=... USERPROFILE=...`，
   否则脚本里 `$env:LOCALAPPDATA` 为空，报 `Unexpected release path`。
5. **失败只回报，不重跑。** 脚本超时/报错时回报错误 + 任务是否已复原 Enabled，不自行强装、不第二次执行。
6. **装完三项核验**：新 `manifest.json` SHA256 == 对端给的值；`verifyManifest` 文件数 == 期望数（缺失/不匹配 0）；
   技能标记注释**成对出现**（grep 开/闭两条，不是重复追加）。
7. **回报形状**：upgrade 的脱敏 receipt JSON（`installed` / `originalEnabled` / `enabledRestored` /
   `taskDefinitionUnchanged` / `privateConfigurationsUnchanged` / `noReboot` / `noCloudWrites`）+ apply 的
   `patched` / `files` / `sourceCommit` + 上面三条核验结论。原文摘录，不要转述成「都成功了」。

### 安装类任务的坑

- **复原 `Enabled` 后分钟级任务会立刻自然跑起来**，可能产生它自己的云端同步。必须主动声明「这是它自身的常规同步，不是我发起的写入」，
  否则对端会以为你违反了「不做云端写入」。
- **对端常明确说「先不做整套长验收」**——那就只给要求的三项，不要顺手跑全套用例把回执淹掉。
- 私有配置改动只能报**布尔**（`privateConfigUnchanged: true`）与文件数，不能报哈希列表、路径内容、凭据。
