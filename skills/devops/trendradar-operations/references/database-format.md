# TrendRadar 本地 SQLite 数据格式与增量模式局限

## 库结构（output/news/YYYY-MM-DD.db，按天分文件）
- 表 `news_items`：id, title, platform_id, rank, url, mobile_url, first_crawl_time, last_crawl_time, crawl_count
- 表 `platforms`：id, name（platform_id → name 映射）
- 表 `rank_history`：news_item_id, rank, crawl_time（排名轨迹）
- RSS 独立库：output/rss/YYYY-MM-DD.db

## ⚠️ 时间格式坑（实测）
- **first_crawl_time / last_crawl_time 存 `HH-MM`**（无日期，日期在文件名里）
- 跨天窗口过滤必须拼成 `YYYY-MM-DD HH-MM` 再字符串比较（同格式字典序 = 时间序）
- 取"一次全量抓取"：`SELECT MAX(last_crawl_time) FROM news_items` 后按该值过滤

## 增量模式（report_mode: incremental）的局限
- 语义：只推新增新闻（"无新增时不推送"）
- **去重基准是"当天"**（`_detect_new_titles_impl` 用 `_get_today_all_data_impl(current_data.date)` 只查当天库）
- 后果：**每天第一次运行会把当前在榜全部当"新增"推送** → 跨天重复（昨天推过的今天又推）
- 18:00 那次（当天第二次）才真正只推增量
- 这就是为什么要"采集器+AI主编"架构：跨天窗口由 prepare_candidates.py 自己控制（昨天库+今天库合并查重）

## 官方三种 report_mode
| 模式 | 行为 |
|---|---|
| current | 当前在榜最新批次（全量匹配词） |
| daily | 当日全部新闻汇总 |
| incremental | 只推新增（当天基准，跨天局限见上） |

## 官方 timeline 调度（timeline.yaml）
- presets：always_on / morning_evening / office_hours / night_owl / custom
- periods 的 start/end 是"执行窗口"（时间范围内运行才触发对应行为），不是数据窗口
- `once.push: true` = 窗口内只推一次（防重复触发）
- schedule.enabled=false 时 timeline 时间段不生效（--show-schedule 显示"日计划: disabled"）
- 本地模式由计划任务定时触发 `python -m trendradar`，每次跑完退出（无常驻进程）
