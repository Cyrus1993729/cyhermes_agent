"""抓取中国疾控中心《中国食物成分表》查询平台全量数据。

用法：python crawl_official_fooddb.py [输出路径]
默认输出 ~/health/fooddb/official_full.json

为什么需要它：GitHub 上的开源镜像只覆盖 61 个子分类，整块缺掉
糖/调味品/饮料/糕点/酒/速食/婴幼儿食品 等 9 个大类。本脚本从官方源补齐。

⚠️ 接口是页面 JS 里的 AJAX，不是公开文档化的 REST API。参数或结构若失效，
   重新打开 https://nlc.chinanutri.cn/fq/foodlist_0_26_112_0_0_1.htm
   看 scripts/front.js 与页面内联 JS 里的 `url:` 即可重新定位。

字段位置（36 列定长数组）已用「酱油 1518」「鸡精 1567」「精盐 1565」
对照详情页逐项验算，勿凭 header 文字顺序推断。
"""
import io, sys, urllib.request, urllib.parse, json, os, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
      "X-Requested-With": "XMLHttpRequest",
      "Referer": "https://nlc.chinanutri.cn/fq/",
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
URL = "https://nlc.chinanutri.cn/fq/FoodInfoQueryAction!queryFoodInfoList.do"

# categoryOne id -> 官方大类名
CAT1 = {1: "谷类及制品", 10: "薯类、淀粉及制品", 11: "干豆类及制品", 12: "蔬菜类及制品",
        13: "菌藻类", 14: "水果类及制品", 15: "坚果、种子类", 16: "畜肉类及制品",
        17: "禽肉类及制品", 18: "乳类及制品", 19: "蛋类及制品", 20: "鱼虾蟹贝类",
        21: "婴幼儿食品", 22: "小吃、甜饼", 23: "速食食品", 24: "饮料类",
        25: "含酒精饮料", 26: "糖、果脯和蜜饯、蜂蜜", 27: "油脂类", 28: "调味品类", 29: "其它"}

# 36 列定长数组 -> 字段名（位置已验算，勿改）
COLS = {0: "id", 2: "foodName", 3: "alias", 5: "edible", 6: "water", 7: "energyKJ",
        8: "protein", 9: "fat", 10: "cholesterol", 11: "ash", 12: "CHO",
        13: "dietaryFiber", 14: "carotene", 15: "vitaminA", 16: "alphaTE",
        17: "thiamin", 18: "riboflavin", 19: "niacin", 20: "vitaminC",
        21: "Ca", 22: "P", 23: "K", 24: "Na", 25: "Mg", 26: "Fe", 27: "Zn",
        28: "Se", 29: "Cu", 30: "Mn", 31: "I",
        32: "SFA", 33: "MUFA", 34: "PUFA", 35: "fatTotal"}


def fetch(cat1, page, retries=3):
    data = urllib.parse.urlencode({"categoryOne": cat1, "categoryTwo": 0, "foodName": "",
                                   "pageNum": page, "field": "", "flag": ""}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL, data=data, headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace'))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)


def main(out_path=None):
    out_path = out_path or os.path.join(os.path.expanduser("~"), "health", "fooddb", "official_full.json")
    out, seen = [], set()
    for c1, cname in CAT1.items():
        page, tp, got = 1, None, 0
        while True:
            try:
                j = fetch(c1, page)
            except Exception as e:
                print(f"  [{cname}] p{page} 失败: {type(e).__name__}")
                break
            if tp is None:
                tp = int(j.get("totalPages", 1) or 1)
            rows = j.get("list") or []
            if not rows:
                break
            for r in rows:
                if not isinstance(r, list) or len(r) < 30 or r[0] in seen:
                    continue
                seen.add(r[0])
                rec = {"_category": cname,
                       "_source": "中国疾控中心营养与健康所 食物营养成分查询平台 nlc.chinanutri.cn",
                       "foodCode": f"OFFICIAL-{r[0]}"}
                for i, k in COLS.items():
                    rec[k] = r[i] if i < len(r) else ""
                out.append(rec)
                got += 1
            page += 1
            if page > tp:
                break
            time.sleep(0.35)          # 礼貌间隔，勿去掉
        print(f"  [{cname:<22}] 官方 {tp} 页 -> 实抓 {got} 条 | 累计 {len(out)}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n✅ 完成：{len(out)} 条 -> {out_path}")
    print("   期望量级 ~1356 条。若明显偏低，检查 totalPages 解析或分类 id 是否变动。")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
