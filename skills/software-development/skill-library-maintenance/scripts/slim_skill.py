"""Skill SKILL.md 瘦身工具：按行号区间原文搬移 + 行级零丢失校验。

用法
----
1) 切片（先 grep -n '^## \\|^### ' SKILL.md 拿标题行号）：

    python slim_skill.py --split split_spec.json

   split_spec.json:
   {
     "source": "SKILL.md.bak_slim_20261020_223412",
     "outputs": [
       {"path": "references/a2a-wiring-details.md",
        "header": "# 标题\n\n> 从 SKILL.md 整段搬移，原文未改。什么时候读：……\n\n",
        "segs": [[29, 66], [111, 127]]},
       {"path": "SKILL.md",
        "header": "---\nname: x\ndescription: y\n---\n\n",
        "segs": [[1, 28]],
        "body": "\n## 新增的浓缩章节（可选，纯文本直接拼在 segs 之后）\n"}
     ]
   }

   区间是 1-based、闭区间，**必须包含标题行本身**——漏掉标题 = 整节丢失（真实踩过）。

2) 校验（缺失行数必须为 0）：

    python slim_skill.py --verify SKILL.md.bak_slim_xxx SKILL.md references/a.md references/b.md

判读：缺失 0 行才可以说「一个字没丢」；缺失 >0 会逐条打印缺失行，先看是不是整节标题被切掉。
"""
import argparse
import io
import json
import os
import sys


sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_lines(path):
    return io.open(path, encoding="utf-8").read().splitlines(keepends=True)


def split(spec_path):
    spec = json.load(io.open(spec_path, encoding="utf-8"))
    src = spec["source"]
    L = load_lines(src)
    total = len(L)
    print(f"源: {src}  {total} 行")

    for out in spec["outputs"]:
        chunks = [out.get("header", "")]
        for a, b in out["segs"]:
            if a < 1 or b > total or a > b:
                raise SystemExit(f"区间越界或反序: [{a}, {b}]（源共 {total} 行）")
            chunks.append("".join(L[a - 1:b]))
        chunks.append(out.get("body", ""))
        content = "".join(chunks)

        dst = out["path"]
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        io.open(dst, "w", encoding="utf-8", newline="").write(content)
        print(f"  写入 {dst}: {len(content.encode())} bytes  segs={out['segs']}")

    print("\n切片完成。下一步跑 --verify 校验零丢失。")


def verify(source, outputs):
    orig = io.open(source, encoding="utf-8").read()
    union = set()
    for p in outputs:
        union |= {l.strip() for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()}

    orig_lines = [l.strip() for l in orig.splitlines() if l.strip()]
    missing = [l for l in orig_lines if l not in union]

    print(f"源非空行 {len(orig_lines)} 条；输出并集 {len(union)} 条")
    print(f"缺失行数: {len(missing)}")
    for m in missing[:40]:
        print("  MISSING:", m[:160])
    if len(missing) > 40:
        print(f"  …… 另有 {len(missing) - 40} 行")

    if not missing:
        print("\n✅ 零丢失校验通过：原文每一行都能在新文件里找到。")
    else:
        print("\n❌ 有内容丢失。常见原因：区间边界漏掉了整节标题；重跑时源路径被上一轮结果污染。")
    return 0 if not missing else 1


def main():
    ap = argparse.ArgumentParser(description="SKILL.md 按行号切片 + 零丢失校验")
    ap.add_argument("--split", metavar="SPEC.json", help="按 spec 切片")
    ap.add_argument("--verify", nargs="+", metavar="FILE", help="第一个是原始备份，其余是输出文件")
    args = ap.parse_args()

    if args.split:
        split(args.split)
        return 0
    if args.verify:
        if len(args.verify) < 2:
            raise SystemExit("--verify 至少需要：原始备份 + 1 个输出文件")
        return verify(args.verify[0], args.verify[1:])
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
