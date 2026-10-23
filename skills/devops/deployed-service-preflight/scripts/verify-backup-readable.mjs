#!/usr/bin/env node
// 只读核验：现有备份能否被（更新后的）读取器解析。
// 用法: node verify-backup-readable.mjs <runtime/lib/backup.ts> <backup.json>
// 输出: 单行脱敏 JSON（字段名 + 计数），不含任何业务正文/密钥。
// node >= 23 默认类型擦除，可直接 import .ts。
import fs from "node:fs";
import { pathToFileURL } from "node:url";

const libPath = process.argv[2];
const bkPath = process.argv[3];

const emit = (o) => console.log(JSON.stringify(o));

if (!libPath || !bkPath) {
  emit({ error: "usage: node verify-backup-readable.mjs <lib.ts> <backup.json>" });
  process.exit(2);
}

const len = (v) =>
  Array.isArray(v) ? v.length : v && typeof v === "object" ? Object.keys(v).length : 0;

try {
  const m = await import(pathToFileURL(libPath).href);
  const fn = m.validateBackup;
  if (typeof fn !== "function") {
    emit({ error: "validateBackup not exported", exports: Object.keys(m) });
    process.exit(4);
  }
  const b = JSON.parse(fs.readFileSync(bkPath, "utf8"));
  const s = fn(b) || {};
  emit({
    valid: true,
    backupVersion: b.version,
    exportedAt: b.exportedAt,
    requiredFeatures: Array.isArray(b.requiredFeatures) ? b.requiredFeatures : [],
    items: len(s.items),
    goals: len(s.goals),
    reviews: len(s.reviews),
    newReaderUsed: true,
    noRestore: true
  });
} catch (e) {
  const msg = e && e.message ? e.message : String(e);
  emit({ error: "reader failed", detail: msg.slice(0, 600), code: (e && e.code) || null });
  process.exit(5);
}
