#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_opencode_key_consistency.py — OpenCode Go key 一致性核查（换 key 后必跑）

为什么需要它：2026-10-18 实踩。用户把新 key 存成了**新文件**，旧文件留着；
我只改了 .env + config.yaml，主链路转绿了，但**健康检查脚本每 30 分钟假报一次 401**
——因为 5 个脚本硬编码读的是一个固定的桌面 key 文件，不读环境变量。
当时只能逐条手敲命令去比对，所以沉淀成脚本。

它比对 4 个来源，任何一个还是旧 key 就会报出来：
  ① .env                      → OPENCODE_GO_API_KEY          （Hermes 主链路 + 3 个从 config 读 key 的脚本）
  ② config.yaml               → opencode-go-anthropic 内联 api_key
  ③ 硬编码桌面 key 文件的脚本 （不读环境变量，必须单独换）
  ④ 运行中的 gateway 进程环境  （.env 改动靠下一次 cron tick 热重载）

用法：
  python check_opencode_key_consistency.py                 # 用 .env 里的 key 当基准
  python check_opencode_key_consistency.py --key-file <路径>  # 用别的文件当基准（如用户新存的那份）

退出码：0 = 全部一致；1 = 有不一致（已打印逐项修复提示）
"""
import argparse
import io
import os
import re
import sys
from pathlib import Path

HERMES = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "hermes"
ENV_FILE = HERMES / ".env"
CFG_FILE = HERMES / "config.yaml"

# 硬编码桌面 key 文件的脚本（2026-10-18 实测清单；换 key 时这 5 个最容易被漏掉）
HARDCODED_SCRIPTS = [
    "scripts/api_healthcheck.py",
    "scripts/api_probe.py",
    "skills/research/model-subscription-evaluation/scripts/model_probe.py",
    "skills/video-understand-core/scripts/pipeline.py",
    "skills/video-understand-core/scripts/quick_summary.py",
]


def read_env_key() -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("OPENCODE_GO_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def mask(k: str) -> str:
    return f"{k[:10]}...{k[-4:]} (len={len(k)})" if len(k) > 16 else f"<{len(k)} chars>"


def scan_hardcoded_paths() -> dict:
    """返回 {脚本相对路径: 它硬编码的 key 文件绝对路径}"""
    out = {}
    for rel in HARDCODED_SCRIPTS:
        p = HERMES / rel
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'''([A-Za-z]:[\\/][^\n"']*?(?:api\s*key|key)[^\n"']*?\.txt)''', txt, re.I)
        if m:
            out[rel] = m.group(1).replace("\\\\", "\\")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-file", help="以这个文件的内容当基准 key（默认读 .env 的 OPENCODE_GO_API_KEY）")
    args = ap.parse_args()

    if args.key_file:
        ref = Path(args.key_file).read_text(encoding="utf-8", errors="replace").strip().strip('"').strip("'")
        ref_src = args.key_file
    else:
        ref = read_env_key()
        ref_src = str(ENV_FILE)

    if not ref:
        print(f"✗ 基准 key 为空（来源 {ref_src}）——先确认该文件里有 key")
        return 1

    print(f"基准 key: {mask(ref)}")
    print(f"来源    : {ref_src}")
    print("=" * 68)
    bad = 0

    # ① .env
    env_key = read_env_key()
    ok = env_key == ref
    print(f"① .env OPENCODE_GO_API_KEY          {'一致 ✓' if ok else '不一致 ✗ ' + mask(env_key)}")
    bad += 0 if ok else 1

    # ② config.yaml（opencode-go-anthropic 内联 api_key）
    if CFG_FILE.exists():
        cfg = CFG_FILE.read_text(encoding="utf-8", errors="replace")
        keys = re.findall(r"^\s*api_key:\s*['\"]?([^'\"\n#]+)", cfg, re.M)
        mism = [k.strip() for k in keys if k.strip().startswith(("oc_sk_", "sk-")) and k.strip() != ref]
        if not mism:
            print("② config.yaml 内联 api_key         一致 ✓")
        else:
            print(f"② config.yaml 内联 api_key         ✗ 有 {len(mism)} 处不是新 key: {[mask(m) for m in mism]}")
            bad += 1
    else:
        print("② config.yaml                      (不存在，跳过)")

    # ③ 硬编码桌面 key 文件的脚本
    scan = scan_hardcoded_paths()
    if not scan:
        print("③ 硬编码脚本                        (未匹配到，可能本机路径格式不同)")
    else:
        seen = {}
        for rel, kf in scan.items():
            seen.setdefault(kf, []).append(rel)
        for kf, scripts in seen.items():
            try:
                got = Path(kf).read_text(encoding="utf-8", errors="replace").strip().strip('"').strip("'")
            except Exception as e:
                print(f"③ ✗ 读不到 key 文件: {kf} ({e})")
                bad += 1
                continue
            ok = got == ref
            tag = "一致 ✓" if ok else f"不一致 ✗ 该文件里是 {mask(got)}"
            print(f"③ 桌面 key 文件 {tag}")
            print(f"    路径  : {kf}")
            print(f"    使用者: {', '.join(scripts)}")
            if not ok:
                bad += 1
                print("    → 这 5 个脚本读的是**这个文件**、不读环境变量；把新 key 写进去它们就全部转绿：")
                print(f"       python -c \"open(r'{kf}','w',encoding='utf-8').write(open(r'{ref_src}',encoding='utf-8').read().strip())\"")

    # ④ 运行中的进程环境
    try:
        import psutil
        states = {}
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cl = " ".join(p.info["cmdline"] or [])
                if "hermes_cli.main" not in cl:
                    continue
                v = p.environ().get("OPENCODE_GO_API_KEY")
                st = "新KEY ✓" if v == ref else ("未设置" if not v else "旧KEY ✗")
                role = "gateway" if "gateway run" in cl else ("serve" if " serve " in cl else "?")
                states[(p.info["pid"], role, st)] = True
            except Exception:
                pass
        if not states:
            print("④ 进程环境                          (没找到 hermes_cli.main 进程)")
        else:
            for (pid, role, st) in sorted(states):
                print(f"④ PID {pid:<7} {role:<9} {st}")
            print("    注：`.env` 改动靠**下一次 cron tick 热重载**（no_agent 脚本任务也算），")
            print("        不必重启 gateway；要立刻生效就跑任一 job：cronjob(action='run', job_id=<id>)")
    except ImportError:
        print("④ 进程环境                          (psutil 不可用，跳过)")

    print("=" * 68)
    if bad:
        print(f"✗ 有 {bad} 处不一致 —— 按上面提示改完再跑一次")
        return 1
    print("✓ 四个来源完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
