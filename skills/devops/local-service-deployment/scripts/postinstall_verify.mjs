// 补丁装后验证器模板：manifest 计数 + client 只读回读 + 内存严格类型探针（只写脱敏 JSON）
// 用法：改下面常量后 `<tools>/node24/node.exe postinstall_verify.mjs`
// 铁律：不写业务库（只用 emptyState 内存态）、不打印凭据/业务内容；client 只发 GET。
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const ROOT = 'C:/Users/<user>/AppData/Local/<AppHome>';
const PATCH_ID = '<patchId>';
const RELEASE = path.join(ROOT, 'releases/<bundleId>');
const NODE24 = path.join(ROOT, 'tools/node24/node.exe');
const OUT = path.join(ROOT, 'patches', PATCH_ID, 'verify');
const EXPECTED_FILES = 52;
const CLIENT = 'runtime/scripts/hermes-cloud.mjs';   // 只读 op 名放 CLIENT_OP
const CLIENT_OP = 'categories';
// 可选：期望哈希（留空则跳过）
const EXPECT_MANIFEST_SHA = '';
const STRICT_PROBES = [                             // [label, action, body]
  ['patch color:[teal]', 'category.patch', {id: 'work', color: ['teal']}],
  ['patch icon:{teal}', 'category.patch', {id: 'work', icon: {teal: 1}}],
];

fs.mkdirSync(OUT, {recursive: true});
const res = {patch: PATCH_ID, finishedAt: new Date().toISOString()};

// 1) manifest 完整性
const {verifyManifest} = await import(pathToFileURL(path.join(RELEASE, 'deployment/home.mjs')));
const v = verifyManifest(RELEASE);
const declared = JSON.parse(fs.readFileSync(path.join(RELEASE, 'manifest.json'), 'utf8')).files.length;
res.manifest = {files: v.files.length, declared, ok: v.files.length === EXPECTED_FILES && declared === EXPECTED_FILES};
if (EXPECT_MANIFEST_SHA) {
  const crypto = await import('node:crypto');
  const cur = crypto.createHash('sha256').update(fs.readFileSync(path.join(RELEASE, 'manifest.json'))).digest('hex');
  res.manifest.expectedSha = cur === EXPECT_MANIFEST_SHA;
}

// 2) client 只读回读（pwsh 必须能在 PATH 里找到：该程序自带 tools/pwsh7）
const env = {...process.env, PATH: `${path.join(ROOT, 'tools/pwsh7')}${path.delimiter}${process.env.PATH || ''}`};
const cli = spawnSync(NODE24, [path.join(RELEASE, CLIENT), CLIENT_OP], {encoding: 'utf8', windowsHide: true, timeout: 45000, env});
let payload = null; try { payload = JSON.parse(cli.stdout); } catch {}
fs.writeFileSync(path.join(OUT, `${CLIENT_OP}-readback.json`), JSON.stringify(payload, null, 1), 'utf8');
res.clientReadback = {
  rc: cli.status, parseOk: Array.isArray(payload), count: Array.isArray(payload) ? payload.length : null,
  ids: Array.isArray(payload) ? payload.map(x => x?.id) : null,
  stderrPresent: !!(cli.stderr || '').trim(),   // 内容不入结果：可能含凭据
  pwshHint: /PowerShell 7 is required/.test(cli.stderr || '') ? 'PATH 缺 tools/pwsh7' : undefined,
};

// 3) 内存严格类型探针（不落库）
const {emptyState, mutate, DomainError} = await import(pathToFileURL(path.join(RELEASE, 'runtime/lib/domain.ts')));
const s = emptyState();
const attempt = ([label, action, body]) => {
  try { mutate(s, action, body); return {case: label, threw: false}; }
  catch (e) { return {case: label, threw: true, isDomainError: e instanceof DomainError || e?.name === 'DomainError', status: e?.status, message: String(e?.message || '').slice(0, 60)}; }
};
res.strictType = STRICT_PROBES.map(attempt);
res.strictTypeAll400 = res.strictType.every(x => x.threw && x.isDomainError && x.status === 400);
res.settingsUntouched = JSON.stringify(s.settings) === JSON.stringify(emptyState().settings);

fs.writeFileSync(path.join(OUT, 'verify-result.json'), JSON.stringify(res, null, 1), 'utf8');
console.log(JSON.stringify(res, null, 1));
