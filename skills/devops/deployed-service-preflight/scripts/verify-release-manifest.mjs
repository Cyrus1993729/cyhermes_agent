// 校验活动 release 的 manifest 完整性（不写盘、不联网、不输出正文）
// 用法: "<root>/tools/node24/node.exe" verify-release-manifest.mjs [releaseDir]
// 默认取 DayflowHome 家主机活动 release；换项目改 RELEASE 常量或在参数里给目录。
import {pathToFileURL} from 'node:url';

const RELEASE = process.argv[2]
  || 'C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1';

const {verifyManifest} = await import(pathToFileURL(RELEASE + '/deployment/home.mjs'));
try {
  const r = verifyManifest(RELEASE);
  console.log(JSON.stringify({ok: true, bundleId: r.bundleId, files: r.files.length, verified: r.verified}));
} catch (e) {
  console.log(JSON.stringify({ok: false, error: String(e.message)}));
  process.exitCode = 1;
}
