---
name: data-to-image-rendering
description: Use when 用户要「做成一张图」看数据并发出。HTML→PNG 渲染与投递。
version: 1.0.0
metadata:
  hermes:
    tags: [rendering, image, png, telegram, visual, calendar, report]
    related_skills: [dayflow-personal-planner, hermes-telegram-delivery]
---

# 把数据渲染成图片并交付

触发：用户说「我希望你能做一张图，让我更清晰地看到」「把这份数据画成图发给我」「做成截图」。
典型场景：周日程表、指标对比、报表摘要、账单核对表。

**核心路线：Python 算好布局 → 生成 HTML → 无头浏览器截图 → 发 `MEDIA:<路径>`。**
不要用 matplotlib/PIL 硬画——中文字体、圆角、阴影、换行全是坑，HTML+CSS 一次就能做对。

## 一、四步流程

1. **数据侧**：从源头取数（云端库/DB/文件），在 Python 里过滤、分组、排序。
   **排序和聚合在代码里做，不要在脑子里做。**
2. **生成 HTML**：Python 拼字符串，每个元素用绝对定位按数值落位。**尺寸先算好**（宽高写成常量），
   最后 `body{width:Wpx;height:Hpx;overflow:hidden}`，截图就不用猜高度。
3. **截图**：`browser_exec` 打开 `file:///<html>` → 设 device metrics → 截 PNG。
4. **交付**：存成 **ASCII 文件名**（如 `D:/Workspace/week_calendar_20261026.png`）→ 回复里写 `MEDIA:<绝对路径>`。

## 二、截图：用 `capture_screenshot()`，不要用裸 CDP

```python
new_tab("file:///C:/path/to/chart.html")   # 首次导航用 new_tab；同页重绘用 goto_url
wait_for_load()
cdp('Emulation.setDeviceMetricsOverride', width=1520, height=1186, deviceScaleFactor=2, mobile=False)
pth = capture_screenshot()                 # ← 内置 helper，稳定
shutil.copyfile(pth, r"D:/Workspace/xxx.png")
```

🔴 **`cdp('Page.captureScreenshot', format='png', captureBeyondViewport=True)` 会超时**：
反复报 `_IPCResponseTimeout: Page.captureScreenshot timed out after 5s waiting for the daemon`，
降 deviceScaleFactor 到 1、加 `time.sleep`、`ensure_real_tab()` 都救不回来。**改用 `capture_screenshot()` 立刻就好。**
它给出的就是整页 2x 图（1520×1186 → 3040×2372），正是想要的分辨率。

🔴 **`MEDIA:` 走 ASCII 文件名**。中文名多数情况能发，但没有任何好处，别冒险。
源码/中间 HTML 留在 Temp 即可，交付图片放 `D:/Workspace/`。

## 三、排版规则（都是被用户当场指出来的）

| 规则 | 为什么 |
|:--|:--|
| **中文字体写 `"Microsoft YaHei"`** | 不写容易出方框/细字 |
| **每个元素算好尺寸，不要靠流式布局** | 绝对定位才能保证数值与像素对得上 |
| **过小的元素给最小尺寸** | 10 分钟的事件块只 10px 高，标题被裁得看不清。日历类给**下限 50px**，并在图例里注明「实际只有 N 分钟，为看清标题做了加高」 |
| **跨天/无钟点的事项做成顶部横幅** | 塞进时间轴会占满整列，信息全错 |
| **文字用 `word-break:break-word`，不用 `nowrap`+省略号** | 省略号被用户当成「信息被截了」 |
| **底部留白 ≥100px** | 图例容易被画布边缘裁掉 |

## 四、🔴 验收：用 DOM 坐标核，不要问视觉模型

**这是本类任务最容易翻车的地方。** 渲染完让 vision 模型「看一眼对不对」，
它会把列/行判错——2026-10-26 实测：图里「千问培训」明明在**周三**列，vision 两次都报成「周二」，
还据此说「有两处标题被截断」。**照它说的改，就把对的改错了。**

**正确姿势——用 `js()` 拿 bounding box 程序化校验：**

```python
check = js('''(() => {
  const heads = [...document.querySelectorAll('[data-col]')].map(e => {
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
# 然后 Python 里逐条核：heads[day].left <= ev.cx <= heads[day].right 且 not clipped
```

**给每个元素打 `data-*` 属性（`data-col` / `data-day`），验收时才有东西可核。**
视觉模型只用来看「整体好不好看」，**不用来判断位置和截断**。

## 五、发出去之后

- 用户会接着提修改（「再加一条」「这个取消掉」）→ **每改一次都重新拉数、重新截图、重发**，
  不要只回一句「改好了」。
- 图反映的是**生成那一刻的库状态**，所以副标题要写清数据来源和「已按最新调整更新」。
- 数据里如果存在**用户自己还没定的冲突**（同一时间两件事、异地行程撞档），
  **不要在图里静默掉**，在图下文单独列一行问他取消/改期/改时间。

## 参考

- `references/weekly-calendar-grid.md` — **Dayflow 周日程表的完整渲染器**：7 列时间轴 HTML 模板、
  全天/多日横幅、短事件加高策略、重叠检测、DOM 坐标验收代码（2026-10-26 实做，可直接改周次复用）
