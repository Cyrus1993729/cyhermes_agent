// 增量补丁运行器模板：停计划任务 → 等在途结束 → apply → finally 无条件恢复 → 落 result JSON
// 用法：改 ROOT/PATCH/RELEASE/TASK 后 `node24 apply_patch_guarded.mjs`
// 铁律：不杀进程、不删锁；停用与恢复必须在同一个 try/finally 里，绝不拆成多次调用。
// 顺序：先停触发器再等空闲 —— apply.mjs 同时要求 Enabled=false 且无锁，先停能防止等待期间新开一轮。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';

const ROOT = 'C:/Users/<user>/AppData/Local/<AppHome>';
const PATCH = path.join(ROOT, 'patches/<patchId>/extracted');
const RELEASE = path.join(ROOT, 'releases/<bundleId>');
const NODE24 = path.join(ROOT, 'tools/node24/node.exe');
const LOCAL = path.join(RELEASE, 'runtime/.local');
const LOCK = path.join(LOCAL, 'work-sync.lock');
const LOG = path.join(ROOT, 'patches/<patchId>/install-result.json');
const TASK = '<TaskName>';
const IDLE_BUDGET_MS = 150000;
// 私有/授权配置：只在内存里比前后哈希，结果只落布尔
const PRIVATE = ['home-deployment.json', 'home-enabled.json', 'hermes-cloud-connection.json', 'calendar-automation.json', 'cutover-permit.json', 'runtime-paths.json'];

const ps = (script) => execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], {encoding: 'utf8', windowsHide: true}).trim();
const taskState = () => {
  const raw = ps(`$t=Get-ScheduledTask -TaskName '${TASK}'; "Enabled=$($t.Settings.Enabled);State=$([string]$t.State)"`);
  const m = raw.match(/Enabled=(\w+);State=(\w+)/);
  return {raw, enabled: m[1] === 'True', state: m[2]};
};
const h = (p) => { try { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'); } catch { return null; } };
const privSnapshot = () => Object.fromEntries(PRIVATE.map(f => [f, h(path.join(LOCAL, f))]));
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const result = {startedAt: new Date().toISOString()};
const log = (k, v) => { result[k] = v; };
let originallyEnabled = null;
const pre = {private: privSnapshot(), categories: h(path.join(RELEASE, 'runtime/lib/categories.ts'))};

// 落地证据只认哈希，不认 mtime（copyFileSync+rename 保留源时间戳）
log('preCategoriesSha256', pre.categories);

try {
  const before = taskState();
  originallyEnabled = before.enabled;
  log('taskBefore', before);
  log('lockBefore', fs.existsSync(LOCK));

  // 1) 先停触发器（保持同一 task 对象，不重新注册）
  ps(`Disable-ScheduledTask -TaskName '${TASK}' | Out-Null`);
  const s1 = taskState();
  log('taskAfterDisable', s1);
  if (s1.enabled) throw new Error('disable failed');

  // 2) 等在途那一轮自然结束（不 kill、不删锁）
  const deadline = Date.now() + IDLE_BUDGET_MS;
  let idle = false;
  while (Date.now() < deadline) {
    const s = taskState();
    if (s.state !== 'Running' && !fs.existsSync(LOCK)) { idle = true; break; }
    await sleep(3000);
  }
  log('idleReachedAt', new Date().toISOString());
  if (!idle) { log('aborted', 'wait_for_idle_timeout'); throw new Error('idle timeout'); }

  // 3) 用该程序自带的独立 Node 跑安装器
  try {
    result.applyStdout = execFileSync(NODE24, [path.join(PATCH, 'apply.mjs'), RELEASE], {encoding: 'utf8', windowsHide: true}).trim();
    result.applyExit = 0;
  } catch (e) {
    result.applyExit = e.status ?? -1;
    result.applyStdout = (e.stdout || '').toString().trim().slice(0, 4000);
    result.applyStderr = (e.stderr || '').toString().trim().slice(0, 4000);
  }
} catch (e) {
  log('error', String(e.message || e));
} finally {
  try {
    if (originallyEnabled === true) ps(`Enable-ScheduledTask -TaskName '${TASK}' | Out-Null`);   // 只切 Enabled，不重新 activate
    const after = taskState();
    log('taskAfterRestore', after);
    log('taskRestoredToOriginal', after.enabled === originallyEnabled);
    log('taskAction', ps(`$t=(Get-ScheduledTask -TaskName '${TASK}').Actions[0]; "$($t.Execute)|$($t.Arguments)"`));
  } catch (e) {
    log('restoreError', String(e.message || e));
  }
  const post = {private: privSnapshot(), categories: h(path.join(RELEASE, 'runtime/lib/categories.ts'))};
  log('privateConfigUnchanged', JSON.stringify(pre.private) === JSON.stringify(post.private));
  log('categoriesSha256Changed', pre.categories !== post.categories);
  log('lockAfter', fs.existsSync(LOCK));
  result.finishedAt = new Date().toISOString();
  fs.writeFileSync(LOG, JSON.stringify(result, null, 1), 'utf8');
  console.log(JSON.stringify(result, null, 1));
}
