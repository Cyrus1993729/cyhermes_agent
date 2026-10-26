# 案例：Dayflow 周日程 → 周视图 PNG（2026-10-25，Telegram）

用户先口述了一周安排让我建库，随后要「一张图更清楚看到这周日程」，做完直接 Telegram 发图。
成品：`D:\Workspace\week_calendar_20261026.png`，3040×2372，一次通过。

## 数据侧（Dayflow 特有，别处可跳过）

Node：`C:/Users/Administrator/AppData/Local/DayflowHome/tools/node24/node.exe`
入口：`C:/Users/Administrator/AppData/Local/DayflowHome/releases/sites29-afdf902-home1/deployment/home.mjs`

```bash
"$NODE" "$APP" client items
```

输出是「一行 JSON 数组 + 一行 diagnostics」，解析时**按行尝试 `json.loads`，取第一个以 `[` 开头的行**。

事项字段：`date` / `start` / `end` / `endDate` / `allDay` / `category` / `status` / `title` / `notes` / `version`。

**跨日事项的判别**：`allDay=true`，或「有 `endDate` 但没有 `start`」。这类（如「杭州考察」10/27–10/28）
走顶部横幅泳道，横跨对应列，不进时间轴。

## 版面参数（已验证）

`START_H=7, END_H=22, PX_H=58, LEFT=90, COLW=200` → 画布 1520×1186（@2x = 3040×2372）

配色：work `#3b82f6`/`#eff6ff`，sport `#f97316`/`#fff7ed`，side `#a855f7`/`#faf5ff`，life `#14b8a6`/`#f0fdfa`；
全天横幅 `linear-gradient(90deg,#2563eb,#3b82f6)` 白字。字体 `"Microsoft YaHei"`（无方块字）。

生成器：`scripts/render_week_html.py <items.json> <out.html> [周一日期]`

## 实际跑通的截图调用

```python
import shutil
new_tab("file:///C:/Users/Administrator/AppData/Local/Temp/week_cal.html"); wait_for_load()
cdp('Emulation.setDeviceMetricsOverride', width=1520, height=1186, deviceScaleFactor=2, mobile=False)
pth = capture_screenshot()      # -> C:\Users\Administrator\.config\browser-harness\tmp\shot.png
shutil.copyfile(pth, r"D:\Workspace\week_calendar_20261026.png")   # ASCII 名
```

随后 PNG 头 16–24 字节读出尺寸核对：`struct.unpack(">II", head[16:24])` → `(3040, 2372)`。

## 这一轮踩到的两处（第一版被用户看到的缺陷）

1. **周一 08:30 那条 10 分钟事项标题全被裁**（色块只有 10px 高）
   → 最小块高提到 50px + `.short` 样式，并在图例写「该条实际只有 10 分钟，为看清标题做了加高」。
2. **长标题被 ellipsis 截断**（「设计部室内精装修+H地块…」）
   → 去掉 `nowrap`，允许换行；列宽 200px / 13px 字号约 13 字一行。

另外视觉模型两次把「周三」读成「周二」、把「周四」读成「周三」——**列对齐必须用
`getBoundingClientRect` 对比列头，不能问图像模型**。

## 交付时的说明口径（用户接受）

- 数据来源：Dayflow 云端库、覆盖哪几天
- 跨日事项为什么是横幅
- 哪条被加高了、为什么
- 本周一共几条、哪几天是空的
- 图上一眼看出的冲突/待确认点（例：周三 18:00 打球但当天在杭州出差）
