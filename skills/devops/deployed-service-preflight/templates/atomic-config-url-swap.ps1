# 原子替换一个 JSON 配置里的单个 URL 字段（PowerShell 5.1 兼容）。
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File atomic-config-url-swap.ps1 `
#         -ConfigPath <json 绝对路径> -OldUrl <旧> -NewUrl <新> [-BackupTag pre-migration]
# 回执只有 ASCII 布尔 JSON，不打印任何 URL/密钥/正文。
param(
  [Parameter(Mandatory = $true)][string]$ConfigPath,
  [Parameter(Mandatory = $true)][string]$OldUrl,
  [Parameter(Mandatory = $true)][string]$NewUrl,
  [string]$BackupTag = 'pre-migration'
)
$ErrorActionPreference = 'Stop'

# PS 5.1 没有 [Convert]::ToHexString
function SH([string]$s) {
  $sha = [Security.Cryptography.SHA256]::Create()
  [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s))).Replace('-', '')
}

$c = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
if ($c.url -notin @($OldUrl, $NewUrl)) { throw 'Unexpected configured URL' }

$changed = ($c.url -eq $OldUrl)
$res = [ordered]@{ changed = $changed; credentialsUnchanged = $true; backupVerified = $false; at = [DateTimeOffset]::UtcNow.ToString('o') }

if ($changed) {
  # 所有校验/哈希都在写盘之前
  $originalHash = (Get-FileHash -LiteralPath $ConfigPath -Algorithm SHA256).Hash
  $keyBefore = SH([string]$c.key)
  $othersBefore = (@($c.PSObject.Properties | Where-Object { $_.Name -ne 'url' } |
      ForEach-Object { $_.Name + '=' + (SH([string]$_.Value)) }) -join '|')

  $tmp = $ConfigPath + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
  $bak = $ConfigPath + '.' + $BackupTag + '-' + [guid]::NewGuid().ToString('N') + '.bak'

  $c.url = $NewUrl
  [IO.File]::WriteAllText($tmp, ($c | ConvertTo-Json -Depth 20 -Compress), [Text.UTF8Encoding]::new($false))
  Set-Acl -LiteralPath $tmp -AclObject (Get-Acl -LiteralPath $ConfigPath)
  [IO.File]::Replace($tmp, $ConfigPath, $bak)

  $saved = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
  $othersAfter = (@($saved.PSObject.Properties | Where-Object { $_.Name -ne 'url' } |
      ForEach-Object { $_.Name + '=' + (SH([string]$_.Value)) }) -join '|')

  $urlOk = ($saved.url -eq $NewUrl)
  $credOk = ($keyBefore -ceq (SH([string]$saved.key))) -and ($othersBefore -ceq $othersAfter)
  $bakOk = ((Get-FileHash -LiteralPath $bak -Algorithm SHA256).Hash -eq $originalHash)
  if (-not ($urlOk -and $credOk -and $bakOk)) { throw 'Connection post-check failed' }

  $res.credentialsUnchanged = $credOk
  $res.backupVerified = $bakOk
}

$res | ConvertTo-Json -Compress
