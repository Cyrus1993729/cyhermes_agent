# 增量补丁落地实录 — Dayflow 类别 API v1（2026-10-22，牛来端）

协调端（妈妈机 A2A peer）交付：
- `Dayflow-Home-Category-API-v1.zip`，27775 B，SHA256 `a988879f…5ea82a96`（下载后实测一致）
- 内容 10 个文件：`apply.mjs`、`patch.json`、`manifest.json`(新)、`skill-append.md`、6 个改动文件
- 目标 release：`C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1`
- manifest 基线 `bf934819…3259de`(52) → 补丁后 `e193aede…ad4a58`(52)

## 1. 下载与解压

```bash
curl -sS --noproxy '*' -o pkg.zip "http://<peer>/<token>/x.zip" -w 'http_code=%{http_code} size=%{size_download}\n'
sha256sum pkg.zip                     # 与来件逐字比对
mkdir -p <AppHome>/patches/<patchId>/extracted && unzip -o -q pkg.zip -d <...>/extracted
```

LAN 直连必须 `--noproxy '*'`（本机常驻 HTTP_PROXY=127.0.0.1:10808）。

## 2. 双向哈希 + 范围核对（apply 之前，全部只读）

```python
for c in patch['changes']:
    assert sha(patch_dir/c.path) == c['after']      # 载荷正确
    assert sha(target/c.path)    == c['before']     # 目标正是基线
assert sha(patch_dir/'manifest.json') == patch['newManifestSHA256']
new = {f['path']:f['sha256'] for f in new_manifest['files']}
old = {f['path']:f['sha256'] for f in target_manifest['files']}
changed = [p for p in new if old.get(p) != new[p]]
assert set(changed) == {c['path'] for c in patch['changes']}   # 只有声明的 6 条
```

本次：6 条全部 before/after 双向匹配；52 条中恰 6 条不同；其余 46 条在目标里已匹配新 manifest（载荷未携带、无需改）。

## 3. apply.mjs 的 gate（决定必须先停任务）

```js
if(path.basename(target)!=='sites29-afdf902-home1') throw 'Exact active release path required';
if(identity.homeId!=='7d4b5206-…'||identity.bundleId!==spec.bundleId) throw 'Home identity mismatch';
if(hash(mp)===spec.newManifestSHA256){ verifyManifest(target); exit(0) }        // 已打过 = 幂等退出
if(hash(mp)!==spec.oldManifestSHA256) throw 'Active release manifest does not match expected baseline';
if(fs.existsSync(local+'/work-sync.lock')) throw 'Wait for active sync to finish; do not kill or remove its lock';
// 再用 PowerShell 校验：Settings.Enabled 必须 false 且 State !== 'Running'，否则 throw
const allowed=[6 个白名单路径];                 // 白名单外一律 mismatch
```

装前快照：`schtasks /query /tn Dayflow-Work-Sync /xml > task-<name>.original.xml`、私有 `.local/*.json` 哈希、`pre-state.json`（release manifest sha + files 数 + 私有配置哈希 + 技能 sha）。

## 4. 运行器（一个脚本内 try/finally，勿拆调用）

见 `templates/apply_patch_guarded.mjs`。本次实测时间线：

| 时刻(UTC) | 事件 |
|---|---|
| 00:57:14 | task Enabled=True / State=Running |
| 00:57:26 | 自然结束，lock 消失（等 12 s，未杀进程/未删锁） |
| 00:57:2x | Disable-ScheduledTask → Enabled=False / Disabled |
| 00:57:3x | `node24 apply.mjs <release>` → `{"patched":true,"files":52,"categoryAPISourceCommit":"791e83f…","skillAppended":true,"previousSkillPreserved":true,"privateConfigUnchanged":true,"taskStillPaused":true,"backupDirectory":"…category-api-backup-1792630660682"}` |
| 00:57:55 | finally：Enable-ScheduledTask → Enabled=True / Ready，Action/Arguments 与原始逐字相同 |

判断任务是否空闲用：`[string]$t.State -ne 'Running'` 且 `!Test-Path <release>/runtime/.local/work-sync.lock`。

## 5. 装后八项核对（顺序）

1. `sha256sum <release>/manifest.json` == `newManifestSHA256`
2. `verifyManifest(release)` → files=52（`node --input-type=module -e "import {pathToFileURL}…"` 动态 import `deployment/home.mjs`）
3. 私有配置 6 个 json 哈希与 before 完全一致
4. 技能：`cur.startswith(backup/SKILL.md)` 且 `sha(cur[:len(bk)]) == sha(bk)`，且 marker 只出现 2 次（开/闭注释）
5. 根离线副本 `verifyManifest(AppHome)` → 51 files OK，且**未**把新 manifest 拷到根
6. 任务 Enabled 恢复 True、State=Ready、Action 未被改写
7. 等一次自然分钟轮：`work-automation-observation.jsonl` 末行 `error:null`（本次 00:59:59Z、01:00:59Z 两轮均 null）
8. 业务数据只读计数：`client items` 37 条、`client state` 的 items 37 / goals 2 / reviews 1 / drafts 0

## 6. 类别 API 客户端用法（本轮新增能力）

委派链：`home.mjs client <op>` → `hermes-cloud.mjs` → `hermes-local.mjs` → `hermes-client.mjs`。
`hermes-local.mjs` 解析 `--json-file <abs>` 与 `--request-id <id>`；**GET 类与 `category-delete` 不读 stdin**，其余写操作必须给 JSON（stdin 或 --json-file）。缺 `--request-id` 直接拒（映射到 `Idempotency-Key`）。

```bash
N=<AppHome>/tools/node24/node.exe; R=<release>
"$N" "$R/deployment/home.mjs" client categories                       # 裸数组
"$N" "$R/deployment/home.mjs" client category-create --json-file body.json --request-id rid-1   # 201 直返对象
"$N" "$R/deployment/home.mjs" client category-patch <id> --json-file body.json --request-id rid-2
"$N" "$R/deployment/home.mjs" client category-delete <id> --request-id rid-3
```

实测（默认 4 类 work/side/sport/life，全部 `default:true`）：
- create → 201 `custom_1ebfa535-…`；**同 request-id 重发 → 同 id**，回读总数 5、同名 1 条（幂等，不产生重复）
- patch 改名 → 回读命中新名
- delete 成功；**同 request-id 重发 delete 仍成功**（幂等）；最终回读 4 类，id/名称与基线完全一致，临时类别清零
- 全程未触发 409；真实事项/目标/复盘未动

## 7. 脱敏回执结构（可直接照抄字段）

```json
{"patch":"…","bundleId":"…","zip":{"bytes":27775,"sha256Matched":true},
 "scopeCheck":{"declaredFiles":6,"payloadAfterHashesMatch":true,"targetBeforeHashesMatch":true,"onlySixPathsDifferFromBaseline":true},
 "manifest":{"before":"bf93…","after":"e193…","fileCountAfter":52,"verifyManifest":"OK 52/52"},
 "task":{"enabledBefore":true,"enabledAfter":true,"stateAfter":"Ready","waitedIdleSeconds":12,"killedProcess":false,"lockRemoved":false,"actionUnchanged":true,"reactivated":false},
 "privateConfig":{"unchanged":true,"filesChecked":[…6 项…]},
 "categoryTests":{"baselineCount":4,"createRetrySameRequestId":"same id","finalCount":4,"finalEqualsBaseline":true,"conflict409":"none"},
 "businessDataUntouched":{"items":37,"goals":2,"reviews":1},
 "rootOfflineCopy":{"verifyManifest":"OK 51 files","releaseManifestCopiedToRoot":false}}
```

## 8. 本轮新发现

- 新 manifest 的 `sourceCommit`/`sourceSiteVersion` 未随补丁前进（两版都是 `975d8984…`/30），只有 `patch.json.sourceCommit=791e83f8…`；属元数据不同步，功能无影响 → 回执点出，交回协调端。
- 安装器自带内存 smoke 覆盖面：`emptyState` → `category.patch` 改名 → 删到最后一类必须抛 `last_category` → `validateBackup(createBackup(s))` 后类别名仍为新名（证明新备份规则生效）。
- 补丁也会改「技能文档」(`deployment/hermes-skill.md`) 并追加到生效技能：这类改动必须靠**前缀逐字节 + 旧 sha** 证明原文没被重写，别只看「文件变大了」。
