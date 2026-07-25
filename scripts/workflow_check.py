#!/usr/bin/env python3
"""workflow_check.py — P2 自动打勾脚本。

每个 5 步流程 skill 完成时调用此脚本，自动把追踪文件的对应步骤打勾。
Agent 不再需要"记得去勾"——做了，勾就有了。

用法：
  python workflow_check.py --step "①"
  python workflow_check.py --step "④"
  python workflow_check.py --step "⑤" --delete

匹配规则：--step 传入圈码（如 ①、④），脚本在追踪文件中找
"- [ ] ①" 这样的行并替换为 "- [x] ①"。不依赖完整标签文本。
"""

import argparse, os, sys, time
from pathlib import Path


def _hermes_home():
    """Resolve hermes home — same logic as workflow-tracker plugin."""
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    return Path.home() / "AppData" / "Local" / "hermes"


CONTRACTS = _hermes_home() / "contracts"
STALE = 86400


def find_active():
    if not CONTRACTS.exists():
        return None
    best = None
    best_mtime = 0
    for p in CONTRACTS.glob("workflow_*.md"):
        if time.time() - p.stat().st_mtime > STALE:
            continue
        if p.stat().st_mtime > best_mtime:
            best = p
            best_mtime = p.stat().st_mtime
    return best


def check_step(wf_path, step_marker):
    """Replace the first unchecked line containing the step marker.

    Matches lines like "- [ ] ① ..." and replaces with "- [x] ① ...".
    step_marker is e.g. "①", "④".
    """
    text = wf_path.read_text(encoding="utf-8")
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]") and step_marker in stripped:
            old = line
            new = line.replace("- [ ]", "- [x]", 1)
            text = text.replace(old, new, 1)
            wf_path.write_text(text, encoding="utf-8")
            print(f"[workflow_check] ✅ 已打勾: {stripped}")
            return True

    print(f"[workflow_check] ❌ 未找到含 '{step_marker}' 的未勾步骤", file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    help='圈码，如 ① / ④ / ⑤')
    ap.add_argument("--delete", action="store_true",
                    help="打勾后若全部完成则删除追踪文件")
    args = ap.parse_args()

    wf = find_active()
    if not wf:
        print("[workflow_check] 无活跃追踪文件，跳过", file=sys.stderr)
        sys.exit(0)  # No file = not an error, nothing to do.

    ok = check_step(wf, args.step)
    if not ok:
        sys.exit(1)  # Step not found → signal failure.

    if args.delete:
        text = wf.read_text(encoding="utf-8")
        if "- [ ]" not in text:
            wf.unlink()
            print(f"[workflow_check] 🗑 全部完成，已删除追踪文件: {wf.name}")
        else:
            print("[workflow_check] ⚠ 仍有未完成步骤，跳过删除", file=sys.stderr)


if __name__ == "__main__":
    main()
