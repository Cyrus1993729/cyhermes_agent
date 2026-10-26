# 周日程图：渲染与校验流水线

用户 2026-10-25 在 Telegram 说「这个图片的形式还可以」，以下是那一版的可复现做法。
**改样式前先问**；只调数据，不重设计。

## 步骤

1. **拉数据**（Dayflow 客户端实例）：
   ```
   "C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe" \
     "C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/deployment/home.mjs" client items
   ```
   输出是**单个 JSON 数组**，后面可能跟一行 `{"requestId":...}` 诊断。逐行扫，取第一个能 `json.loads` 的 `[` 开头的行。

2. **过滤**：只留本周 `date` 区间内的，且 **`status != "cancelled"`**（取消的事项 items 里还在，必须自己滤掉，否则又出现在图上）。

3. **出 HTML**：
   ```
   python scripts/render_week_calendar.py --start 2026-10-26 --days 7 \
       --out C:/Users/Administrator/AppData/Local/Temp/week_cal.html
   ```

4. **截图（浏览器 CDP）**：
   ```python
   goto_url("file:///" + html_path); wait_for_load()
   cdp('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=2, mobile=False)
   pth = capture_screenshot()          # 给的是 2x 全页 PNG
   ```

5. **校验**，通过后复制到稳定路径，用 `MEDIA:<绝对路径>` 发出去。
   Windows 上加一份 ASCII 文件名副本更保险，例如 `D:\Workspace\week_calendar_20261026.png`。

## 校验：用 DOM 反查，不要用看图模型

看图模型**读不准分栏**——本次它两次报“千问在周二、领航员在周三”，实际是周三和周四。
列位置必须用 DOM 判定：

```python
check = js('''(() => {
  const heads = [...document.querySelectorAll('.wdcell[data-col]')].map(e => {
    const r = e.getBoundingClientRect();
    return {col: e.dataset.col, name: e.querySelector('.d').textContent,
            left: Math.round(r.left), right: Math.round(r.right)};
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

`clipped` 抓的是 `scrollHeight > clientHeight`，能自动发现标题被截断。看图模型只用来做最后一层“人眼”确认（颜色、整体观感）。

## 踩过的坑

| 现象 | 原因 | 处理 |
|:--|:--|:--|
| 10 分钟的事项标题只剩半个字 | 块高按比例只有 ~8px | `MIN_BLOCK_H = 50`，小字号 + 两行；**图例里必须写明“实际只有 X 分钟，为看清标题做了加高”**，否则用户会误以为时长变了 |
| 标题带省略号 | `.n2` 用了 `white-space:nowrap + ellipsis` | 改成 `word-break:break-word` 允许换行，块高够就完整显示 |
| `Page.captureScreenshot` 卡住、报 `_IPCResponseTimeout ... timed out after 5s` | 大画布 + `captureBeyondViewport=True` 偶发 | 换内置 `capture_screenshot()` 助手，一次成功；它返回的已经是全页 2x PNG |
| 底部图例/刻度被裁 | 画布高度没给图例留位 | `H = grid_top + gh + 110`；时间轴刻度只画到 `end_h - 1`，别画到底边 |
| 全天事项改成定点后还原成横幅 | 没清 `allDay`/`endDate` | patch 时必须显式传 `allDay:false` + `endDate:null` |

## 版式约定（用户认可的这版）

- 宽 1520px，左轴 90px，7 列各 200px，每小时 56px，2x 出图（约 3040×2300）
- 颜色：主业工作蓝 `#3b82f6` / 运动橙 `#f97316` / 副业紫 `#a855f7` / 生活青 `#14b8a6`；周末列头日期红字
- 多日/全天事项：顶部横跨对应列数的蓝色渐变横幅
- 底部图例 + 一行灰色备注（说明非标准时长等）
