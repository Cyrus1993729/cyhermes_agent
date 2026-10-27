# Dayflow 周日程表 → PNG（2026-10-26 实做，可直接复用）

用户原话：「我希望你能做一张图，然后让我更清晰地看到我这一周的日程安排。这个图可以是你读取了我每天的日程表之后再做出来的。然后你做好以后直接通过 Telegram 发给我。」

## 数据侧

```python
# 1) 拉全量，Python 过滤区间 + 剔除 cancelled
r = terminal(f'"{NODE}" "{APP}" client items 2>&1', timeout=120)
for ln in r["output"].strip().splitlines():
    if ln.strip().startswith("["):
        data = json.loads(ln); break          # 后面跟着一行诊断 JSON，只取以 [ 开头的那行
rows = [it for it in data
        if "2026-10-26" <= it.get("date","") <= "2026-11-01"
        and it.get("status") != "cancelled"]   # 取消的必须剔掉
```

拆分规则：

- `allDay is True` 或 (`endDate` 存在且 `start` 为空) → **全天/多日横幅**
- 其余且有 `start` → 时间轴上的事件块

## 布局常量（1520 宽是手机可读的甜点）

```python
START_H, END_H = 8, 24     # 按当周最早/最晚事项定，本例最早 08:25、最晚 23:00
PX_H  = 56                 # 每小时像素
LEFT  = 90                 # 左侧时间轴宽
COLW  = 200                # 每天列宽
W = LEFT + COLW*7 + 30
lane_h = 56 if allday else 0        # 全天横幅带的高度
GH = (END_H-START_H)*PX_H           # 网格高
H  = 150 + lane_h + GH + 110        # 顶部标题 + 周头 + 网格 + 底部图例留白
```

绝对定位：`x = LEFT + day_index*COLW + 6`，`y = (hm(start)-START_H)*PX_H + 2`，
`height = max((hm(end)-hm(start))*PX_H - 4, 50)` — **`max(...,50)` 就是短事件加高那一步**。
`hm(s)` = `int(h)+int(m)/60`。

## 全天/多日横幅

```python
i0 = (date.fromisoformat(it["date"]) - WEEK[0]).days
i1 = (date.fromisoformat(it["endDate"] or it["date"]) - WEEK[0]).days
left  = LEFT + i0*COLW + 5
width = (i1-i0+1)*COLW - 10        # 跨两列时自动覆盖整两列，两侧各留 5px
```

## 重叠检测（同一天两件事时间相交时并排显示）

```python
byday = {}
for it in timed:
    byday.setdefault((date.fromisoformat(it["date"]) - WEEK[0]).days, []).append(it)
for i, lst in byday.items():
    lst.sort(key=lambda x: hm(x["start"])); slots = []
    for it in lst:
        for si, last in enumerate(slots):
            if hm(it["start"]) >= hm(last["end"]) - 1e-9:
                slots[si] = it; it["_col"] = si; break
        else:
            slots.append(it); it["_col"] = len(slots)-1
    for it in lst: it["_ncol"] = len(slots)
# 渲染时：width = (COLW-12)/ncol - 4，x = LEFT + i*COLW + 6 + col*((COLW-12)/ncol)
```

## 配色

```python
COLORS = {"work":("#3b82f6","#eff6ff"),   # 蓝
          "sport":("#f97316","#fff7ed"),  # 橙
          "side":("#a855f7","#faf5ff"),   # 紫
          "life":("#14b8a6","#f0fdfa")}  # 青
# 用法：border-left-color 用深色，background 用浅色
```
周末列头 `color:#e11d48`；时间轴标签 `transform:translateY(-8px)` 对齐网格线。

## 关键 CSS

```css
.ev{position:absolute;border-radius:8px;padding:6px 9px;overflow:hidden;
    border-left:4px solid;line-height:1.28}
.ev .n2{font-size:13px;font-weight:700;margin-top:2px;word-break:break-word}
.ev.short{padding:4px 8px}                 /* 被 max(...,50) 加高的短事件 */
.ev.short .n2{font-size:11.5px;line-height:1.2}
body{font-family:"Microsoft YaHei","Segoe UI",sans-serif}   /* 必须 */
```

**不要用 `white-space:nowrap;text-overflow:ellipsis`** —— 省略号会被读成「信息被截了」。

## 验收（必须做，别靠肉眼/别靠 vision）

用 `js()` 拿 `data-col` / `data-day` 元素的 bounding box，逐条核「事件块中心 x 落在哪一列」+
`scrollHeight > clientHeight+1` 判是否被裁。完整代码见 SKILL.md 第四节。
本次 10 个事件块全部 OK、无错列、无裁剪，一行 `问题项: 无` 就够交付。

⚠️ **vision_analyze 只能用于「整体好不好看」**。本次它两次把「周三的千问培训」读成周二，
还误报三处标题被截断——**照它改就是把对的改错了**。

## 交付话术

图下发三条说明就够：① 数据来源与周次 ② 他可能不知道的取舍（全天事项做成横幅、短事件加高）
③ **需要他拍板的冲突**（如「周三考察到 17:30、18:00 却有打球，取消还是改期？」）。

## 已知的用户节奏

他会在同一周内连续改：加事项 → 取消某项 → 改时段 → 再让重出图。
**每次都要重新拉库重画，不能拿上一版改两笔。**
改完如果当天日程被写回了云端，记得跑 `df_snapshot.py` 刷快照（见 dayflow-personal-planner）。
