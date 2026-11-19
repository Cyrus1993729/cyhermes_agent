// 只读探针：验证「带查询参数的已认证 GET」是否被服务端接受/解析。
// 只输出 status / 形状 / 字段名，绝不打印正文、标题或凭据。
//
// 用法：
//   node probe-auth-get.mjs <releaseRoot> "reminders/due?calendarChanges=1&lead=18"
//   node probe-auth-get.mjs <releaseRoot> "reminders/due?lead=abc"   # 非法值探针：仍 200 ⇒ 参数没被解析
//
// releaseRoot 例：C:/Users/<u>/AppData/Local/DayflowHome/releases/<bundle>
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const [releaseRoot, route] = process.argv.slice(2);
const out = (o) => console.log(JSON.stringify(o));
if (!releaseRoot || !route) { out({ok: false, reason: 'usage: <releaseRoot> "<route>?<query>"'}); process.exit(2); }

const localDir = path.join(releaseRoot, 'runtime', '.local');
const connPath = path.join(localDir, 'hermes-cloud-connection.json');
if (!fs.existsSync(connPath)) { out({ok: false, reason: 'connection-missing'}); process.exit(2); }
const conn = JSON.parse(fs.readFileSync(connPath, 'utf8').replace(/^\uFEFF/, ''));

// 复刻入口脚本的 environment()：pwsh 前置到 PATH，用本机代理（仅本次进程）。
const cfgPath = path.join(localDir, 'calendar-automation.json');
const cfg = fs.existsSync(cfgPath) ? JSON.parse(fs.readFileSync(cfgPath, 'utf8').replace(/^\uFEFF/, '')) : {};
if (cfg.pwshExe) process.env.PATH = path.dirname(cfg.pwshExe) + path.delimiter + process.env.PATH;
if (cfg.httpProxy) { process.env.HTTP_PROXY = cfg.httpProxy; process.env.HTTPS_PROXY = cfg.httpProxy; }

if (typeof conn.key !== 'string' || !/^[A-Za-z0-9_-]{64,200}$/.test(conn.key)) { out({ok: false, reason: 'connection-shape'}); process.exit(2); }

const modURL = pathToFileURL(path.join(releaseRoot, 'runtime', 'scripts', 'http-request.mjs')).href;
let httpRequest;
try { ({httpRequest} = await import(modURL)); } catch (e) { out({ok: false, reason: 'transport-import', error: String(e.message).slice(0, 80)}); process.exit(2); }

const url = new URL('/api/v1/' + route, conn.url);
const report = {route, path: url.pathname + url.search};
try {
  const r = await httpRequest(url, {
    method: 'GET',
    headers: {Authorization: 'Bearer ' + conn.key, Accept: 'application/json'},
    timeoutMs: 30000,
  });
  report.status = r.status;
  let v;
  try { v = JSON.parse(r.body); } catch { v = undefined; }
  if (Array.isArray(v)) {
    report.bodyKind = 'array';
    report.count = v.length;
    report.itemKeys = v.length ? Object.keys(v[0]).sort() : [];
  } else if (v && typeof v === 'object') {
    report.bodyKind = 'object';
    report.keys = Object.keys(v).sort();
  } else {
    report.bodyKind = 'non-json';
    report.bodyLen = (r.body || '').length;
  }
} catch (e) {
  // runtime_missing ≈ PATH 缺 pwsh（先验 cfg.pwshExe 是否读到）；transport_error ≈ 代理/网络
  report.ok = false;
  report.error = String(e.code || e.message || 'error').slice(0, 80);
}
out(report);
