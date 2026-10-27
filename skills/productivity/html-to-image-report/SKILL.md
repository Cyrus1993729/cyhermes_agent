---
name: html-to-image-report
description: Use when 用户要一张图/报表/日程视图：渲染成 PNG 发出去。
version: 1.0.0
platforms: [windows]
---

# 数据 → 图（HTML 渲染 + 截图 + 发图）

用户说「做一张图让我更清楚」「排版好看点」「图做好了直接发我」时走这条线。
不要用 PIL/matplotlib 手画（中文排版、圆角、图例全得自己写），也不要让图像模型画图——**用 HTML/CSS，再截图**。

实测案例（2026-10-25，Dayflow 周日程表 → 3040×2372 PNG）：`references/weekly-calendar-case.md`
可直接改用的生成器：`scripts/render_week_html.py`

## 四步流水线

1. **取数并落盘成 JSON**（不要让数据只活在内存里；后续排版、核对都要重读）。
   过滤掉 `status == "cancelled"`、超出时间窗的条目。
2. **Python 生成自包含 HTML**（CSS 内联、不依赖外网、字体指定 `Microsoft YaHei`）。
   画布大小和内部坐标一起算出来，用绝对定位摆放；**打印出最终 W×H**，截图时原样用。
3. **browser_exec 截图**：
   ```python
   new_tab("file:///C:/Users/.../out.html"); wait_for_load()
   cdp('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=2, mobile=False)
   pth = capture_screenshot()      # 整页 + 2 倍像素
   ```
4. **代码校验 + 发图**：先自己核对版面对齐（见下），再 `cp` 成纯 ASCII 文件名，回复里写
   `MEDIA:D:\Workspace\<ascii_name>.png`。

## 校验：用 DOM 包围盒，不要用眼睛

**视觉模型读列/读行会偏位**（本次两次都把周三认成周二）。版面对齐一律用代码验：

```python
js('''(() => {
  const heads=[...document.querySelectorAll('[data-col]')].map(e=>{const r=e.getBoundingClientRect();
    return {col:e.dataset.col,left:Math.round(r.left),right:Math.round(r.right)};});
  const cells=[...document.querySelectorAll('[data-day]')].map(e=>{const r=e.getBoundingClientRect();
    return {day:e.dataset.day,cx:Math.round(r.left+r.width/2),
            clipped:e.scrollHeight>e.clientHeight+1};});
  return JSON.stringify({heads,cells});
})()''')
```

判据：每个元素 `heads[day].left <= cx <= heads[day].right` 且 `clipped == False`。
给容器加 `data-col` / `data-day` 属性就是为了这一步——**生成 HTML 时就预留好**。
视觉模型只用来看「中文有没有乱码/方块、有没有明显压字」，不用它判版式。

## 坑

| 坑 | 现象 | 修法 |
|:--|:--|:--|
| 截图 API 超时 | `cdp('Page.captureScreenshot', captureBeyondViewport=True)` 报 5s IPC timeout，降 scaleFactor 也一样 | 换内置 `capture_screenshot()`，一次就成且自动出整页 @2x（1520×1186 → 3040×2372）。别在 cdp 版本上反复重试 |
| 中文文件名 | 后续 `MEDIA:` 发送留隐患 | 先 `cp` 一份纯 ASCII 名字（`week_calendar_YYYYMMDD.png`）再发 |
| 极小时间块 | 10 分钟的事件色块只有 ~10px 高，标题全裁 | 最小块高 `max(real, 50)` + `.short` 样式（小一档字号、标题可换行） |
| 长标题 | `text-overflow:ellipsis` 把标题截成「设计部室内精装修+H地块…」 | 去掉 `white-space:nowrap`，改 `word-break:break-word` 让它换行 |
| 底部刻度被切 | 最后一个整点标签压在画布下沿 | 刻度循环 `range(START, END)` 不要 `+1`；底部另留 ~110px 给图例 |
| 同时段多条 | 色块互相压住 | 按分组贪心分槽（`_col`/`_ncol`）再分宽 |
| 跨日事项 | 塞进时间轴会糊成一条压满全天的色块 | 单独做**顶部横幅泳道**，横跨对应列 |
| **时间轴范围写死** | 固定 `07:00–22:00` 会把 21:00 之后新增的安排**整条丢掉**，用户不会告诉你「图里少了一条」，他会以为你没记 | `START_H = min(所有 start)`、`END_H = max(所有 end)`，**每次从数据算**。本次就因为新加了一条 21:00–23:00，范围从 7–22 改成 8–24 |

## 交付口径（用户认可的写法）

图发出去时附一段**诚实标注口径**，说清图里哪些是视觉处理过的：
- 「X 那条实际只有 10 分钟，为了看清标题做了加高」（图上也要有脚注）
- 「跨日事项为全天未定钟点，所以是横幅不在时间轴里」
- 「哪几天是空的」

**不要为了让图好看而改数据含义**；必须改视觉时，在图例和回复里同时说明。用户会核这些。

正文里同时给出「图上一眼能看出的冲突/待确认点」，比让他自己找更省事。

## 🔴 改完数据要重出一张，不能只回「已改好」

用户拿到图之后一定会提修改（改时间、把全天拆成具体时段、取消某一条、加新事件）。
**他在看图和回话之间来回切，脑子里的「现在是什么样」就是那张图。**

→ **只要图里的内容变了，就必须重新渲染、重新校验、重新发一张。**
→ 只回一句「已改好」他会不知道改后的样子，还得自己去日程里核对。
→ 重出图时顺便在回复里点出**这次变了哪几处**（1–3 条，不要重发旧信息）。

⚠️ 如果日程的真实数据源是另一个系统（如 Dayflow 云端库），**写库与重出图是一对动作**：
写完必须回读确认再渲染，否则图会画库里没有的东西。
