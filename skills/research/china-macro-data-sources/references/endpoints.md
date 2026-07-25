# 已验证一手端点（2026-07-24 会话实测）

## 1. 国家统计局 最新发布（PMI / 失业率 / 贸易 / CPI 等）
- 列表页：`https://www.stats.gov.cn/sj/zxfb/`（200, UTF-8）
  - 分页：`index_1.html`（更早）、`index_2.html`…
  - 稿件 href 形如 `./202607/t20260715_1964123.html`，全 URL = `https://www.stats.gov.cn/sj/zxfb/202607/t20260715_1964123.html`
  - 解析：`<a ... href="(\./20\d{4}/t[^"]+)"[^>]*>(标题)</a>`，标题关键词定位：
    - `X月中国采购经理指数运行情况`（月末发布，含制造业PMI表、非制造业商务活动表、综合PMI）
    - `X月份/上半年国民经济运行…`（月中发布，含城镇调查失业率、货物进出口、CPI/PPI、社零、固投）
- 正文抓取后直接 `<tr>`/`<td>` 解析表格（rowspan 坑见 SKILL.md 坑3）。
- 实测样例（2026-07-24 抓到）：
  - `202606/t20260630_1964032.html` = 2026年6月PMI稿（发布 2026/06/30 09:30）
  - `202607/t20260715_1964121.html` = 上半年经济稿（6月城镇失业率5.0%、上半年货物进出口254686亿+16.9%）
  - `202606/t20260616_1963954.html` = 5月稿（5月失业率5.1%）；`202605/t20260518_1963732.html` = 4月稿（4月失业率5.2%）

## 2. 中国货币网 / CFETS 人民币中间价（官方定盘）
- `https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/fx/ccpr.json`（200, JSON, 无需特殊头）
- 结构：`data.lastDate`（如 `2026-07-24 9:15`）+ 币种数组，元素字段：
  - `vrtName`: `美元/人民币`，`vrtEName`: `USD/CNY`，`price`: `6.7939`，`bp`: `33.00`（较前日点数）
- 页面端 `chinamoney.com.cn/chinese/bkccpr/` 是 JS 骨架（无内嵌数据）；旧接口 `ags/ms/cm-u-bk-ccpr/CcprHis` 已 404——**用上面的 r/cms JSON**。

## 3. 在岸即期 USDCNY（行情口径，非官方定盘）
- `https://hq.sinajs.cn/list=USDCNY`
  - 必须带 `Referer: https://finance.sina.com.cn`，否则 403
  - 响应 **GBK 编码**，用 `decode('gbk')`
  - 格式：`var hq_str_USDCNY="时间,买入,卖出,最新,量,昨结,最高,最低,开盘,美元人民币,日期";`
  - 实测：`22:57:50,6.7710,6.7730,6.7667,156,6.7667,6.7762,6.7606,6.7720,美元人民币,2026-07-24`
- 与中间价（6.7939）存在口径/点差差异，报告中分开标注。

## 4. 青年失业率（16—24岁，不含在校生）
- **不在**月度国民经济综合新闻稿中。官方发布口：统计局"数据发布"分年龄组城镇调查失业率。
- `data.stats.gov.cn/easyquery.htm` 在本会话 403（可能是IP/会话限制，非永久结论）。拿不到时按 SKILL.md 铁律2如实标注缺口。

## 5. 搜索引擎状态（2026-07-24 会话）
- **Bing 不可用**：`www.bing.com` 对 curl 弹 Cloudflare 验证页；`cn.bing.com` 301→www；浏览器工具对其响应 utf-8 解码报错；UTF-8 修正后对该批精确月度数据仅返回兜底百科（`b_algo` 块10个但相关关键词命中0）。**2026-07-24 再次确认：Cloudflare 拦截持续存在，不可依赖。**
- **DuckDuckGo HTML 端点可用**（替代方案）：`https://html.duckduckgo.com/html/?q=...`（UTF-8 预编码，curl 直接抓，返回 `<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=ENCODED_URL">标题</a>`）。**用于定位 gov.cn / people.com.cn / news.cn 等一手 URL，再直连抓正文**。实测 2026-07-24 成功定位两会财政政策稿件（赤字率4%、专项债4.4万亿等）。
- 教训：精确月度宏观数据不要指望搜索引擎结果页，直接走上面的一手端点；若需搜索定位，用 DuckDuckGo HTML 端点而非 Bing。
