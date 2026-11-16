# 成对写读：临时锁 → 独立核验 → 还原（Dayflow ai-models，2026-11-04 实测）

场景：A2A 对端做「配置能被独立读取 + 能原样还原」的联机证明。
第一步把某用途的 override 锁定成它当前 effective 的同一型号（只把 `source` 从 default 变 independent），
对端用自己的 HTTP 通道独立回读确认后，第二步用新 request id 与最新 version 把 override 置回 null。

## 环境

```
release   : C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1
node      : <root>/tools/node24/node.exe     (类型擦除，可直接 import .ts)
pwsh      : <root>/tools/pwsh7/pwsh.exe      (不在系统 PATH)
connection: <release>/runtime/.local/hermes-cloud-connection.json  (键: url,key[,siteToken]，不打印)
```

## 唯一可用的调用姿势（bash 里 export PATH 无效）

```bash
cd "<release>/runtime" && "<root>/tools/pwsh7/pwsh.exe" -NoLogo -NoProfile -NonInteractive -Command "\
\$env:PATH='<root>\tools\pwsh7;'+\$env:PATH; \
& '<root>\tools\node24\node.exe' 'scripts\hermes-local.mjs' \
  --connection '.local\hermes-cloud-connection.json' \
  --request-id '<uuid>' --json-file '.local\<payload>.json' models-set; 'EXIT='+\$LASTEXITCODE"
```

- MSYS bash 里 `export PATH=...pwsh7:$PATH` 传给 node 后 `spawn('pwsh')` 仍失败 →
  `{"errorType":"runtime_missing","phase":"startup","durationMs":31}`、退出码 1。31ms 级失败就是 PATH 问题，与 key/网络无关。
- `models` / `models-catalog` 是只读，`hermes-local.mjs` 不读 stdin；其余操作才需要 `--json-file`（stdin 也行但不稳）。
- env 里的 `DAYFLOW_REQUEST_ID` 不生效，只有 `--request-id` flag 可靠。

## 实测回执（2026-11-04 20:58 本地）

```
before  exit=0  version=1 epochDigest=e3b0c442…b855 default=deepseek-v4-flash
        mail=deepseek-v4-flash(indep) review=default coach=deepseek-v4.1-flash(indep) capture=default
write   requestId=ef307403-… payload={"version":1,"epochDigest":"e3b0…","overrides":{"mail":null}}
        → 200 3404ms attempt=1 exit=0 response {version:2, overrides:{mail:null, review:null,
          coach:deepseek-v4.1-flash, capture:null}}   （version 1→2）
after   exit=0  version=2 epochDigest 未变 default 未变
        mail selection=null source=default effective=deepseek-v4-flash（型号不变）
        其余三用途 effective 与 source 全未变
```

判读三件事：① 还原后该用途 `selection:null` + `source:default`，但 `effectiveModel` 必须与还原前相同；
② `epochDigest` 不变说明不是换库；③ version 连续（0→1→2 无跳号）= 窗口内无第三方写入。

## 配套的云端备份核验（同一轮常一起要）

`runtime/scripts/work-backup.mjs` **不是 CLI**，只有导出函数；用
`scripts/backup-drill-verify.mjs <release> <connection.json>` 一次跑完：GET 备份（仅内存）→ 读器校验（backup/
persistence/coach-records/work-records）→ `isolatedBackupDrill`（内部已完成真空库恢复 + 非空二次恢复）。

实测（305408 B 那次导出）：`requiredFeatures:["ai-models-v1"]`，items 61 / goals 2 / reviews 1 / drafts 0 /
history 128 / coach 5 / work 139；drill `complete, isolated, nonemptyRestore, items 61, records 139`，与计数全等。
`ai-models-v1` 的内容不在顶层而在 `coach[]`：`ai_model_configuration` 的
`selection:{schema:1,defaultModel,overrides}` ＋ 3 条 `model_operation`（test：unknown / failed / complete）。

## 坑清单

- 备份每次导出 `exportedAt` 不同 ⇒ 字节数与 SHA256 都变，回执必须写「本次导出专属」。
- 云端 `runs[].updatedAt` 与本地 `work-host.json` 的 `lastCalendar`/`lastMail` 差几十秒，报告以云端为准确时刻。
- `history/coach/work` 在备份顶层，`items/goals/reviews/drafts` 在 `data.*`；按错位置会报 0。
- 收尾删掉 `.local/<payload>.json` 与临时 runner（`$LOCALAPPDATA/Temp/*.mjs`），release 内零残留。
