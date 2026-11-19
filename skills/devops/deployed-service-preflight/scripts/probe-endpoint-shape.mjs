#!/usr/bin/env node
// probe-endpoint-shape.mjs —— 只读取证：同一个路由跑多组 query，报 status/形状/条数/字段并集
//
// 用法：node probe-endpoint-shape.mjs <releaseRoot> <connection.json> <route> [route...]
//   例：node probe-endpoint-shape.mjs \
//         C:/Users/x/AppData/Local/DayflowHome/releases/sites29-afdf902-home1 \
//         C:/Users/x/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/runtime/.local/hermes-cloud-connection.json \
//         /api/v1/reminders/due '/api/v1/reminders/due?calendarChanges=1&lead=18' '/api/v1/reminders/due?lead=1200'
//
// 为什么不用裸 fetch / urllib：win32 上裸请求会吃 Cloudflare 403 (error code: 1010)，
// 只有 release 自带的 http-request.mjs（内部 spawn pwsh）能过。
// 输出不含 url、key、正文：只给字段名与计数，可直接进回执。
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const [, , releaseRoot, connPath, ...routes] = process.argv;
if (!releaseRoot || !connPath || !routes.length) {
  console.error('usage: node probe-endpoint-shape.mjs <releaseRoot> <connection.json> <route> [route...]');
  process.exit(2);
}

// pwsh 前置：http-request.mjs 在 win32 上 spawn('pwsh')，系统 PATH 里通常没有
const autoPath = path.join(releaseRoot, 'runtime', '.local', 'calendar-automation.json');
if (fs.existsSync(autoPath)) {
  try {
    const auto = JSON.parse(fs.readFileSync(autoPath, 'utf8').replace(/^\uFEFF/, ''));
    if (auto.pwshExe) process.env.PATH = path.dirname(auto.pwshExe) + ';' + process.env.PATH;
  } catch { /* 没有就照常跑，缺 pwsh 会自己报 runtime_missing */ }
}

const {httpRequest} = await import(
  pathToFileURL(path.join(releaseRoot, 'runtime', 'scripts', 'http-request.mjs')).href);

const cfg = JSON.parse(fs.readFileSync(connPath, 'utf8').replace(/^\uFEFF/, ''));
const headers = {Authorization: 'Bearer ' + cfg.key};
if (cfg.siteToken) headers['OAI-Sites-Authorization'] = 'Bearer ' + cfg.siteToken;

const rows = [];
for (const route of routes) {
  const row = {route};
  try {
    const r = await httpRequest(new URL(route, cfg.url), {headers, timeoutMs: 25000});
    row.status = r.status;
    row.bytes = Buffer.byteLength(r.body || '');
    let d = null;
    try { d = JSON.parse(r.body); } catch { }
    const arr = Array.isArray(d) ? d
      : (d && typeof d === 'object'
        ? ['candidates', 'due', 'reminders', 'items'].map(k => d[k]).find(Array.isArray) || null
        : null);
    row.shape = Array.isArray(d) ? 'array' : (d && typeof d === 'object' ? 'object' : 'unparsable');
    row.n = Array.isArray(arr) ? arr.length : null;
    row.fields = Array.isArray(arr)
      ? [...new Set(arr.flatMap(x => (x && typeof x === 'object') ? Object.keys(x) : []))].sort()
      : [];
  } catch (e) {
    row.error = (e.code || '') + ' ' + e.message;
  }
  rows.push(row);
}
console.log(JSON.stringify(rows, null, 1));
