#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本化安装目录（releases/x.y + patches/）的 manifest 只读校验器。

不写文件、不联网、不打印文件内容，输出可直接贴进交付/A2A 回执。

用法：
  python verify_manifest.py verify <manifest.json> <校验根目录>
  python verify_manifest.py diff   <manifestA> <manifestB>
  python verify_manifest.py triage <AppHome>     # 根 / release / 补丁包 三层一次体检

判读口诀：release 校验全通过 + 根 == patch.json.oldManifestSHA256
          => 补丁已落地、根基线未回写（不是损坏）。
"""
import hashlib
import json
import os
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify(manifest_path, base_dir):
    mani = load(manifest_path)
    files = mani.get("files", [])
    ok = mismatch = missing = 0
    bads = []
    mapping = {}
    for entry in files:
        rel = entry["path"]
        mapping[rel] = entry.get("sha256")
        target = os.path.join(base_dir, rel)
        if not os.path.exists(target):
            missing += 1
            bads.append(("MISSING", rel))
            continue
        if sha256(target) == entry.get("sha256"):
            ok += 1
        else:
            mismatch += 1
            bads.append(("MISMATCH", rel))
    print("[verify] %s" % manifest_path)
    print("         files=%d ok=%d mismatch=%d missing=%d" % (len(files), ok, mismatch, missing))
    print("         manifest_sha256=%s" % sha256(manifest_path))
    print("         base=%s" % base_dir)
    for kind, rel in bads[:20]:
        print("         %s %s" % (kind, rel))
    return ok, mismatch, missing, mapping


def diff(a_path, b_path):
    ma = {f["path"]: f.get("sha256") for f in load(a_path)["files"]}
    mb = {f["path"]: f.get("sha256") for f in load(b_path)["files"]}
    only_a = sorted(set(ma) - set(mb))
    only_b = sorted(set(mb) - set(ma))
    changed = sorted(p for p in set(ma) & set(mb) if ma[p] != mb[p])
    print("[diff] A=%s n=%d  B=%s n=%d" % (a_path, len(ma), b_path, len(mb)))
    print("       only_in_A=%d %s" % (len(only_a), only_a[:10]))
    print("       only_in_B=%d %s" % (len(only_b), only_b[:10]))
    print("       hash_changed=%d %s" % (len(changed), changed[:10]))
    return only_a, only_b, changed


def triage(app_home):
    root_m = os.path.join(app_home, "manifest.json")
    root_mani = load(root_m)
    bundle = root_mani.get("bundleId")
    rel_dir = os.path.join(app_home, "releases", bundle)
    rel_m = os.path.join(rel_dir, "manifest.json")
    print("bundleId=%s formatVersion=%s" % (bundle, root_mani.get("formatVersion")))
    print("root sourceCommit=%s siteVersion=%s" % (root_mani.get("sourceCommit"), root_mani.get("sourceSiteVersion")))
    print("")
    verify(root_m, app_home)
    print("")
    if not os.path.exists(rel_m):
        print("[warn] release manifest 不存在: %s" % rel_m)
        return
    verify(rel_m, rel_dir)
    print("")
    patch_root = os.path.join(app_home, "patches")
    if not os.path.isdir(patch_root):
        return
    for name in sorted(os.listdir(patch_root)):
        pm = os.path.join(patch_root, name, "extracted", "manifest.json")
        pj = os.path.join(patch_root, name, "extracted", "patch.json")
        if not os.path.exists(pm):
            continue
        print("--- patch: %s ---" % name)
        if os.path.exists(pj):
            meta = load(pj)
            print("    patchId=%s" % meta.get("patchId"))
            print("    old=%s" % meta.get("oldManifestSHA256"))
            print("    new=%s" % meta.get("newManifestSHA256"))
            print("    changes=%s" % [c.get("path") for c in meta.get("changes", [])])
            print("    根 == oldManifest? %s" % (sha256(root_m) == meta.get("oldManifestSHA256")))
            print("    release == newManifest? %s" % (sha256(rel_m) == meta.get("newManifestSHA256")))
        verify(pm, app_home)
        print("")
        diff(rel_m, pm)
    print("判读：release 全通过 + 根 == oldManifest => 补丁已落地、根基线未回写（非损坏）。")
    print("      增量包需含「根 manifest 回写对齐」。")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "verify" and len(argv) >= 4:
        verify(argv[2], argv[3])
    elif cmd == "diff" and len(argv) >= 4:
        diff(argv[2], argv[3])
    elif cmd == "triage" and len(argv) >= 3:
        triage(argv[2])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
