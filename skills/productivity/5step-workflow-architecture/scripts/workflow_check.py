#!/usr/bin/env python3
"""workflow_check.py — P2 自动打勾脚本。见 SKILL.md 或脚本内 docstring。"""
import argparse, os, sys, time
from pathlib import Path

def _hermes_home():
    env = os.environ.get("HERMES_HOME")
    if env: return Path(env)
    return Path.home() / "AppData" / "Local" / "hermes"

CONTRACTS = _hermes_home() / "contracts"
STALE = 86400

def find_active():
    if not CONTRACTS.exists(): return None
    best, best_mtime = None, 0
    for p in CONTRACTS.glob("workflow_*.md"):
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True); ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()
    wf = find_active()
    if not wf: print("[workflow_check] 无活跃追踪文件", file=sys.stderr); sys.exit(0)
    ok = check_step(wf, args.step)
    if not ok: sys.exit(1)
    if args.delete:
        text = wf.read_text(encoding="utf-8")
        if "- [ ]" not in text: wf.unlink(); print(f"[workflow_check] 🗑 {wf.name}")

if __name__ == "__main__": main()
