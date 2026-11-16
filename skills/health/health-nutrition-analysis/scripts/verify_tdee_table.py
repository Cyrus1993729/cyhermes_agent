#!/usr/bin/env python3
"""校验 `references/tdee-deficit-calibration.md` 里的敏感性表与算式自洽。

2026-10-30 实踩：该表原版把 MET 3.0 当**满额**算，而同文件的算式行写的是
`净增 = (MET−1) × 体重 × 时长`，且 10-28 实测锚点（13000 步 → +274.7）用的是净增量。
结果表中 5000/7000/9000 三行**虚高 1.5 倍**，并已污染过一次对用户的报告。

本脚本把每一行从公式重算一遍，对不上就非零退出。
**凡是「公式 + 数字表」并存的参考文件，改完都该跑一次这类核对。**

用法：
    python verify_tdee_table.py [--file <path-to-calibration.md>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --- 校准常量（改口径时同步改这里） ---
WEIGHT_KG = 80.8          # 体重
BMR = 1759.0              # Mifflin-St Jeor
PAL = 1.25                # 久坐办公
STEP_M = 0.68             # 步行步幅 m/步
SPEED_KMH = 4.0           # 慢走速度
WALK_MET = 3.0            # 步行 MET
WALK_NET_MET = WALK_MET - 1.0   # 净增量口径：MET − 1
INTAKE = 1961.65          # 表内赤字所依据的摄入（10-29）
TOL = 0.6                 # 允差（表中保留 1 位小数）

BASE_TDEE = BMR * PAL


def expected(incr_steps: float) -> tuple[float, float, float]:
    """由增量步数推出 (净增, TDEE, 赤字)，全部净增量口径。"""
    km = incr_steps * STEP_M / 1000.0
    hours = km / SPEED_KMH
    net = WALK_NET_MET * WEIGHT_KG * hours
    tdee = BASE_TDEE + net
    return net, tdee, tdee - INTAKE


def parse_rows(md: str) -> list[tuple[int, float, float, float, float]]:
    rows = []
    for line in md.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip().replace("**", "") for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        try:
            steps = int(re.sub(r"[^0-9]", "", cells[0]))
            incr, net, tdee, deficit = (float(c) for c in cells[1:5])
        except (ValueError, TypeError):
            continue  # 表头 / 分隔行
        rows.append((steps, incr, net, tdee, deficit))
    return rows


def main() -> int:
    default = Path(__file__).resolve().parent.parent / "references" / "tdee-deficit-calibration.md"
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(default))
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"FAIL 找不到文件：{path}")
        return 2

    rows = parse_rows(path.read_text(encoding="utf-8"))
    if not rows:
        print("FAIL 没解析到敏感性表行（表格格式变了？）")
        return 2

    print(f"基线 TDEE = {BMR} × {PAL} = {BASE_TDEE:.2f}")
    print(f"每 1000 增量步 = {1000 * STEP_M / 1000 / SPEED_KMH:.2f} h "
          f"→ {WALK_NET_MET * WEIGHT_KG * (1000 * STEP_M / 1000 / SPEED_KMH):.2f} 卡")
    print()

    bad = 0
    for steps, incr, net, tdee, deficit in rows:
        e_net, e_tdee, e_def = expected(incr)
        ok = abs(e_net - net) < TOL and abs(e_tdee - tdee) < TOL and abs(e_def - deficit) < TOL
        bad += 0 if ok else 1
        flag = "OK " if ok else "BAD"
        print(f"[{flag}] {steps:>6}步 增量{incr:>6.0f} | "
              f"净增 {net:>7.1f}(算 {e_net:>7.1f}) | "
              f"TDEE {tdee:>8.1f}(算 {e_tdee:>8.1f}) | "
              f"赤字 {deficit:>6.1f}(算 {e_def:>6.1f})")

    # 锚点：10-28 实测 13000 步 → +274.7（档案已记）
    anchor = next((r for r in rows if r[0] == 13000), None)
    if anchor:
        if abs(anchor[2] - 274.7) < 0.5:
            print("\n锚点 OK：13000 步净增 274.7 与 10-28 档案一致")
        else:
            print(f"\n锚点 BAD：13000 步应约 274.7，表中 {anchor[2]}（口径可能被改回满额）")
            bad += 1

    print()
    if bad:
        print(f"FAIL {bad} 行与净增量公式不符——表与算式已失去自洽，先修表再引用。")
        return 1
    print(f"PASS {len(rows)} 行全部与 (MET−1)×体重×时长 自洽")
    return 0


if __name__ == "__main__":
    sys.exit(main())
