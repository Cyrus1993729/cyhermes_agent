# 升级前只读预检：三层 manifest 一致性（2026-10-22 实案，Dayflow 类别 API 升级）

场景：A2A peer / 协调端说「要发增量包，你先做只读预检：报 release 路径、manifest SHA256、manifest files 数量、同步任务状态、有无锁、技能文件位置，并说明 manifest 与某补丁（device-compat-v1）是否一致」。
禁止项写死在任务书里：不安装、不停同步、不重启、不改 Hermes/A2A/模型配置、不回密钥/cookie/凭据/业务正文。

## 最容易被答错的一点：manifest 有三层

| 层 | 路径 | 语义 |
|:--|:--|:--|
| 根 | `<AppHome>/manifest.json` | 安装基线。**打补丁后通常没人回写它，会落后** |
| release | `<AppHome>/releases/<bundle>/manifest.json` | **运行态真相**（校验它对不对，才算「补丁落没落地」） |
| 补丁包 | `<AppHome>/patches/<patch>/extracted/manifest.json` | 补丁后的期望态；同级 `patch.json` 有 `old/newManifestSHA256` 与 changes 列表 |

本次实测：

- 根 `9263a4f9…8376`（51 files，siteVersion 29）= `patch.json.oldManifestSHA256`
- release `bf934819…59de`（52 files，siteVersion 30）= `patch.json.newManifestSHA256`，逐文件 **52/52 校验通过**
- 拿补丁 manifest 去校验**根目录** → 1 mismatch（`runtime/scripts/work-runner.mjs`）+ 1 missing（`runtime/lib/device-authorization.ts`）

判读：release 全通过 + 根 == oldManifest ⇒ 补丁已落地、根基线登记簿没回写。**不是损坏、不是篡改。**
对外若说成「manifest 不一致/可能被改」，对方会按被篡改处理并回滚 = 真事故。

**任何增量包都必须带「根 manifest 回写对齐」一步**，否则每打一次补丁就留一个错基线，下次预检再误判一次。

## 「实际在跑哪个 release」只看计划任务 Action

```powershell
(Get-ScheduledTask -TaskName '<任务名>').Actions | Format-List Execute,Arguments,WorkingDirectory
```

本次 Action = wscript → run-node-hidden.vbs → node.exe home-task.mjs `<AppHome>\releases\sites29-afdf902-home1`。
凭目录名、mtime 或「releases/ 下只有一项」推断都不可靠——升级后新旧 release 会并存。

## 同步锁是「每轮瞬时锁」，不是持久锁

- `<release>/runtime/.local/work-sync.lock` 内容 `{pid, at, token}`，任务跑完即删。
- 同一 1 分钟周期内两次采样即可判活：本次 08:41 有、08:42:21 无 ⇒ 正常释放。
- 单次 `ls` 看不到 ≠ 没在跑；看到残留 ≠ 卡死。判活看 `work-automation-status.json` 的 `finishedAt` 是否推进。
- `token` 字段**不得**转录进对话 / A2A 回执。
- 别和 DWS 自身锁混谈：`dws-config/.data.lock`、`dws-config/audit/.audit.lock`、`tools/dws/.dws-runtime.lock`。

## 计划任务健康判读（PowerShell 优于 schtasks）

```powershell
Get-ScheduledTask | ?{$_.TaskName -match '<关键字>'} | %{ $i=$_|Get-ScheduledTaskInfo; '{0} | {1} | {2} | {3} | {4}' -f $_.TaskName,$_.State,$i.LastRunTime,$i.NextRunTime,$i.LastTaskResult }
```

- `LastTaskResult=267009`(0x41301) = **正在运行**，不是错误码（1 分钟周期的任务很容易抓到）。
- 无失败码 + `NextRunTime` 前进 ⇒ 正常。
- `.local/work-automation-status.json` 正常一轮 = `commands:[]` + `error:null`，起止差数秒~数十秒（UTC ISO）。

## 技能文件位置别猜（要报三处）

- 包内模板 `<AppHome>/deployment/<app>-skill.md` 恒为原始版本（本次 2357 B，sha `2d80c9d6…`）；
- `<AppHome>/skills/` 可能是**空目录**；
- 真正生效的是 `…/hermes/skills/<category>/<skill>/SKILL.md`（本次 11048 B，mtime 更新）。

## 评估「新需求差距」要落到函数级

本次要求「默认四类可改删 / 至少留一个 / 被事项计划复盘历史引用时拒删」，对照 `runtime/lib/categories.ts`（3164 B 源码直跑，无构建产物）：

- `defaultCategories` 是硬编码常量，`categoriesFor()` 恒返回 `[...default, ...custom]` ⇒ 默认四类改不了删不了；
- 只有 `createCategory()`，全库无 update/delete 类别函数；
- `validateCategoryReferences(state)` 已存在，可直接挂「被引用拒删」；
- 现成约束：颜色 6 种、图标 8 种、名称 1–20 字、≤32 个自定义、id 必须 `custom_<uuid>`。

⇒ 汇报给「要碰哪些函数 + 有什么可复用」，比笼统说「需要改造」有用得多。

## 只读边界落地（本次验证可行）

- 自写校验脚本放 `%LOCALAPPDATA%/Temp/`；回执写 `…/hermes/state/a2a/<date>_<topic>.md`。**一个字节都不写进 AppHome。**
- 不 `schtasks /end`、不动 `.local/` 里的锁、不联网（云端接口状态只能标「历史记录，非本次实测」）。
- 回执可带：路径、sha256、文件数、任务状态、锁的存活结论；不可带：token / cookie / DWS 凭据、邮件与日程正文；`.local/` 里 `hd4-*.json` 之类业务 JSON 只报文件名不读内容。
- 收尾给「增量包到位后的建议顺序」：备份 release + 根 manifest → 停任务 → 落文件 → 回写根 manifest 两层对齐 → 逐文件 sha256 → 只读回读 → 启任务。不要把停任务做在预检阶段。
