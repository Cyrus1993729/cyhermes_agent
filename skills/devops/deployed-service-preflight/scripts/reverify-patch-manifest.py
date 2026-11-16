"""Read-only reverify of an installed patch: manifest-to-manifest diff + independent proofs.

No writes, no network, no model calls. Prints one desensitized JSON blob.

Usage:
  python reverify-patch-manifest.py --release <releaseDir> --backup-manifest <backup/manifest.json>
      [--expect rel/path=<sha256>]... [--old-skill <backup/SKILL.md> --skill <current/SKILL.md>]
      [--install-write-utc 2026-11-04T07:10:40Z] [--marker DAYFLOW-XXX-]
      [--private <name>]...

Defaults are tuned for the Dayflow home host (release/runtime/.local private configs).
"""
import argparse, datetime, hashlib, json, os, sys


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def iso_z(ts):
    return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--backup-manifest", required=True)
    ap.add_argument("--expect", action="append", default=[], help="rel/path=sha256")
    ap.add_argument("--old-skill")
    ap.add_argument("--skill")
    ap.add_argument("--marker")
    ap.add_argument("--install-write-utc", help="ISO8601 Z of the install write moment")
    ap.add_argument("--private", action="append", default=[])
    ap.add_argument("--pretty", action="store_true")
    a = ap.parse_args()

    rel = os.path.abspath(a.release)
    cur_p = os.path.join(rel, "manifest.json")
    old = json.load(open(a.backup_manifest, encoding="utf-8"))
    cur = json.load(open(cur_p, encoding="utf-8"))
    out = {"mode": "readonly"}

    # ---- files[] diff, all fields per entry ----
    of = {f["path"]: f for f in old.get("files", [])}
    cf = {f["path"]: f for f in cur.get("files", [])}
    changed = []
    for p, e in of.items():
        n = cf.get(p)
        if n is None:
            changed.append({"path": p, "kind": "missing_in_current"})
            continue
        if json.dumps(e, sort_keys=True) != json.dumps(n, sort_keys=True):
            changed.append({
                "path": p, "kind": "changed",
                "bytes": {"old": e.get("bytes"), "new": n.get("bytes")},
                "sha256": {"old": (e.get("sha256") or "")[:12] + "\u2026",
                           "new": (n.get("sha256") or "")[:12] + "\u2026"},
            })
    ch_paths = {c["path"] for c in changed}
    same = [p for p in of if p in cf and p not in ch_paths]
    out["filesDiff"] = {
        "oldCount": len(of), "newCount": len(cf),
        "changedCount": len(changed), "changed": changed,
        "addedPaths": [p for p in cf if p not in of],
        "unchangedCount": len(same),
        "unchangedVerifiedItemByItem": True,
        "unchangedCompareScope": "path+bytes+sha256, all fields compared per entry",
    }

    # ---- top-level fields ----
    oldk, newk = set(old), set(cur)
    out["topLevelFields"] = {
        "oldFieldCount": len(oldk),
        "preservedIdentical": sorted(k for k in oldk & newk if k != "files" and old[k] == cur[k]),
        "presentButDifferent": sorted(k for k in oldk & newk if k != "files" and old[k] != cur[k]),
        "missingInCurrent": sorted(oldk - newk),
        "addedOnly": sorted(newk - oldk),
    }
    for k in sorted(newk - oldk):
        out["topLevelFields"]["added_" + k] = cur[k]

    out["manifestSha256SelfCalculated"] = sha256(cur_p)

    # ---- independent hashes of expected files ----
    exp = {}
    for item in a.expect:
        k, _, v = item.partition("=")
        exp[k] = v
    if exp:
        res = {}
        for k, v in exp.items():
            p = os.path.join(rel, k.replace("/", os.sep))
            ok = os.path.exists(p)
            h = sha256(p) if ok else None
            res[k] = {"exists": ok, "computed": h, "match": h == v,
                      "bytes": os.path.getsize(p) if ok else None,
                      "manifestEntryAgrees": (cf.get(k, {}).get("sha256") == h) if ok else False}
        out["independentHash"] = res

    # ---- private configs: mtime evidence only (never内容/哈希列表) ----
    local = os.path.join(rel, "runtime", ".local")
    names = a.private or ["hermes-cloud-connection.json", "calendar-automation.json",
                          "home-deployment.json", "home-enabled.json",
                          "cutover-permit.json", "home-preflight.json"]
    cands = [os.path.join(local, n) for n in names]
    la = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    cands += [os.path.join(la, "hermes", "config.yaml"),
              os.path.join(os.path.expanduser("~"), ".hermes", "config.yaml")]
    if os.environ.get("HERMES_HOME"):
        cands.append(os.path.join(os.environ["HERMES_HOME"], "config.yaml"))

    # install write moment: explicit, else newest mtime among changed files
    if a.install_write_utc:
        cut = datetime.datetime.strptime(a.install_write_utc.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    else:
        ts = [os.stat(os.path.join(rel, c["path"].replace("/", os.sep))).st_mtime
              for c in changed if os.path.exists(os.path.join(rel, c["path"].replace("/", os.sep)))]
        cut = datetime.datetime.utcfromtimestamp(max(ts)) if ts else datetime.datetime.utcnow()

    rows, existing, older = [], 0, True
    for p in dict.fromkeys(cands):
        if not os.path.exists(p):
            continue
        existing += 1
        m = datetime.datetime.utcfromtimestamp(os.stat(p).st_mtime)
        older = older and (m < cut)
        rows.append({"name": os.path.basename(p), "mtimeZ": m.isoformat() + "Z"})
    out["privateConfig"] = {
        "candidatesProbed": len(dict.fromkeys(cands)), "filesCompared": existing,
        "installWriteZ": cut.isoformat() + "Z",
        "allMtimeBeforeInstallWrite": older, "unchanged": older,
        "newestPrivateMtimeZ": max((r["mtimeZ"] for r in rows), default=None),
    }

    # ---- skill personalization prefix (byte level) ----
    if a.old_skill and a.skill and os.path.exists(a.old_skill) and os.path.exists(a.skill):
        ob = open(a.old_skill, "rb").read()
        nb = open(a.skill, "rb").read()
        nt = nb.decode("utf-8", "replace")
        info = {"bytes": {"before": len(ob), "after": len(nb)},
                "personalizationPrefixPreservedByteExact": nb[:len(ob)] == ob,
                "yamlNameLine": next((l for l in nt.splitlines()[:8] if l.startswith("name:")), None),
                "mtimeZ": iso_z(os.stat(a.skill).st_mtime)}
        if a.marker:
            info["marker"] = a.marker
            info["markerOccurrences"] = nt.count(a.marker)
        out["hermesSkill"] = info

    out["sideEffects"] = {"filesWritten": 0, "taskModified": False,
                         "networkCalls": 0, "messagesSent": 0, "installRerun": False}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1 if a.pretty else None)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
