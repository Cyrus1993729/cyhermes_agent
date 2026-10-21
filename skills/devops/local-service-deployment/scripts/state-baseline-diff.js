// 通用基线比对：受控写入前后各存一份 state JSON，跑本脚本给出计数与差异。
// 标题只输出 sha256 前 12 位，避免把真实数据贴进回执/日志。
// 用法: node state-baseline-diff.js <before.json> <after.json> [--items-key items] [--id-key id] [--title-key title] [--extra-keys goals,reviews]
const fs = require('fs');
const crypto = require('crypto');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));
const [beforePath, afterPath] = positional;
if (!beforePath || !afterPath) { console.error('用法: node state-baseline-diff.js <before.json> <after.json>'); process.exit(2); }

const itemsKey = flag('items-key', 'items');
const idKey = flag('id-key', 'id');
const titleKey = flag('title-key', 'title');
const extraKeys = flag('extra-keys', 'goals,reviews').split(',').map(s => s.trim()).filter(Boolean);
const h = s => crypto.createHash('sha256').update(String(s || '')).digest('hex').slice(0, 12);

const before = JSON.parse(fs.readFileSync(beforePath, 'utf8').replace(/^\uFEFF/, ''));
const after = JSON.parse(fs.readFileSync(afterPath, 'utf8').replace(/^\uFEFF/, ''));
const bItems = before[itemsKey] || [], aItems = after[itemsKey] || [];
const aById = new Map(aItems.map(i => [i[idKey], i]));
const bIds = new Set(bItems.map(i => i[idKey]));

const missing = [], changed = [], unchanged = [];
for (const o of bItems) {
  const n = aById.get(o[idKey]);
  if (!n) { missing.push(o[idKey]); continue; }
  const diffs = [];
  if (n.version !== o.version) diffs.push(`version ${o.version}->${n.version}`);
  if (n.status !== o.status) diffs.push(`status ${o.status}->${n.status}`);
  if (n.category !== o.category) diffs.push(`category ${o.category}->${n.category}`);
  if (n.source !== o.source) diffs.push(`source ${o.source}->${n.source}`);
  if (h(n[titleKey]) !== h(o[titleKey])) diffs.push('title-changed');
  (diffs.length ? changed : unchanged).push(diffs.length ? { id: o[idKey], diffs } : o[idKey]);
}
const added = aItems.filter(i => !bIds.has(i[idKey])).map(i => ({
  id: i[idKey], status: i.status, version: i.version, source: i.source,
  titleHash: h(i[titleKey]), executions: (i.executions || []).length,
  actualMinutes: i.actualMinutes || 0,
}));

const sum = (arr, k) => arr.reduce((a, i) => a + (Number(i[k]) || 0), 0);
const execCount = arr => arr.reduce((a, i) => a + ((i.executions || []).length), 0);
const extras = {};
for (const k of extraKeys) extras[k] = { before: (before[k] || []).length, after: (after[k] || []).length };

const report = {
  ok: missing.length === 0 && changed.length === 0,
  items: { before: bItems.length, after: aItems.length },
  revision: { before: before.revision, after: after.revision },
  executionsTotal: { before: execCount(bItems), after: execCount(aItems) },
  actualMinutesSum: { before: sum(bItems, 'actualMinutes'), after: sum(aItems, 'actualMinutes') },
  extras,
  missingOriginalIds: missing,
  changedOriginal: changed,
  unchangedCount: unchanged.length,
  added,
};
console.log(JSON.stringify(report, null, 1));
process.exitCode = report.ok ? 0 : 1;
