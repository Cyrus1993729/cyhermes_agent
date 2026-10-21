#!/usr/bin/env python3
"""每日营养方案计算 + 用户报数校验。

用法:
  python macro_plan.py plan --weight 80 --bf 22.5 --age 33 --activity 1.55 --goal cut
  python macro_plan.py plan --weight 80 --bf 22.5 --age 33            # 打印全活动量对照表
  python macro_plan.py validate --kcal 910 --protein 98 --carbs 210 --fat 24 --weight 80

不依赖第三方库。
"""
import argparse
import sys

ACTIVITIES = {
    "1.2": "久坐 / 不练",
    "1.375": "轻活动 每周1-3练",
    "1.55": "中度 每周3-5练",
    "1.725": "高度 每周6-7练",
}

# goal -> (热量系数, 蛋白 g/kg, 脂肪 g/kg)
GOALS = {
    "cut": (0.82, 2.2, 0.9),
    "recomp": (1.00, 2.2, 0.9),
    "maintain": (1.00, 1.8, 0.9),
    "bulk": (1.12, 1.8, 1.0),
}

FAT_FLOOR_GKG = 0.6      # 安全下限
PROTEIN_FLOOR_GKG = 1.6  # 通用下限
MAX_WEEKLY_LOSS_PCT = 1.0


def compute_bmr(weight, bf_pct=None, age=None, height=None):
    """体脂已知 -> Katch-McArdle（不依赖身高）；否则 Mifflin-St Jeor。"""
    if bf_pct:
        lbm = weight * (1 - bf_pct / 100.0)
        return 370 + 21.6 * lbm, lbm, "Katch-McArdle"
    if not height or not age:
        sys.exit("没有体脂率时必须提供 --height 和 --age")
    return 10 * weight + 6.25 * height - 5 * age + 5, None, "Mifflin-St Jeor"


def macros_for(kcal, weight, p_gkg, f_gkg):
    p = weight * p_gkg
    f = weight * f_gkg
    c = (kcal - p * 4 - f * 9) / 4.0
    return p, f, c


def cmd_plan(a):
    bmr, lbm, formula = compute_bmr(a.weight, a.bf, a.age, a.height)
    print(f"体重 {a.weight}kg" + (f"  体脂 {a.bf}%  去脂体重 {lbm:.1f}kg  脂肪重 {a.weight - lbm:.1f}kg" if lbm else ""))
    print(f"BMR ({formula}) = {bmr:.0f} kcal")
    if not a.bf:
        print("  提示：没有体脂率 -> 退用 Mifflin；若能拿到体脂率，Katch-McArdle 更准且不需身高。")
    print()

    goal = a.goal
    kfac, p_gkg, f_gkg = GOALS[goal]

    acts = [(float(k), v) for k, v in ACTIVITIES.items()]
    if a.activity:
        acts = [(a.activity, "自定义")]

    print(f"目标 = {goal}（热量系数 {kfac}，蛋白 {p_gkg} g/kg，脂肪 {f_gkg} g/kg）")
    print(f"{'活动量':<20}{'TDEE':>8}{'目标热量':>10}{'蛋白':>8}{'脂肪':>7}{'碳水':>7}{'周减重':>9}")
    for factor, label in acts:
        tdee = bmr * factor
        kcal = tdee * kfac
        p, f, c = macros_for(kcal, a.weight, p_gkg, f_gkg)
        loss = (tdee - kcal) * 7 / 7700 if kfac < 1 else 0.0
        print(f"{label:<20}{tdee:>8.0f}{kcal:>10.0f}{p:>7.0f}g{f:>6.0f}g{c:>6.0f}g{loss:>8.2f}kg")
    print()

    print(f"  安全线：脂肪 >= {FAT_FLOOR_GKG * a.weight:.0f}g/天，蛋白 >= {PROTEIN_FLOOR_GKG * a.weight:.0f}g/天")
    print(f"          每周减重 <= {a.weight * MAX_WEEKLY_LOSS_PCT / 100.0:.2f}kg（体重的 1%）")

    if a.bf:
        lbm_ = a.weight * (1 - a.bf / 100.0)
        for target_bf in (18, 15, 12):
            if target_bf < a.bf:
                tw = lbm_ / (target_bf / 100.0)
                need = a.weight - tw
                print(f"  到 {target_bf}% 体脂（保 LBM 不变）：{tw:.1f}kg，需减脂 {need:.1f}kg"
                      f"  -> 每周 0.5kg 约需 {need / 0.5:.0f} 周")


def cmd_validate(a):
    stated_kcal = a.kcal
    P, C, F = a.protein, a.carbs, a.fat

    print("=== 1) 算术自检：宏量营养反算热量 ===")
    print(f"  蛋白 {P:.0f}g x 4 = {P * 4:.0f} kcal")
    print(f"  碳水 {C:.0f}g x 4 = {C * 4:.0f} kcal")
    print(f"  脂肪 {F:.0f}g x 9 = {F * 9:.0f} kcal")
    calc = P * 4 + C * 4 + F * 9
    print(f"  ----------------------")
    print(f"  合计 = {calc:.0f} kcal   自称 = {stated_kcal:.0f} kcal   差 = {calc - stated_kcal:+.0f}")

    if abs(calc - stated_kcal) <= max(20.0, stated_kcal * 0.05):
        print("  OK 自洽，可以拿来分析")
    else:
        print("  !! 不自洽 —— 不要直接分析，先定位哪一项是错的")
        implied_c = (stated_kcal - P * 4 - F * 9) / 4.0
        implied_p = (stated_kcal - C * 4 - F * 9) / 4.0
        implied_f = (stated_kcal - P * 4 - C * 4) / 9.0
        print(f"      若热量与「蛋白{P:.0f} / 脂肪{F:.0f}」都对 -> 碳水应为 {implied_c:.1f}g（现报 {C:.0f}g）")
        print(f"      若热量与「碳水{C:.0f} / 脂肪{F:.0f}」都对 -> 蛋白应为 {implied_p:.1f}g（现报 {P:.0f}g）")
        print(f"      若热量与「蛋白{P:.0f} / 碳水{C:.0f}」都对 -> 脂肪应为 {implied_f:.1f}g（现报 {F:.0f}g）")
        print("      把三个反推值跟『用户/App 自己描述的实物』比对，吻合的那组才是对的。")
    print()

    if a.weight:
        w = a.weight
        p_gkg, f_gkg = P / w, F / w
        print("=== 2) 安全线校验 ===")
        flag_p = "!! 低于通用下限 1.6" if p_gkg < PROTEIN_FLOOR_GKG else "OK"
        flag_f = "!! 低于安全下限 0.6" if f_gkg < FAT_FLOOR_GKG else "OK"
        print(f"  蛋白 {p_gkg:.2f} g/kg  {flag_p}（刷脂需 2.0-2.4 = {2.0 * w:.0f}-{2.4 * w:.0f}g）")
        print(f"  脂肪 {f_gkg:.2f} g/kg  {flag_f}（下限 {FAT_FLOOR_GKG * w:.0f}g，推荐 {0.9 * w:.0f}g）")
        print(f"  脂肪占热量 {F * 9 / max(calc, 1) * 100:.0f}%（推荐 25-30%）")
        print()

    if a.tdee:
        deficit = a.tdee - stated_kcal
        print("=== 3) 赤字与减重速度 ===")
        print(f"  TDEE {a.tdee:.0f} - 自称 {stated_kcal:.0f} = 赤字 {deficit:.0f} kcal/天")
        print(f"  只吃到 TDEE 的 {stated_kcal / a.tdee * 100:.0f}%")
        wk = deficit * 7 / 7700
        print(f"  折算周减重 {wk:.2f}kg")
        if a.weight:
            cap = a.weight * MAX_WEEKLY_LOSS_PCT / 100.0
            print(f"  安全上限 {cap:.2f}kg/周" + (f"  ->  超出 {wk / cap:.1f} 倍，多出部分基本是肌肉和水" if wk > cap else "  OK 在范围内"))


def main():
    ap = argparse.ArgumentParser(description="每日营养方案计算 + 报数校验")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("plan", help="算每日目标")
    p1.add_argument("--weight", type=float, required=True)
    p1.add_argument("--bf", type=float, default=None, help="体脂率百分数，如 22.5")
    p1.add_argument("--age", type=int, default=None)
    p1.add_argument("--height", type=float, default=None, help="cm；有体脂率时不需要")
    p1.add_argument("--activity", type=float, default=None, help="1.2 / 1.375 / 1.55 / 1.725；不给则打印全表")
    p1.add_argument("--goal", choices=list(GOALS), default="cut")
    p1.set_defaults(func=cmd_plan)

    p2 = sub.add_parser("validate", help="校验用户/App 报的摄入数据")
    p2.add_argument("--kcal", type=float, required=True)
    p2.add_argument("--protein", type=float, required=True)
    p2.add_argument("--carbs", type=float, required=True)
    p2.add_argument("--fat", type=float, required=True)
    p2.add_argument("--weight", type=float, default=None, help="用于 g/kg 安全线校验")
    p2.add_argument("--tdee", type=float, default=None, help="用于赤字换算")
    p2.set_defaults(func=cmd_validate)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
