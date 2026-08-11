#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日报投递健康检查 (cron no_agent 模式: stdout 非空才投递, 空=静默)
用法: python healthcheck_daily.py --five | --cb
- --five: 检查五类财经日报 (9:30 cron) 输出 + 热榜数据源新鲜度
- --cb:   检查跨境日报 (16:00 cron) 存档 + 垂直源数据新鲜度
- 两者都检查: 当天 gateway.log 的 TG 网络断连次数 (投递风险提示)
"""
import os, sys, json, glob, datetime, subprocess

MODE = None
if '--five' in sys.argv:
    MODE = 'five'
elif '--cb' in sys.argv:
    MODE = 'cb'
if MODE is None:
    print('usage: healthcheck_daily.py --five|--cb')
    sys.exit(0)

now = datetime.datetime.now()
today = now.strftime('%Y-%m-%d')
alerts = []

GW_LOG = r'C:\Users\Administrator\AppData\Local\hermes\logs\gateway.log'


def fresh(path, max_hours):
    """文件存在且 mtime 在 max_hours 小时内"""
    if not os.path.exists(path):
        return None
    age_h = (now - datetime.datetime.fromtimestamp(os.path.getmtime(path))).total_seconds() / 3600
    return age_h <= max_hours


if MODE == 'five':
    # --- 五类日报 (970113abe8a7) ---
    out_dir = r'C:\Users\Administrator\AppData\Local\hermes\cron\output\970113abe8a7'
    files = [f for f in os.listdir(out_dir) if f.startswith(today)] if os.path.isdir(out_dir) else []
    if not files:
        alerts.append('⚠️ 五类财经日报：今天 9:30 无输出文件（cron 可能未触发/失败）')
    else:
        latest = os.path.join(out_dir, max(files))
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest))
        if (now - mtime).total_seconds() > 3 * 3600:
            alerts.append(f'⚠️ 五类财经日报：最后输出 {mtime:%H:%M}（疑似 9:30 cron 未正常完成）')
        # 数据源新鲜度（排除"无新动态"是否因采集停摆）
        db = rf'D:\Workspace\Projects\TrendRadar\output\news\{today}.db'
        if not fresh(db, 26):
            alerts.append('⚠️ 五类日报数据源异常：热榜库未更新（采集端可能停摆，检查 TrendRadarHourly 计划任务）')
    # TG 断连检查（五类窗口 9:25-10:00）
    tg_err = 0
    if os.path.exists(GW_LOG):
        try:
            r = subprocess.run(['grep', '-c', f'{today} 09:2[5-9].*Telegram network error\\|{today} 09:[3-5][0-9].*Telegram network error', GW_LOG],
                               capture_output=True, text=True)
            tg_err = int(r.stdout.strip() or 0)
        except Exception:
            pass

elif MODE == 'cb':
    # --- 跨境日报 (f4506e87cc69) ---
    arch_md = rf'D:\Workspace\Projects\TrendRadar\archives\crossborder\{today}.md'
    arch_json = arch_md.replace('.md', '.json')
    if not os.path.exists(arch_md):
        alerts.append('⚠️ 跨境日报：今日存档缺失（16:00 cron 可能未触发/失败）')
    else:
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(arch_md))
        if (now - mtime).total_seconds() > 4 * 3600:
            alerts.append(f'⚠️ 跨境日报：存档生成于 {mtime:%H:%M}（疑似 16:00 cron 未正常完成）')
        else:
            try:
                d = json.load(open(arch_json, encoding='utf-8'))
                n = d.get('news_count', 0)
                if n == 0:
                    alerts.append('⚠️ 跨境日报：今日 news_count=0（无候选，检查垂直源采集）')
            except Exception:
                pass
    # 垂直源数据新鲜度
    cb = r'D:\Workspace\Projects\TrendRadar\output\crossborder\cb_candidates.json'
    if not fresh(cb, 26):
        alerts.append('⚠️ 跨境日报数据源异常：cb_candidates.json 未更新（采集端可能停摆，检查 TrendRadarCrossborder 计划任务）')
    # TG 断连检查（跨境窗口 15:55-16:40）
    tg_err = 0
    if os.path.exists(GW_LOG):
        try:
            r = subprocess.run(['grep', '-c', f'{today} 1[5-6]:[0-5][0-9].*Telegram network error', GW_LOG],
                               capture_output=True, text=True)
            tg_err = int(r.stdout.strip() or 0)
        except Exception:
            pass

# TG 断连通用告警
if tg_err > 0:
    alerts.append(f'⚠️ 今天 TG 连接出现 {tg_err} 次断连（节点问题）——日报可能投递失败，若没收到请告诉我补发')

if alerts:
    print('📋 日报投递健康检查')
    for a in alerts:
        print(a)
    print('---')
    print('（此消息仅异常时出现；已收到日报则可忽略网络提示）')
