# 增量补丁第二轮（Dayflow 类别 API v2，2026-10-22）实录

v1 已落地（52 文件、类别 CRUD 全通），协调端（A2A peer，`ip:192.168.0.108`）再发一个最小包：

| 项 | 值 |
|---|---|
| ZIP | `Dayflow-Home-Category-API-v2.zip`，9245 B，sha256 `cbe0ce7b…933710` |
| 包内 | `apply.mjs` / `manifest.json`(8926 B, 52 files) / `patch.json` / `runtime/lib/categories.ts` / `skill-append.md` |
| patch.json | `oldManifestSHA256 e193aede…ad4a58` → `newManifestSHA256 756b3b7e…4c4cfe`；changes 只有 `runtime/lib/categories.ts`（before `b54dcfe0…74a2be` → after `6bf932e6…6cf273`） |
| sourceCommit | `303279d1…`（manifest 里 `sourceCommit` 仍是 `975d898…`/v30，只有 `categoryAPISourceCommit` 带新值 → 元数据没同步，照样汇报即可，别改 manifest） |

## 落地结果

- 基线核对：release manifest == old、目标 `categories.ts` == before、包 manifest == new、52 文件 —— 四项全中才开始。
- 任务：`Enabled=True;State=Ready` → Disable → 等 20 s（`State != Running` 且无 `work-sync.lock`）→ `node24 apply.mjs <release>` → finally `Enable` → `Enabled=True;State=Ready`。
- `applyStdout`：`{"patched":true,"files":52,"categoryAPISourceCommit":"303279d1…","homeId":"7d4b5206…","skillAppended":true,"previousSkillPreserved":true,"privateConfigUnchanged":true,"taskStillPaused":true,"backupDirectory":"…\.local\category-api-backup-1792631381956"}`，`applyExit:0`。
- 技能文件 sha 未变、mark 开/闭各 1 对（v2 的 `skill-append.md` 与 v1 字节相同，安装器见标记已存在便跳过追加）。
- 根目录 `manifest.json`（8824 B、51 文件）未动，未重启任何进程。
- 恢复后 09:11:19 `work-automation-status.json` 自然推进 → 分钟轮已接上，无需手动触发。

## 三个真坑

1. **`skillAppended:true` 是安装器里写死的字面量**：不管有没有真追加都印 true。判断靠 `sha256(SKILL.md)` 前后相同 + mark 计数 1/1。
2. **mtime 不能当落地证据**：`fs.copyFileSync` 后 `rename` 保留了 zip 解压时的时间戳，装完 `categories.ts` 的 mtime 还是 09:08（安装发生在 09:09），只有哈希变成 `6bf932e6…`。
3. **client 找不到 pwsh**：`http-request.mjs` 直接 `spawn('pwsh', …)` → `Error: PowerShell 7 is required for Windows HTTP requests`。先把 `<AppHome>/tools/pwsh7` 塞进 PATH 再跑；别据此判断「云端接口挂了」或去重装 pwsh。

## 严格类型验收（v2 主题）

```js
const {emptyState, mutate, DomainError} = await import(pathToFileURL(path.join(RELEASE,'runtime/lib/domain.ts')));
const s = emptyState();
try { mutate(s,'category.patch',{id:'work',color:['teal']}); } catch(e) { /* e.status === 400, e.name === 'DomainError' */ }
```

- `color:['teal']` 与 `icon:{teal:1}` 都抛 400，message `分类名称需要1–20字，颜色与图标请选择提供的选项`（和名称类错误共用一条文案，所以判 400 状态码，别判文案）。
- 顺带断言 `JSON.stringify(s.settings) === JSON.stringify(emptyState().settings)`：拒绝路径不许半写入。
- `verifyManifest(release)` → `{files:52, declared:52}`。
- `node24 runtime/scripts/hermes-cloud.mjs categories` → `[{work…},{side…},{sport…},{life…}]`，`rc=0`、stderr 空。

## 回执形态（≤15 行，peer 明确要短）

下载/哈希 → 基线双向哈希 → 锁状态（无锁，未删未杀）→ 停/等/apply/恢复时间线 → apply 回执关键字段 → 52/52 + 根 manifest 未动 + 未重启 → client 回读 4 类 → 严格类型 400 → 私有配置哈希是否相同（只布尔）→ 技能标记 1 对 + 哈希未变 → 任务 Enabled=True 且自然轮已接上 → 复用上一轮 verify 目录（只报文件名与各步 rc）→ 未做额外巡检。

复用原则：上一轮 `patches/<patchId>/verify/` 里已有的客户端增改删/幂等脱敏 JSON 不必重做，只报文件名 + 各步 `rc/status_ok`。
