# 两会/政府工作报告 财政政策数据源

## 适用指标
- 赤字率、赤字规模
- 地方政府专项债额度
- 超长期特别国债规模
- 特别国债（补银行资本等专项用途）
- 一般公共预算支出规模
- 财政收支、转移支付安排

## 一手源

| 来源 | URL 模式 | 发布节奏 |
|---|---|---|
| 中国政府网 政策解读 | `https://www.gov.cn/zhengce/YYYYMM/content_NNNNNNN.htm` | 两会开幕当日（3月5日）起陆续发布 |
| 人民网 两会专题 | `http://lianghui.people.com.cn/YYYY/n1/YYYY/MMDD/cNNNNNN-NNNNNNNN.html` | 两会期间实时 |
| 新华社 全文稿 | `http://www.news.cn/politics/...` 或 `https://www.news.cn/...` | 两会开幕当日 |
| 财政部 预算报告 | `http://yss.mof.gov.cn/` 或 `http://www.mof.gov.cn/zhengcefabu/` | 两会后1-2周 |

## 抓取流程（2026-07-24 实测）
1. **用 DuckDuckGo HTML 端点定位 URL**：
   ```bash
   curl -s -L "https://html.duckduckgo.com/html/?q=政府工作报告+2026+赤字率+专项债" \
     -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
     -H "Accept-Language: zh-CN,zh;q=0.9" \
     | grep -oP '<a rel="nofollow" class="result__a" href="[^"]*">[^<]*</a>' | head -10
   ```
2. **从结果中挑选 gov.cn / people.com.cn / news.cn 域名**，提取 `uddg=` 后的真实 URL
3. **直连一手端点抓正文**：
   ```bash
   curl -s -L "URL" \
     -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
     | sed -n '/<p/,/<\/p>/p' | sed 's/<[^>]*>//g' | head -80
   ```
4. **提取关键数字**：赤字率、赤字规模、专项债额度、超长期特别国债规模、一般公共预算支出

## 实测样例（2026-07-24 抓取）
- **中国政府网**：`https://www.gov.cn/zhengce/202603/content_7060945.htm`
  - 标题：《4%左右，赤字率为何这样安排？》（新华社3月5日电）
  - 内容：赤字率4%左右、赤字规模5.89万亿元、超长期特别国债1.3万亿元、专项债4.4万亿元、特别国债3000亿元（补银行资本）、一般公共预算支出30万亿元
- **人民网两会频道**：`http://lianghui.people.com.cn/2026/n1/2026/0305/c461910-40675373.html`
  - 标题：《政府工作报告：2026年赤字率拟按4%左右安排》
  - 内容同上（两会开幕日实时稿）

## 坑
1. **Bing 搜索对该类查询经常被 Cloudflare 拦截**（2026-07-24 再次确认），返回验证页或空结果。改用 DuckDuckGo HTML 端点。
2. **gov.cn 的 URL 路径不规律**（`content_NNNNNNN.htm` 中的数字无规律），必须先搜索定位，不能猜测。
3. **新华社全文稿有时在 news.cn 找不到**（403/405），优先用 gov.cn 转载版或人民网两会专题。
4. **财政政策数据 as-of 日期**：通常是两会开幕日（3月5日），不是发布日期（同日但需标注"2026年3月5日政府工作报告"）。

## 交付格式
表格列：指标 | 数值 | 来源（机构+稿件名） | as-of（政府工作报告年份+开幕日期）
