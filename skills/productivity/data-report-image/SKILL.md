---
name: data-report-image
description: Use when 要把数据做成一张图发到聊天里。HTML→截图→DOM校验→MEDIA发送。
version: 1.0.0
platforms: [windows, macos, linux]
---

# 把数据渲染成图并发送

适用：用户说「做张图让我看得更清楚」「生成图片直接发我」——周日程、表格、看板、对比图这类结构化数据。

**不要用 PIL/matplotlib 手画排版**（中文断行、圆角、阴影、颜色都要自己算），用 HTML + CSS 渲、浏览器截图。质量差距很大，改版也快。

## 流水线

1. **取数据**：从真实数据源拉（API/本地库/文件），**不要手抄进脚本**。取完制数（去重、去 cancelled、按区间过滤），条目数要与预期对得上——数不对先查，别往下做。
2. **写 HTML**：Python 生成字符串，`open(..., encoding='utf-8')` 写盘。中文字体写 `"Microsoft YaHei","Segoe UI",sans-serif`（Windows）。
3. **截图**：浏览器打开 `file:///<html>`，先 `cdp('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=2, mobile=False)`，再 `capture_screenshot()` → 拿到 2x 全页 PNG。
4. **校验**（强制，见下节）。
5. **交付**：复制到稳定路径（**ASCII 文件名更保险**，如 `D:\Workspace\week_calendar_20261026.png`），回复里给 `MEDIA:<绝对路径>`。

## 🔴 校验必须用 DOM，不能用看图模型

看图模型**读不准分栏/行列位置**——实测它把周三、周四的内容报成周二、周三，还漏看了跨列横幅。它只能做最后一层“人眼”确认（颜色、整体观感、文字有没有乱码）。

几何位置一律用 DOM 反查：

```python
check = js('''(() => {
  const heads = [...document.querySelectorAll('[data-col]')].map(e => {
    const r = e.getBoundingClientRect();
    return {col: e.dataset.col, left: Math.round(r.left), right: Math.round(r.right)};
  });
  const evs = [...document.querySelectorAll('.ev')].map(e => {
    const r = e.getBoundingClientRect();
    return {day: e.dataset.day, title: e.querySelector('.n2').textContent,
            cx: Math.round(r.left + r.width/2),
            clipped: e.scrollHeight > e.clientHeight + 1};
  });
  return JSON.stringify({heads, evs});
})()''')
# 判定：heads[day].left <= ev.cx <= heads[day].right 且 not ev.clipped
```

给每个容器加 `data-col` / `data-day` 属性，就是为了这步能被程序判定，而不是靠目测。

`clipped = scrollHeight > clientHeight` 能自动抓出“标题被截断”——比看图模型靠谱得多。

## 踩过的坑

| 现象 | 原因 | 处理 |
|:--|:--|:--|
| 极短时长的事项块标题只剩半个字 | 按比例算出来只有 ~8px 高 | 给 `MIN_BLOCK_H = 50`，小字号+允许换行；**并在图例里写明“实际只有 X 分钟，为看清标题做了加高”**，否则用户会误以为时长被改了 |
| 标题出现省略号 | `.n2` 用了 `white-space:nowrap; text-overflow:ellipsis` | 改 `word-break:break-word` 允许换行，块够高就完整显示 |
| `Page.captureScreenshot` 报 `_IPCResponseTimeout: timed out after 5s` | 大画布 + `captureBeyondViewport=True` 偶发卡住 | 换内置 `capture_screenshot()` 助手，一次成功；它返回的已经是全页 2x PNG，不用再拼 |
| 底部图例/刻度被裁掉 | 画布高度没给图例留位 | `H = 内容高 + 110`；刻度只画到 `end_h - 1`，别画到底边 |
| 重叠事项压在一起 | 没做区间分组 | 同日按开始时间排序，贪心分配 slot，宽度 = 列宽/并发数 |

失败重试原则：同一操作重试 1–2 次即可，别马上换方案。上面两条坑都是第二次就好。

## 已交付版式（周日程）

脚本：`scripts/render_week_calendar.py`，设计说明与完整踩坑：`references/weekly-calendar-image.md`。

```
python scripts/render_week_calendar.py --start 2026-10-26 --days 7 \
    --out C:/Users/x/AppData/Local/Temp/week_cal.html
```

版式：宽 1520 / 左轴 90 / 7 列各 200 / 每小时 56 / 2x 出图（约 3040×2300）。多日事项做成顶部横跨对应列的横幅；一旦改成定点就落回时间轴。

**用户认可过这一版（原话「这个图片的形式还可以」）——只改数据，不重设计；真要改样式先问。**

## 上游数据源示例：Dayflow

做周日程图时数据来自 Dayflow 云端日程库（怎么调客户端写在用户自有 skill `dayflow-personal-planner` 里）。按图前需注意的数据侧坑记在 `references/dayflow-item-prep.md`：多日/全天事项改定点、冲突 409 的处理顺序、`plannedMinutes` 不自动重算、取消的不等于删除。

## 交付话术

发图时正文要说清三件事，一条不超两行：
1. 数据截止/来源是什么
2. 图上哪些是**估算或为了可读性做的视觉处理**（加高的短块、未定钟点的横幅）
3. 图里暴露出的**待用户定的冲突**（同一时间两件事、异地赶不上等）——点到为止，不展开分析
