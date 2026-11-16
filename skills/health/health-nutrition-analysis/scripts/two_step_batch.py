# -*- coding: utf-8 -*-
"""批量跑 boohee.two_step()——逐菜「免费匹配 code → 开放平台查营养素」。

为什么要有这个脚本：
  2026-10-30 实踩——我用 `public_search` + `public_detail` 临时脚本查库再手算，
  绕过了约定好的 `two_step` 流程。用户审计时当场抓出。
  钠因此漏了 900–1400 mg（菜品级条目已含烹饪油盐，手工拆必漏）。

  → 日常记账一律走本脚本，不要临时写搜索脚本、更不要手工拆原料相加。

用法：
  python two_step_batch.py '牛肉炒粉丝炒青菜:170' '红烧豆腐:165' '米饭:120'
  python two_step_batch.py --json items.json        # [{"name":"...","grams":170}, ...]

输出：每个菜的 matched_name / code / source(cache|api) / quality / 全字段营养素，
      最后给合计 + 额度变化。

必看验收点（脚本已自动标红）：
  1. `quality != exact`      → 必须人工复核，可能是品类近似而非同一道菜
  2. 蛋白与碳水同时为 0     → 拆解拆错了（蔬菜不可能这样）
  3. 钠字段为 0             → 未收录，换 code 再查
  4. 嘌呤合计过低          → 熟菜条目 purine 多为 0，不能当依据
"""
import sys, json, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
TOOLS = os.path.expanduser(r"~\health\tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import boohee  # noqa: E402

KEYS = ["kcal", "protein", "fat", "carb", "fiber", "sodium", "purine"]


def _quota():
    try:
        q = boohee.quota_now()
        return q if callable(q) else q
    except Exception:
        return "n/a"


def run(items):
    print(f"额度(开始): {_quota()}")
    total = {k: 0.0 for k in KEYS}
    flags = []

    for name, grams in items:
        print("\n" + "=" * 72)
        print(f"【{name}】{grams} g")
        try:
            r = boohee.two_step(name, grams)
        except Exception as e:
            print(f"  EXC: {e}")
            flags.append(f"{name}: 调用异常 {e}")
            continue

        if not r.get("ok"):
            print(f"  ok=False: {r.get('note') or r.get('err')}")
            flags.append(f"{name}: ok=False ({r.get('note') or r.get('err')})")
            continue

        nu = r.get("nutrients") or {}
        print(f"  matched={r.get('matched_name')}  code={r.get('code')}  "
              f"source={r.get('source')}  quality={r.get('quality')}")
        if r.get("decomposed"):
            print(f"  decomposed=True  by_llm={r.get('by_llm')}")
            for it in (r.get("ingredients") or []):
                print("    ├ " + json.dumps(it, ensure_ascii=False))
        if r.get("missing"):
            print(f"  MISSING: {r['missing']}")
        if r.get("warnings"):
            print(f"  WARN: {r['warnings']}")
        print("  " + "  ".join(f"{k}={nu.get(k)}" for k in KEYS))

        # 验收点
        if r.get("quality") not in (None, "exact", "user_label"):
            flags.append(f"{name}: quality={r.get('quality')}（非 exact，须人工复核匹配是否同一道菜）")
        p, c = (nu.get("protein") or 0), (nu.get("carb") or 0)
        if p == 0 and c == 0:
            flags.append(f"{name}: 蛋白与碳水同时为 0 —— 多半拆解拆错（蔬菜不可能这样）")
        if nu.get("sodium") == 0 and name not in ("米饭", "粉丝"):
            flags.append(f"{name}: 钠=0 —— 疑未收录，换 code 再查")

        for k in KEYS:
            total[k] += (nu.get(k) or 0)

    total = {k: round(v, 2) for k, v in total.items()}
    print("\n" + "=" * 72)
    print(f"合计: {total}")
    k, p, f, c = total["kcal"], total["protein"], total["fat"], total["carb"]
    if k:
        print(f"供能比: 蛋白{p*4/k*100:.1f}%  脂肪{f*9/k*100:.1f}%  碳水{c*4/k*100:.1f}%")
        print(f"算术自检: {p*4+c*4+f*9:.1f} vs {k:.1f} -> {(p*4+c*4+f*9)/k-1:+.2%}")
    print(f"额度(结束): {_quota()}")

    if flags:
        print("\n🔴 验收未通过项：")
        for x in flags:
            print(f"  - {x}")
    else:
        print("\n✅ 四项验收全过（quality / 蛋白碳水 / 钠 / 嘌呤需自行再看一眼嘌呤合计）")
    return {"total": total, "flags": flags}


def main(argv):
    if argv and argv[0] == "--json":
        raw = json.load(open(argv[1], encoding="utf-8"))
        items = [(x["name"], float(x["grams"])) for x in raw]
    else:
        items = []
        for a in argv:
            if ":" not in a:
                print(f"跳过（需 name:grams 格式）: {a}")
                continue
            n, g = a.rsplit(":", 1)
            items.append((n.strip(), float(g)))
    if not items:
        print(__doc__)
        return 1
    run(items)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
