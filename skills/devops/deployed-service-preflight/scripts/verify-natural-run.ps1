# Read-only probe: did the scheduled task run naturally AFTER <cut>, and did it pass?
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File verify-natural-run.ps1 -ReleasePath <release> -Cut 2026-11-04T00:09:21.375Z
# Output: single-line ASCII-key JSON (safe to forward; string values masked).
param(
  [Parameter(Mandatory=$true)][string]$ReleasePath,
  [Parameter(Mandatory=$true)][string]$Cut,
  [string]$TaskName = 'Dayflow-Work-Sync',
  [int]$Tail = 40
)
$ErrorActionPreference = 'Continue'

function Mask([string]$s) {
  if ($null -eq $s) { return $null }
  $s = [regex]::Replace($s, '\S+@\S+', '<email>')
  $s = [regex]::Replace($s, '(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])', '<secret>')
  if ($s.Length -gt 160) { $s = $s.Substring(0,160) + '...' }
  return $s
}

$cutDto = [DateTimeOffset]::Parse($Cut, [Globalization.CultureInfo]::InvariantCulture)
$local  = Join-Path $ReleasePath 'runtime/.local'
$log    = Join-Path $local 'work-automation-observation.jsonl'

$res = [ordered]@{}
$res.nowUtc        = (Get-Date).ToUniversalTime().ToString('o')
$res.cutUtc        = $cutDto.ToUniversalTime().ToString('o')
$res.cutInFuture   = ((Get-Date).ToUniversalTime() -lt $cutDto.UtcDateTime)

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
$res.taskFound     = [bool]$task
$res.enabled       = if ($task) { [bool]$task.Settings.Enabled } else { $null }
$res.taskState     = if ($task) { [string]$task.State } else { $null }
$res.lastResult    = if ($info) { $info.LastTaskResult } else { $null }
$res.lastRunUtc    = if ($info -and $info.LastRunTime) { ([DateTimeOffset]$info.LastRunTime).ToUniversalTime().ToString('o') } else { $null }
$res.nextRunUtc    = if ($info -and $info.NextRunTime) { ([DateTimeOffset]$info.NextRunTime).ToUniversalTime().ToString('o') } else { $null }
$res.taskCwd       = if ($task -and $task.Actions.Count -gt 0) { [string]$task.Actions[0].WorkingDirectory } else { $null }
$res.taskCwdIsRelease = if ($res.taskCwd) { $res.taskCwd.TrimEnd('\') -ieq $ReleasePath.TrimEnd('\') } else { $null }

$res.logExists = Test-Path -LiteralPath $log
$res.logMtimeUtc = $null
$res.logLines = 0
$res.parseFail = 0
$res.logNewerThanCut = $null
$runs = @()

if ($res.logExists) {
  $fi = Get-Item -LiteralPath $log
  $res.logMtimeUtc = $fi.LastWriteTimeUtc.ToString('o')
  $res.logNewerThanCut = ($fi.LastWriteTimeUtc -gt $cutDto.UtcDateTime)
  $lines = @(Get-Content -LiteralPath $log -Tail $Tail)
  $res.logLines = $lines.Count

  foreach ($l in $lines) {
    if ([string]::IsNullOrWhiteSpace($l)) { continue }
    $o = $null
    try { $o = $l | ConvertFrom-Json } catch { $o = $null }

    $sa = $null; $fa = $null; $err = $null; $calOk = $null; $mailOk = $null; $cmdCount = $null; $parsed = $false
    if ($null -ne $o) {
      $parsed = $true
      $sa = [string]$o.startedAt; $fa = [string]$o.finishedAt; $err = [string]$o.error
      $calOk = ($o.calendar -and $o.calendar.complete -eq $true)
      $mailOk = ($o.mail -and $o.mail.complete -eq $true)
      $cmdCount = @($o.commands).Count
    } else {
      $res.parseFail++
      $sa = [regex]::Match($l, '"startedAt":"(?<v>[^"]*)"').Groups['v'].Value
      $fa = [regex]::Match($l, '"finishedAt":"(?<v>[^"]*)"').Groups['v'].Value
      $err = [regex]::Match($l, '"error":"(?<e>[\s\S]*?)"\s*,?\s*"finishedAt"').Groups['e'].Value
      if (-not $err) { $err = [regex]::Match($l, '"error":(?<e>.{0,160})').Groups['e'].Value }
      $cmdCount = if ($l -match '"commands":\[\]') { 0 } else { $null }
    }

    $started = $null
    try { $started = [DateTimeOffset]::Parse($sa, [Globalization.CultureInfo]::InvariantCulture) } catch { }
    if ($null -eq $started -or $started -le $cutDto) { continue }

    $ok = ($parsed -and $calOk -and $mailOk -and -not $err -and $cmdCount -eq 0)
    $runs += [ordered]@{
      startedAt  = $started.ToUniversalTime().ToString('o')
      finishedAt = $fa
      parsed     = $parsed
      calendarComplete = $calOk
      mailComplete     = $mailOk
      commands         = $cmdCount
      error      = (Mask $err)
      pass       = $ok
    }
  }
}

$res.postCutRuns = $runs
$res.postCutCount = $runs.Count
$res.passCount = @($runs | Where-Object { $_.pass }).Count
$res.verdict = if ($res.passCount -gt 0) { 'pass' } elseif ($runs.Count -gt 0) { 'fail' } elseif ($res.cutInFuture) { 'not_run_cut_in_future' } else { 'not_run' }
$res.note = 'null/empty from a filter script is NOT proof of not-run: check parseFail, logMtimeUtc, lastRunUtc first.'

$res | ConvertTo-Json -Depth 6 -Compress
