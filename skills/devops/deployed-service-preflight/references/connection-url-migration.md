# 私有连接配置的 URL 迁移：校验 → 原子替换 → 独立回读

场景（2026-11-04 实测，A2A 对端下发）：Sites 重新发布后原域名 HTTP 307 指向新域名，
旧客户端拒绝跟随重定向，定时任务失败。授权范围：**只改本机 release 里私有
`hermes-cloud-connection.json` 的 `url`**，用原密钥，不换密钥、不改发布清单/脚本/Hermes 配置、
不重启、不手动触发同步、不发消息。

## 铁律

- 写操作只有 `url` 一个字段。密钥、`siteToken`、其他任何键都不许动。
- 先证明新域名是**同一个生产库**，再动手；证明不了就回报并停。
- 回执只给布尔/计数/时间戳，不输出 URL、key、token、备份正文、日程/邮件内容。
- 不重启、不触发同步、不改清单、不发消息；下一轮由对端独立核验。

## 一、只读校验（通过才允许写）

1. 文件存在、当前 `url` ∈ {旧值, 新值}。若是第三个值 → `Unexpected configured URL`，停。
2. 头部：`Authorization: Bearer <key>`；若配置里有 `siteToken`，再加 `OAI-Sites-Authorization: Bearer <siteToken>`。
3. **`MaximumRedirection = 0`** —— 关键。默认跟随会掩盖「还是 307」，等于没验证迁移成功。
4. 代理：读 `calendar-automation.json` 的 `httpProxy`，只允许 **loopback 且 UserInfo 为空**，否则报 `Unexpected proxy`（防把凭据带进 URL）。
5. 身份判定（对齐「同一生产库」）：
   - `GET <new>/api/v1/sync/work/status` 返回 200（不是 3xx）；
   - `hosts[]` 里存在已知同步主机 key（本次 `7d4b5206-…-f817197b6414`）；
   - `sources[]` 中 `body.selected == true` 的条数 == 对端说的数（本次 3）。
   任一条不符 → `Unexpected production identity`，停。

实测回执（脱敏）：`urlIsOld:true, hasKey:true, hasSiteToken:false, cfgHasHttpProxy:true,
proxyIsLoopback:true, proxyPort:10808, newStatusHttp:200, hostKeyPresent:true,
selectedSourceCount:3, identityOk:true`。

## 二、原子替换（写前把校验做完）

顺序不能变，且**所有哈希计算放在写入分支的最前面**——这样任何 throw 都发生在落盘之前，
自然得到「失败 = 零改动」的强保证：

1. `$originalHash = (Get-FileHash $p -Algorithm SHA256).Hash`
2. `$keyHashBefore = SHA256(key)`；`$otherBefore = 除 url 外每个属性名=哈希` 拼成一串
3. `$tmp = $p + '.' + guid + '.tmp'`；`$bak = $p + '.pre-sites37-' + guid + '.bak'`
4. `$c.url = $new`；`[IO.File]::WriteAllText($tmp, ($c | ConvertTo-Json -Depth 20 -Compress), [Text.UTF8Encoding]::new($false))`
   —— UTF-8 **无 BOM**，客户端按 UTF-8 解析带 BOM 会崩。
5. `Set-Acl -LiteralPath $tmp -AclObject (Get-Acl -LiteralPath $p)` —— 新文件继承原 ACL。
6. `[IO.File]::Replace($tmp, $p, $bak)` —— 同一卷内原子替换并留备份（跨卷会抛，勿用 Move 顶替）。
7. 回读：`url == 新值` 且 `keyHashBefore == 回读 keyHash` 且 `otherBefore == otherAfter` 且 `Get-FileHash $bak == $originalHash`，
   任一不符 `throw 'Connection post-check failed'`。

`ConvertTo-Json` 会重排/压缩整个文件（182B → 170B 正常），所以「只动了 url」不能靠肉眼看 diff，
必须靠上面第 2/7 步的字段哈希串证明。

## 三、独立回读（换个脚本再验一遍）

不要拿同一个脚本的自报当结论，另起一个只读脚本核：

- `url == 新值`、`ConvertFrom-Json` 仍成功、顶层键仍只有 `url`/`key`
- `key -ceq 备份里的 key`（逐字符）
- `(Get-Acl $p).Sddl -eq (Get-Acl $bak).Sddl`（ACL 没被 Replace 改掉）
- `.pre-sites37-*.bak` 恰好 1 个，且其 url 仍是旧值
- 残留 `*.tmp` 计数 == 0

本次实测：`urlIsNew:true, keyIdenticalToBackup:true, backupUrlIsOld:true,
aclSddlMatchesBackup:true, strayTmpCount:0, backupCount:1`。

## 四、PowerShell 细节坑

- **Windows PowerShell 5.1 没有 `[Convert]::ToHexString`**（.NET Framework 才有；pwsh 7 有）。
  首次执行就是死在这一行，`MethodNotFound`，中文报错在 bash 里还是 GBK 乱码。
  统一用 `[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','')`。
- 脚本一律落成 `.ps1` 用 `powershell -NoProfile -ExecutionPolicy Bypass -File <绝对路径>` 跑；
  塞进 bash 单行会被吃 `$`、`-e` 里的双引号。
- 脚本自己打印的 JSON **只用 ASCII 键与布尔**，别依赖 PowerShell 的中文报错文本回传。
- `Invoke-WebRequest/RestMethod` 的 `ErrorAction` 走公共参数，放 splat 里合法；
  4xx/5xx 时 `$_.Exception.Response.StatusCode` 才有值，只能回报 `Exception 类型名`，不回报响应正文。

## 五、回执形状

```json
{"changed":true,"verifiedSameProduction":true,"credentialsUnchanged":true,"backupVerified":true,"at":"<ISO8601 UTC>"}
```

正文再补 2–4 行：独立回读结论、首次失败是否发生在写前（本次：`ToHexString` 报错于 tmp 创建之前，零改动）、
以及「未改清单/脚本/配置、未重启、未触发同步、未发消息」。
