#!/usr/bin/env python3
"""pre_review_check.py 注错回归测试。
验证闸门在遇到预期错误时正确阻断（exit 1），合规交付物正确放行（exit 0）。
"""
import subprocess, sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTRACT = FIXTURES / "contract_test.md"
SCRIPT = Path(__file__).resolve().parent / "pre_review_check.py"

CASES = [
    # (filename, description, expected_exit, expected_keyword)
    ("bad_wrong_mapping.md",   "定投映射私改(39.0→30%而非暂停)",   1, "定投映射"),
    ("bad_wrong_threshold.md", "D4.4阈值私改(±10%→±5%)",         1, "D4.4"),
    ("bad_amplitude_mismatch.md", "振幅矛盾($4,200超出$3,900-$4,000)", 1, "振幅"),
    ("clean_passing.md",       "合规交付物应放行",                 0, None),
]

passed = 0
failed = 0

print("=" * 60)
print("  pre_review_check 注错回归测试")
print("=" * 60)

for filename, desc, want_exit, keyword in CASES:
    path = FIXTURES / filename
    result = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--contract", str(CONTRACT),
         "--deliverable", str(path)],
        capture_output=True, text=True, timeout=30
    )
    stdout = result.stdout
    
    if result.returncode == want_exit:
        # 额外检查：阻断案例需断言关键字
        if want_exit == 1 and keyword:
            if keyword not in stdout:
                print(f"  ❌ {desc}: exit正确({want_exit})但关键字'{keyword}'缺失 — 因错误原因阻断!")
                failed += 1
                continue
        # 放行案例需确认是"通过"而非"未运行"
        if want_exit == 0 and "闸门通过" not in stdout:
            print(f"  ❌ {desc}: exit 0但未输出'闸门通过' — 可能未执行检查")
            failed += 1
            continue
        print(f"  ✅ {desc}: 正确{'(阻断)' if want_exit == 1 else '(放行)'}" + 
              (f" [{keyword}]" if keyword else ""))
        passed += 1
    else:
        print(f"  ❌ {desc}: 期望exit {want_exit} 实际 {result.returncode}")
        print(f"     stdout: {stdout.strip()[-150:]}")
        failed += 1

print(f"\n{'='*60}")
print(f"  结果: {passed}/{len(CASES)} 通过, {failed} 失败")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
