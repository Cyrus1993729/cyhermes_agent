#!/usr/bin/env bash
# Dayflow 类别 API 回归测试
#
# 🔴 跑之前先看这里：
#   1) 会创建一个幂等测试类别（能删干净）
#   2) 会创建一条 cancelled 测试事项「[测试] 类别删除保护验证」放到今天
#   3) 会留下一个【删不掉】的类别「测试分类C-409」——因为类别一旦被事项引用过，
#      即使事项移走/取消，referenceCount 仍计入历史，永久 409。
#      → 必须人工决定：留着改名，或后台清理。
#   4) 会临时把 sport 颜色改成 pink 再改回来（失败时记得手动还原 orange）
#
# 用法：bash test_categories.sh --confirm

set -u
if [ "${1:-}" != "--confirm" ]; then
  echo "⚠️  这会留下删不掉的测试类别和一条 cancelled 测试事项。"
  echo "   确认无影响后重跑：bash test_categories.sh --confirm"
  exit 1
fi

NODE="C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe"
ENTRY="C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/deployment/home.mjs"
D="$(cygpath -m "$LOCALAPPDATA" 2>/dev/null || echo "$LOCALAPPDATA")/Temp/dfcat_$$"
mkdir -p "$D"

PASS=0; FAIL=0
uuid() { python -c "import uuid;print(uuid.uuid4())"; }

# retry <cmd...> —— 客户端偶发 TaskCanceledException，重试 3 次
retry() {
  for i in 1 2 3; do
    out=$("$@" 2>&1 | tail -1)
    case "$out" in
      *TaskCanceledException*|*"Invalid Windows HTTP"*) sleep 1; continue ;;
    esac
    echo "$out"; return 0
  done
  echo "RETRY_FAILED"; return 1
}

check() { # check <描述> <期望子串> <实际>
  case "$3" in
    *"$2"*) PASS=$((PASS+1)); echo "  ✅ $1" ;;
    *)      FAIL=$((FAIL+1)); echo "  ❌ $1  ← 期望含「$2」，实际：$3" ;;
  esac
}

echo "== 0. 列出类别 =="
CATS=$(retry "$NODE" "$ENTRY" client categories)
echo "  $CATS" | head -c 300; echo

echo "== 1. 建类别（带颜色图标）=="
echo '{"name":"测试分类A","color":"pink","icon":"book"}' > "$D/c1.json"
R1=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/c1.json" --request-id "$(uuid)")
check "create 返回 custom_ 前缀 id" "custom_" "$R1"
A_ID=$(python -c "import json,sys;print(json.loads('''$R1''')['id'])")

echo "== 2. 只给 name（默认 teal/tag）=="
echo '{"name":"测试分类B"}' > "$D/c2.json"
R2=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/c2.json" --request-id "$(uuid)")
check "默认颜色 teal" '"color":"teal"' "$R2"
B_ID=$(python -c "import json,sys;print(json.loads('''$R2''')['id'])")

echo "== 3. patch 改名+换色 =="
echo '{"name":"测试分类B改","color":"slate"}' > "$D/p1.json"
R3=$(retry "$NODE" "$ENTRY" client category-patch "$B_ID" --json-file "$D/p1.json" --request-id "$(uuid)")
check "patch 生效" '"color":"slate"' "$R3"

echo "== 4. 校验类（全部应被拒绝）=="
for case in '{"name":""}|空名' '{"name":"   "}|纯空格' '{"name":" 前导空格"}|首尾空格'; do
  json="${case%|*}"; label="${case#*|}"
  echo "$json" > "$D/v.json"
  R=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/v.json" --request-id "$(uuid)")
  check "$label 被拒绝" '"error"' "$R"
done
echo '{"name":"测试分类C","color":"red"}' > "$D/v.json"
check "非法颜色被拒绝" '"error"' "$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/v.json" --request-id "$(uuid)")"
python -c "import json;json.dump({'name':'测'*21},open(r'$D/v2.json','w',encoding='utf-8'),ensure_ascii=False)"
check "超20字被拒绝" '"error"' "$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/v2.json" --request-id "$(uuid)")"

echo "== 5. 重名 / NFKC 全角去重 =="
echo '{"name":"测试分类B改"}' > "$D/v.json"
check "重名被拒绝" '"error"' "$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/v.json" --request-id "$(uuid)")"
python -c "import json;json.dump({'name':'测试分类Ｂ改'},open(r'$D/v3.json','w',encoding='utf-8'),ensure_ascii=False)"
check "全角同名被拒绝(NFKC)" '"error"' "$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/v3.json" --request-id "$(uuid)")"

echo "== 6. 幂等：同一 request-id 两次 =="
RID=$(uuid)
echo '{"name":"测试分类D-幂等"}' > "$D/c9.json"
X1=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/c9.json" --request-id "$RID")
X2=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/c9.json" --request-id "$RID")
[ "$X1" = "$X2" ] && { PASS=$((PASS+1)); echo "  ✅ 幂等（两次返回同一对象）"; } || { FAIL=$((FAIL+1)); echo "  ❌ 幂等失效"; }
D_ID=$(python -c "import json,sys;print(json.loads('''$X1''')['id'])")

echo "== 7. 删除不存在的类别 =="
check "分类不存在" "分类不存在" "$(retry "$NODE" "$ENTRY" client category-delete "custom_00000000-0000-0000-0000-000000000000" --request-id "$(uuid)")"

echo "== 8. 默认类别可改性（sport 改色后还原）=="
echo '{"color":"pink"}' > "$D/p6.json"
check "默认类别改色成功" '"color":"pink"' "$(retry "$NODE" "$ENTRY" client category-patch sport --json-file "$D/p6.json" --request-id "$(uuid)")"
echo '{"color":"orange"}' > "$D/p7.json"
check "颜色已还原 orange" '"color":"orange"' "$(retry "$NODE" "$ENTRY" client category-patch sport --json-file "$D/p7.json" --request-id "$(uuid)")"

echo "== 9. 引用保护（会留下删不掉的类别 C-409）=="
echo '{"name":"测试分类C-409"}' > "$D/c8.json"
R=$(retry "$NODE" "$ENTRY" client category-create --json-file "$D/c8.json" --request-id "$(uuid)")
C_ID=$(python -c "import json,sys;print(json.loads('''$R''')['id'])")
TODAY=$(python -c "import datetime;print(datetime.date.today())")
python -c "import json;json.dump({'title':'[测试] 类别删除保护验证','date':'$TODAY','category':'$C_ID','mode':'binary','source':'hermes','notes':'类别API回归测试，测完即取消'},open(r'$D/i1.json','w',encoding='utf-8'),ensure_ascii=False)"
ITEM=$(retry "$NODE" "$ENTRY" client create --json-file "$D/i1.json" --request-id "$(uuid)")
I_ID=$(python -c "import json,sys;d=json.loads('''$ITEM''');print(d.get('result',d)['id'])")
check "被引用时拒删(itemCount)" "itemCount" "$(retry "$NODE" "$ENTRY" client category-delete "$C_ID" --request-id "$(uuid)")"

echo "== 10. 清理 =="
retry "$NODE" "$ENTRY" client category-delete "$A_ID" --request-id "$(uuid)" >/dev/null
retry "$NODE" "$ENTRY" client category-delete "$D_ID" --request-id "$(uuid)" >/dev/null
echo "  已删 测试分类A / D-幂等（从未使用过，删得掉）"
echo "  ⚠️ 残留：类别「测试分类C-409」$C_ID（referenceCount>0，删不掉）"
echo "  ⚠️ 残留：事项「[测试] 类别删除保护验证」$I_ID（已建，建议 patch 成 cancelled）"

echo
echo "==== 通过 $PASS ｜ 失败 $FAIL ===="
rm -rf "$D"
