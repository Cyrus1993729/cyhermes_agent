# -*- coding: utf-8 -*-
import json, re, datetime, pathlib

ROOT = pathlib.Path(r"D:/Workspace/Projects/TrendRadar")
draft = (ROOT / "output/_draft_cb.txt").read_text(encoding="utf-8")
cands = json.loads((ROOT / "output/candidates_cb.json").read_text(encoding="utf-8"))["candidates"]

def url_of(idx):
    return cands[idx]["url"]

events = [
    ("欧盟11月1日起对境外直邮小包按件收2欧元处理费", 46, "🛃 政策法规",
     "欧盟自11月1日起对境外直邮B2C包裹按报关商品项每件征收2欧元联盟处理费。路透看到的文件测算，这套收费一年最多可带来约60亿欧元；Temu、Shein、AliExpress 的低价小包受冲击最大。", "多源报道"),
    ("美国商务部修正中国皮卡货箱盖反倾销初裁", 39, "🛃 政策法规",
     "美国商务部以初裁存在重大计算错误为由，修改对中国产皮卡货箱盖低于公平价值调查的初裁结论，调查期为2025年7月1日至12月31日。修正后该调查期内中国出口商的对美报价需按新保证金比例重算。", "Federal Register"),
    ("eBay Live 直播伦敦卡展，主打拆卡", 20, "🏪 平台动态",
     "10月30日至11月1日，eBay Live 在伦敦卡展现场直播，内容包括稀有宝可梦卡开箱、游戏王藏品和英超球星卡拆卡，面向英国买家。", "ChannelX"),
    ("TikTok Shop 把便捷退货当成拉销量工具", 9, "🏪 平台动态",
     "2026年秋季，TikTok Shop 与 DoorDash 先后加码退货体验，把好退货当作提升转化的手段。退货率正从售后指标变成选品和定价的前置变量。", "Modern Retail"),
    ("小额免税终止后的黑五：Shein 美国站涨价", 96, "📦 物流与市场",
     "美国执行了10年的小额免税通道（单笔800美元以下包裹免关税）终止后，Shein 美国站价格明显上涨。国内媒体称今年黑五中国卖家变天，直邮小包成本优势被削弱，履约转向海外仓。", "多源报道"),
    ("德国买家账号被标记，卖家担心牵连店铺", 38, "🛡️ 合规与风险",
     "一位卖家称其德国买家账号同时触发身份验证、事件报告和退货警告三项标记，担心同一身份信息下的卖家账号被连带审核；平台未证实会连带处理。", "Reddit FBA"),
    ("保税仓进口商品能否七天无理由退货，关键看商品是否属除外品类", 71, "🛡️ 合规与风险",
     "广州日报案例指出，保税仓发货的进口商品原则上同样适用法定七日无理由退货，能否排除取决于是否属法定除外情形及消费者是否依法确认。", "广州日报新花城"),
    ("卖家讨论：单价降12%要不要换供应商", 36, "💼 卖家运营",
     "Reddit 亚马逊卖家板块提问：新供应商报价低12%是否值得切换。回复集中在换厂隐性成本——重新打样、验货、交期波动和断货风险，主流建议先小批量试单。", "Reddit FBA"),
    ("有卖家怀疑亚马逊存在隐形日销上限", 37, "💼 卖家运营",
     "一位卖家称观察两年，单量涨到某一水平后不再上升，怀疑平台存在未公开的每日销量上限。帖中没有平台官方回应，回复多指向库存周转、广告位和类目竞争。", "Reddit FBA"),
]

# ---- 第5步 已推送清单 ----
MOD = ["的", "了", "将", "被", "把", "对", "与", "和", "在", "是"]
def norm(t):
    s = t.lower()
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "", s)
    for m in MOD:
        s = s.replace(m, "")
    return s

pf = ROOT / "pushed_titles.json"
pd = json.loads(pf.read_text(encoding="utf-8"))
existing = {x.get("norm") for x in pd["pushed"]}
now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
added = 0
for title, idx, sec, summ, src in events:
    n = norm(title)
    if n in existing:
        continue
    pd["pushed"].append({"title": title, "norm": n, "pushed_at": now, "url": url_of(idx)})
    existing.add(n)
    added += 1
pf.write_text(json.dumps(pd, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- 第5.5步 存档 ----
today = datetime.date.today().isoformat()
adir = ROOT / "archives/crossborder"
adir.mkdir(parents=True, exist_ok=True)
(adir / f"{today}.md").write_text(draft, encoding="utf-8")

analysis = draft.split("━━━━━━━━━━━━━━━━━━━━")[0].strip()
news = [{"section": sec, "title": t, "source": src, "url": url_of(i), "summary": s}
        for t, i, sec, s, src in events]
rec = {"date": today, "pushed_at": datetime.datetime.now().strftime("%H:%M"),
       "mode": "crossborder", "news_count": len(news), "analysis": analysis, "news": news}
(adir / f"{today}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")

ixf = adir / "index.json"
ix = json.loads(ixf.read_text(encoding="utf-8")) if ixf.exists() else {"archives": []}
ix.setdefault("archives", [])
entry = {"date": today, "file": f"{today}.md", "news_count": len(news)}
for i, e in enumerate(ix["archives"]):
    if e.get("date") == today:
        ix["archives"][i] = entry
        break
else:
    ix["archives"].append(entry)
ixf.write_text(json.dumps(ix, ensure_ascii=False, indent=1), encoding="utf-8")

print("pushed_added", added, "total", len(pd["pushed"]))
print("archive", today, "news", len(news), "draft_chars", len(draft))
print("index_len", len(ix["archives"]))
