#!/usr/bin/env python3
"""workflow_check.py — P2 自动打勾脚本 + 新流程双审验证。"""
import argparse, json, os, sys, time
from pathlib import Path

def _hermes_home():
    env = os.environ.get("HERMES_HOME")
    if env: return Path(env)
    return Path.home() / "AppData" / "Local" / "hermes"

CONTRACTS = _hermes_home() / "contracts"
REVIEWS = _hermes_home() / "reviews"
STALE = 86400

# === Legacy mode (unchanged) ===

def find_active(pattern="workflow_*.md"):
    if not CONTRACTS.exists(): return None
    best, best_mtime = None, 0
    for p in CONTRACTS.glob(pattern):
        if time.time() - p.stat().st_mtime > STALE: continue
        if p.stat().st_mtime > best_mtime: best, best_mtime = p, p.stat().st_mtime
    return best

def check_step(wf_path, step_marker):
    text = wf_path.read_text(encoding="utf-8")
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]") and step_marker in stripped:
            text = text.replace(line, line.replace("- [ ]", "- [x]", 1), 1)
            wf_path.write_text(text, encoding="utf-8")
            print(f"[workflow_check] ✅ 已打勾: {stripped}")
            return True
    print(f"[workflow_check] ❌ 未找到含 '{step_marker}' 的未勾步骤", file=sys.stderr)
    return False

# === Dual mode ===

def load_json(path):
    """Load JSON from file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def grounding_check(codex_path, opus_path, deliverable_path):
    """三模式接地校验。"""
    codex = load_json(codex_path)
    opus = load_json(opus_path)
    all_findings = codex.get("findings", []) + opus.get("findings", [])

    grounded = []
    ungrounded = []

    for f in all_findings:
        g = f.get("grounding", {})
        gtype = g.get("type", "")
        if not gtype:
            ungrounded.append(f)
            continue

        if gtype == "present_text":
            quote = g.get("present_text", {}).get("locator", {}).get("quote", "")
            # Simple check: quote present in deliverable
            if deliverable_path:
                text = Path(deliverable_path).read_text(encoding="utf-8")
                # Exact match
                if quote in text:
                    grounded.append(f)
                else:
                    # Fuzzy: strip spaces and punctuation
                    import re
                    clean_q = re.sub(r'\s+', '', quote)
                    clean_t = re.sub(r'\s+', '', text)
                    if clean_q in clean_t:
                        f["_fuzzy_match"] = True
                        grounded.append(f)
                    else:
                        f["_unground_reason"] = "quote_not_found"
                        ungrounded.append(f)
            else:
                grounded.append(f)  # No deliverable to check against, assume valid

        elif gtype == "omission":
            expected_ref = g.get("omission", {}).get("expected_from", {}).get("ref", "")
            if expected_ref:
                grounded.append(f)
            else:
                f["_unground_reason"] = "no_contract_ref"
                ungrounded.append(f)

        elif gtype == "external_evidence":
            version = g.get("external_evidence", {}).get("version", "")
            if version:
                grounded.append(f)
            else:
                f["_unground_reason"] = "no_version"
                ungrounded.append(f)

    # Process ungrounded
    for f in ungrounded:
        sev = f.get("severity", "low")
        f["confidence"] = "low"  # Only lower confidence, not severity
        if sev in ("critical", "high"):
            f["_requires_human_review"] = True

    return {
        "grounded_count": len(grounded),
        "ungrounded_count": len(ungrounded),
        "grounded": grounded,
        "ungrounded": ungrounded
    }

def oscillation_check(history_dir, current_findings, round_num):
    """双模震荡检测：停滞+回环。"""
    # Build current fingerprint
    current_fp = set()
    for f in current_findings:
        dim = f.get("dimension", "")
        claim = f.get("claim", "")[:50]
        current_fp.add(f"{dim}:{claim}")

    # Check stagnation (相邻轮)
    if round_num > 1:
        prev_path = Path(history_dir) / f"merged-r{round_num-1}.json"
        if prev_path.exists():
            prev = load_json(prev_path)
            prev_fp = set()
            for f in prev.get("findings", []):
                dim = f.get("dimension", "")
                claim = f.get("claim", "")[:50]
                prev_fp.add(f"{dim}:{claim}")

            if current_fp and prev_fp:
                overlap = len(current_fp & prev_fp) / max(len(current_fp | prev_fp), 1)
                if overlap > 0.8:
                    return {"oscillation": True, "type": "stagnation", "overlap": overlap}

    # Check loopback (任一历史轮)
    for r in range(1, round_num):
        hist_path = Path(history_dir) / f"merged-r{r}.json"
        if hist_path.exists():
            hist = load_json(hist_path)
            hist_fp = set()
            for f in hist.get("findings", []):
                dim = f.get("dimension", "")
                claim = f.get("claim", "")[:50]
                hist_fp.add(f"{dim}:{claim}")

            if current_fp and hist_fp:
                overlap = len(current_fp & hist_fp) / max(len(current_fp | hist_fp), 1)
                if overlap > 0.8:
                    return {"oscillation": True, "type": "loopback", "round": r, "overlap": overlap}

    return {"oscillation": False}

def verify_pass_gate(findings):
    """统一通过门禁。"""
    has_grounded_critical = False
    has_grounded_high = False
    has_unresolved_critical_high = False

    for f in findings:
        sev = f.get("severity", "")
        grounded = f.get("_unground_reason") is None or f.get("_unground_reason") == ""
        if sev == "critical" and grounded:
            has_grounded_critical = True
        if sev == "high" and grounded:
            has_grounded_high = True
        if sev in ("critical", "high") and f.get("_status") != "resolved":
            has_unresolved_critical_high = True

    if has_grounded_critical:
        return 20  # REPAIR_REQUIRED
    if has_unresolved_critical_high:
        return 20  # REPAIR_REQUIRED
    if has_grounded_high:
        return 20  # REPAIR_REQUIRED (除非已修复+重审——调用方判断)

    # Check for any findings at all
    if not findings:
        return 0  # PASS
    return 10  # PASS_WITH_NOTES

# === Main ===

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="legacy", choices=["legacy", "dual"])
    ap.add_argument("--step", required=True)
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--codex", help="Codex review JSON path")
    ap.add_argument("--opus", help="Opus review JSON path")
    ap.add_argument("--deliverable", help="Deliverable path for grounding")
    ap.add_argument("--history-dir", help="Review history directory")
    ap.add_argument("--round", type=int, default=0, help="Current repair round")
    args = ap.parse_args()

    if args.mode == "legacy":
        # Original logic - unchanged
        wf = find_active("workflow_*.md")
        # Exclude v2 files
        wf = find_active("workflow_[!v]*.md") or find_active("workflow_*.md")
        if not wf:
            print("[workflow_check] 无活跃追踪文件", file=sys.stderr)
            sys.exit(0)
        ok = check_step(wf, args.step)
        if not ok: sys.exit(1)
        if args.delete:
            text = wf.read_text(encoding="utf-8")
            if "- [ ]" not in text:
                wf.unlink()
                print(f"[workflow_check] 🗑 {wf.name}")

    elif args.mode == "dual":
        if args.step == "ground":
            if not args.codex or not args.opus:
                print("[workflow_check] dual ground need --codex and --opus", file=sys.stderr)
                sys.exit(1)
            result = grounding_check(args.codex, args.opus, args.deliverable)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.step == "oscillation":
            if not args.history_dir or not args.codex:
                print("[workflow_check] dual oscillation need --history-dir and --codex", file=sys.stderr)
                sys.exit(1)
            current = load_json(args.codex)
            result = oscillation_check(args.history_dir, current.get("findings", []), args.round)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.step == "verify":
            if not args.codex:
                print("[workflow_check] dual verify need --codex", file=sys.stderr)
                sys.exit(1)
            findings = load_json(args.codex).get("findings", [])
            code = verify_pass_gate(findings)
            print(json.dumps({"status_code": code}, ensure_ascii=False))
            sys.exit(0 if code == 0 else 1)

        elif args.step == "wrap":
            wf = find_active("workflow_v2_*.md")
            if not wf:
                print("[workflow_check] 无活跃v2追踪文件", file=sys.stderr)
                sys.exit(0)
            ok = check_step(wf, args.step)
            if not ok: sys.exit(1)
            if args.delete:
                text = wf.read_text(encoding="utf-8")
                if "- [ ]" not in text:
                    wf.unlink()
                    print(f"[workflow_check] 🗑 {wf.name}")

if __name__ == "__main__": main()
