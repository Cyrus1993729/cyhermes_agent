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
可直接改用的生成器：`scripts/render_week_html.py`（纯时间轴） / `scripts/render_agenda_overlap_html.py`（日程+重叠可视化三块版）
重叠可视化的完整口径与实测数字：`references/overlap-visualization-case.md`

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

两条实现细节：
- `dataset.col` 拿到的是**字符串**，和 `c.day`（数字）比之前先 `+e.dataset.col`，否则 `===` 永远不相等
- 把判据写成一次算总账，别逐条人肉看：
  ```python
  js('''(() => { ... const bad=cells.filter(c=>{const h=heads.find(x=>x.col===c.day);
        return !h||c.cx<h.left||c.cx>h.right||c.clipped;});
      return JSON.stringify({total:cells.length,bad}); })()''')
  ```
  `bad:[]` 才发图；`bad` 里每一条带 `txt` 前 40 字，能直接定位是哪条压字了。

## 坑

| 坑 | 现象 | 修法 |
|:--|:--|:--|
| 截图 API 超时 | `cdp('Page.captureScreenshot', captureBeyondViewport=True)` 报 5s IPC timeout，降 scaleFactor 也一样 | 换内置 `capture_screenshot()`，一次就成且自动出整页 @2x（1520×1186 → 3040×2372）。别在 cdp 版本上反复重试 |
| **浏览器没起** | `browser_exec` 直接报 `BU_CDP_URL=http://127.0.0.1:9222 unreachable … is the dedicated automation Chrome running?`；`local=true` 也一样 | 自己拉一个（后台起）：`chrome.exe --remote-debugging-port=9222 --user-data-dir=<专用目录> --headless=new about:blank`，再 `curl -s --noproxy '*' http://127.0.0.1:9222/json/version` 看到 `Chrome/...` 才继续。这是环境没起，不是 browser 工具坏了 |
| 中文文件名 | 后续 `MEDIA:` 发送留隐患 | 先 `cp` 一份纯 ASCII 名字（`week_calendar_YYYYMMDD.png`）再发 |
| 极小时间块 | 10 分钟的事件色块只有 ~10px 高，标题全裁 | 最小块高 `max(real, 50)` + `.short` 样式（小一档字号、标题可换行） |
| 长标题 | `text-overflow:ellipsis` 把标题截成「设计部室内精装修+H地块…」 | 去掉 `white-space:nowrap`，改 `word-break:break-word` 让它换行。**但换行还不够**：90 分钟块装不下 40 字标题，仍会 `clipped:true` → 再加 `.ev.long`（标题长度 >20 时挂上）把字号降到 10.5px、行高 1.16、时间行降一档；改完必须重跑 DOM 校验确认 `clipped` 全为 false |
| 底部刻度被切 | 最后一个整点标签压在画布下沿 | 刻度循环 `range(START, END)` 不要 `+1`；底部另留 ~110px 给图例 |
| 同时段多条 | 色块互相压住 | 按分组贪心分槽（`_col`/`_ncol`）再分宽 |
| 跨日事项 | 塞进时间轴会糊成一条压满全天的色块 | 单独做**顶部横幅泳道**，横跨对应列 |
| **时间轴范围写死** | 固定 `07:00–22:00` 会把 21:00 之后新增的安排**整条丢掉**，用户不会告诉你「图里少了一条」，他会以为你没记 | `START_H = min(所有 start)`、`END_H = max(所有 end)`，**每次从数据算**。本次就因为新加了一条 21:00–23:00，范围从 7–22 改成 8–24。`scripts/render_week_html.py` 已内置 `axis_range()`（当周数据 → 前后各留 1 小时 → 夹到 0–24，最小 3 小时），**不要再从外面 monkeypatch `R.START_H`** |
| **绝对定位子元素撑破画布** | `scrollWidth=1598` > 画布 1520，最右刻度/色条被裁。成因：容器 `.dayrow{margin-left:64px}` 又有子元素 `left:px(...)`，两段偏移叠加 | 坐标一律相对**定位容器自身**算（容器 `left:0;width:AW`，子元素 `left:(m-m0)/(m1-m0)*AW`）。`AW = 画布宽 - body padding×2 - border×2 - sect padding×2 - 左标签宽`。改完跑溢出扫描 |
| 短色块文字冲出条外 | 30 分钟条只有 ~45px，`<span>` 里的标题直接溢出到隔壁 | 先在 Python 里判宽度：`w>=104` 才生成文字，否则只画纯色块（完整名称在卡片/明细表里） |
| 重叠斜纹压字 | 斜纹框覆盖整行时把色条上的标题盖住 | 分层 z-index：斜纹 `1`（底）、色条/跨度带 `2`、分钟标签 `3`；分钟数**不放斜纹内部**，另起一行 `.olab{top:82px}` |

## 按周输出日程：视图选择与可读性验收

- 时间轴适合少量、时段明确且标题短的事项；同日密集或重叠安排会把小块挤窄、裁掉标题。此时不要为通过时间轴校验反复缩字号，改用**按天分列的议程卡片视图**：按时间排序，卡片完整显示时段、标题、分类和状态，适合周工作安排。
- 用 DOM 统计核验：日期列数为 7、事项卡片数与筛选后的源数据数相同；文字应完整可读。时间重叠需逐日检测并在卡片及图例中显式标出，不能静默覆盖；**但只标橙不够**——见上文「要在图里显示出来 ≠ 加个颜色」。空白日期显式写“暂无安排”。检查页面滚动高度/截图画布高度，确保最后一行与图例没有被截掉。
- 周视图的查询时间窗要以当前本地日期所在周（周一至周日）计算，而非取库中最早事项所在周；过滤取消项和窗外事项，并保留已完成项但明确标状态。标题应准确称“本周工作安排/本周日程”，不要把副业、运动混入后仍只叫工作安排；若混合类别，要在图中图例标清。
- 截图工具返回路径后，先确认浏览器实际页面 URL、DOM 项目数及正文，再复制截图。不要把 about:blank/空页面的截图当成成品；若出现空白，换有内容的独立 session 加载 `file:///...` 后再截图与校验。
- 含密集日程时，宁可增加卡片视图纵向画布高度，也不要用固定高度裁切内容；缩放/截图前后都核对最终画布和项目数。

## 🔴 用户说「要在图里显示出来」≠ 加个颜色

标注色（橙色/红框）只是提示，**用户要的是把关系本身画出来**。
一次实测：第一版把重叠卡片标橙 + 写一句「时间重叠」，他回「时间重叠的安排要在图里显示出来」。
颜色+一个词不含信息量：既没说是和**哪一条**重叠，也没说**重叠了多久**。

合格的重叠图必须三样齐全（缺一样他都会再提一次）：

1. **图形层**：时间轴上把重叠区间真画出来（红色斜纹盖在色条上），一眼看出哪段时间被两条占着。
2. **卡片层**：重叠事项挂红框，卡内**逐条**写对端全名 + 重叠窗口 + 分钟数，例：
   `⟷ 地下会所多功能室设计灵感收集（10:30–11:45，75分）`。**不要截断对端名称**——
   为省版面把名称截成「地下会所多功能室设计…」会被当成漏信息（他要完整回执，
   卡片写全名、明细表再列一遍不算冗余）。
3. **明细表**：底部逐对列出 `日期 / 事项A + 起止 / 事项B + 起止 / 实际重叠时段 / 时长`，
   能一眼数出几对、各多少分钟。

判定口径必须写进图注：**只有起止时间有真正交集才算重叠**（`max(start) < min(end)`）；
首尾相接（09:30–10:00 与 10:00–10:30）**不算**。主动说明这条，否则用户会质疑为什么某对没标。

**长跨度事项要单独点明**：极端情况下全部重叠都来自同一条 8 小时事项（如 09:30–17:30 的
「设计灵感收集」），当天其余安排整体落在它内部。图注里写明成因，回复末尾给一条**可执行的收口建议**
（「要不要把这条拆成具体时段，重叠就自动消除」），否则他看到的只是一片红。

### 溢出扫描（每次截图前跑）

版面除了防「压字」，还要防「出画布」。一条判据搞定：

```python
js('''(() => { const bad=[];
  document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();
    if(r.right>CANVAS_W+1||r.left<-1) bad.push({cls:e.className.toString().slice(0,16),
                                               right:Math.round(r.right),txt:e.innerText.slice(0,14)});});
  return JSON.stringify({docW:document.documentElement.scrollWidth,
                         docH:document.documentElement.scrollHeight,overflow:bad}); })()''')
```

要求 `docW == 画布宽` 且 `overflow:[]`；清单带 class 和文字，能直接定位是哪一层的 left 算错了。
把 `clipped`（`scrollHeight>clientHeight+1`）和 `overflow` 写成一次算总账的返回体，截图前一次跑完。

**视觉模型只用来查乱码/方块**；它报的「文字压住」「超出边界」经常误判（本次全报错，
实际 `clip:[]`、`overflow:[]`）。压字与越界一律以代码数值为准。

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
