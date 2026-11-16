// 只读探针：GET /api/v1/backup（走 release 自带的 Windows 传输层）→ 内存 SQLite 隔离恢复演练
// 用法: <root>/tools/node24/node.exe backup-drill-verify.mjs <release-dir> <hermes-cloud-connection.json>
// 前提: PATH 前置 <root>/tools/pwsh7（http-request.mjs 在 win32 上 spawn('pwsh')）
// 纪律: 响应只在内存；不落盘、不打印正文/标题/密钥；stdout 只有一行脱敏 JSON
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const release = process.argv[2];
const cfgPath = process.argv[3];
if (!release || !cfgPath) {
  console.log(JSON.stringify({ error: 'usage: backup-drill-verify.mjs <release-dir> <connection.json>' }));
  process.exit(2);
}
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const { httpRequest } = await import(pathToFileURL(release + '/runtime/scripts/http-request.mjs').href);

const out = { httpStatus: 0 };
let bodyText = null;
try {
  const r = await httpRequest(new URL('/api/v1/backup', cfg.url).toString(), {
    method: 'GET',
    headers: { Authorization: 'Bearer ' + cfg.key, Accept: 'application/json' },
    timeoutMs: 60000,
  });
  out.httpStatus = r.status;
  if (r.status === 200) bodyText = r.body;
} catch (e) {
  out.transportError = e.code || e.message;
}
if (out.httpStatus !== 200 || typeof bodyText !== 'string') {
  console.log(JSON.stringify(out));
  process.exit(0);
}

const buf = Buffer.from(bodyText, 'utf8');
out.bytes = buf.length;
out.sha256 = createHash('sha256').update(buf).digest('hex');
out.shaNote = 'per-export: exportedAt changes on every GET, so bytes/sha256 are this export only';

let backup;
try {
  backup = JSON.parse(bodyText);
} catch {
  out.parseError = 'json_invalid';
  console.log(JSON.stringify(out));
  process.exit(0);
}

out.format = backup.format;
out.backupVersion = backup.version;
out.exportedAt = backup.exportedAt; // 服务端时钟，实测可快本机 ~2min
out.requiredFeatures = Array.isArray(backup.requiredFeatures) ? backup.requiredFeatures : [];
out.counts = {
  items: ((backup.data && backup.data.items) || []).length,
  goals: ((backup.data && backup.data.goals) || []).length,
  reviews: ((backup.data && backup.data.reviews) || []).length,
  history: (backup.history || []).length,
  coach: (backup.coach || []).length,
  work: (backup.work || []).length,
};

// ai-models-v1 的载荷不在顶层，而在 coach[]：ai_model_configuration 的 selection + model_operation 测试回执
const purposes = {};
for (const row of backup.coach || []) {
  const p = (row && row.body && row.body.purpose) || '?';
  purposes[p] = (purposes[p] || 0) + 1;
}
const cfgRow = (backup.coach || []).find(x => x && x.body && x.body.purpose === 'ai_model_configuration');
const ops = (backup.coach || []).filter(x => x && x.body && x.body.purpose === 'model_operation');
const lastOp = ops.length ? ops[ops.length - 1].body : null;
out.aiModels = {
  coachPurposes: purposes,
  selection: cfgRow ? cfgRow.body.selection : null,
  modelOperationReceipts: ops.length,
  lastOperation: lastOp
    ? { operation: lastOp.operation, status: lastOp.status, model: lastOp.model, requestIdPrefix: String(lastOp.requestId || '').slice(0, 8) + '…', finishedAt: lastOp.finishedAt }
    : null,
};

let validatedState = null;
try {
  const { validateBackup } = await import(pathToFileURL(release + '/runtime/lib/backup.ts').href);
  validatedState = validateBackup(backup);
  out.valid = true;
  out.storageVersion = validatedState.storageVersion;
} catch (e) {
  out.valid = false;
  out.validateError = e.message;
}

// 读取器全链路：history / coach / work 三个模块都要能读（ai-models-v1 备份就看这几条过不过）
try {
  const p = await import(pathToFileURL(release + '/runtime/lib/persistence.ts').href);
  const { backupCoach } = await import(pathToFileURL(release + '/runtime/lib/coach-records.ts').href);
  const { backupWork } = await import(pathToFileURL(release + '/runtime/lib/work-records.ts').href);
  p.validateHistory(backup);
  out.readers = {
    validateHistory: 'ok',
    coachRows: backupCoach(backup).length,
    workRows: backupWork(backup, validatedState || {}).length,
  };
} catch (e) {
  out.readers = { error: String((e && e.message) || e).slice(0, 200) };
}

// 演练自己覆盖「空库 → 恢复 → 逐段深度比对 → 带 epoch 二次恢复」，不要手写恢复流程
try {
  const mod = await import(pathToFileURL(release + '/runtime/scripts/work-backup.mjs').href);
  out.drillExported = typeof mod.isolatedBackupDrill === 'function';
  if (out.drillExported) {
    const d = await mod.isolatedBackupDrill(backup);
    out.drill = {
      at: d.at, status: d.status, isolated: d.isolated,
      nonemptyRestore: d.nonemptyRestore, items: d.items, workRecords: d.records,
      matchesBackup: d.items === out.counts.items && d.records === out.counts.work,
    };
  }
} catch (e) {
  out.drill = { status: 'failed', error: String((e && e.message) || e).slice(0, 300) };
}

console.log(JSON.stringify(out));
