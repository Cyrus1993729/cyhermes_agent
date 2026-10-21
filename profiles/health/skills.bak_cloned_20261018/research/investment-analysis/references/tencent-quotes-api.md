# 腾讯行情接口速查（A股 + 港股实时/历史行情，免费直连）

**实踩**：2026-08-31（A股+港股地产股批量收盘整理、龙湖公告后股价走势回顾）。腾讯行情接口国内直连免费（`--noproxy '*'` 或 urllib 禁代理），无需 API key/授权。

## 1. 实时行情（批量）

```
https://qt.gtimg.cn/q=sz000002,sh600048,hk00960,hk01109,...
```

- 一次可传几十个代码（逗号分隔），直连即可
- 响应 GBK 编码：`resp.content.decode("gbk", errors="replace")`
- 每行格式 `v_sz000002="...";`，按 `~` 切分：
  - `f[1]` 名称（含中文空格垫位，如"万 科Ａ"）
  - `f[2]` **纯代码不带市场前缀**（"000002"/"00960"）→ 市场（A/HK）必须靠**自己请求列表里维护的映射**判断，不能从响应推断
  - `f[3]` 最新价、`f[4]` 昨收、`f[5]` 今开
  - `f[31]` 涨跌、`f[32]` 涨跌幅%、`f[33]` 最高、`f[34]` 最低
  - `f[36]` 成交量（A股=手，港股=股）、`f[37]` 成交额（A股=万元，港股=HKD）
  - 港股多一个 `f[30]` 时间戳（"2026/08/28 15:18:23"）
- 交易日收盘后（A股 15:00 / 港股 16:00）查询即当日收盘数据；周末/盘中查询显示最近交易日或盘中值——**先 `date` 确认今天是星期几再解释数据**（用户周六问"今天的股价"实际要的是最近交易日收盘）

## 2. 日 K 线（判断"事件后股价反应"）

```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=hk00960,day,,,25,qfq
```

- JSON：`data.hk00960.day` = `[[日期,开,收,高,低,成交量], ...]`（注意顺序：开、收、高、低）
- 用途：公告/财报发布前后股价对比（例：龙湖 8/14 业绩预告 → 8/14 当日 -1.2% 但预告后两周 +6~8%，用 K 线还原真实反应，避免凭印象断言"发完就涨"）

## 3. Python 调用姿势（anti-proxy）

```python
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 禁代理直连
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
raw = opener.open(req, timeout=15).read()
text = raw.decode("gbk", errors="replace")
```

## 注意

- 港股低价股（如 0.038 港元的旭辉）字段正常，别当数据错误
- 已停牌标的不在响应里或字段为 0——对照请求列表排查缺席行
- 与新浪接口（`http://hq.sinajs.cn/list=rt_hk00960`，需 Referer 头）互为备份