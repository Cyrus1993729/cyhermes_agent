#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""跨境日报投递员（方案 C：生成与投递分离，no_agent cron 用）
调度: 20:45（cron "45 20 * * *"）
行为:
  - 草稿 _draft_cb.txt 今天生成且未投递 → stdout = 日报全文（原样投递）+ 写投递标记
  - 已投递（草稿 mtime == 标记）→ stdout 空（静默，防重复投递）
  - 草稿缺失/过期但存档今天存在 → 读存档投递（兜底）
  - 全部缺失: 20:40 之后 → stdout = 显式告警（大声失败）；20:30 时段 → 静默（生成任务可能仍在运行）
投递守卫（方案 D③）: 正常日报须 ≥5000 字符且以 ⚡ 开头；无新动态日（<2000 字符且含"无新动态"）也允许投递；内容异常 → 告警不投递。
"""
import datetime
import os
import sys

DRAFT = r"D:\Workspace\Projects\TrendRadar\output\_draft_cb.txt"
MARK = r"D:\Workspace\Projects\TrendRadar\output\_cb_delivered.txt"
ARCHIVE = r"D:\Workspace\Projects\TrendRadar\archives\crossborder\{date}.md"
MIN_LEN = 5000


def is_today(path):
    if not os.path.exists(path):
        return False
    return datetime.date.fromtimestamp(os.path.getmtime(path)) == datetime.date.today()


def mark_mtime():
    try:
        return open(MARK, encoding="utf-8").read().strip()
    except Exception:
        return ""


def deliver(path):
    """校验并输出日报内容。返回 True=已投递（写标记），False=内容异常。"""
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception as e:
        print(f"⚠️ 日报读取失败: {path} ({e})")
        return True  # 已尝试，避免下次重复报错

    stripped = txt.lstrip()
    normal = len(txt) >= MIN_LEN and stripped.startswith("⚡")
    empty_day = len(txt) < 2000 and "无新动态" in txt
    if normal or empty_day:
        open(MARK, "w", encoding="utf-8").write(str(os.path.getmtime(path)))
        sys.stdout.write(txt)
        return True
    print(f"⚠️ 日报内容异常（长度 {len(txt)}，header '{stripped[:10]}'），未投递: {path}")
    return True


def main():
    now = datetime.datetime.now()

    # 1) 草稿优先
    if is_today(DRAFT):
        cur = str(os.path.getmtime(DRAFT))
        if mark_mtime() != cur:  # 未投递过本次内容
            deliver(DRAFT)
        return  # 已投递或已处理 → 静默

    # 2) 存档兜底（草稿缺失/过期时）
    arch = ARCHIVE.format(date=datetime.date.today().isoformat())
    if is_today(arch):
        cur = str(os.path.getmtime(arch))
        if mark_mtime() != cur:
            deliver(arch)
        return

    # 3) 全部缺失
    if now.hour >= 20 and now.minute >= 40:
        print("⚠️ 跨境日报生成失败：草稿与存档均缺失或过期（20:30 生成任务未产出，请检查）")
    # 20:30 时段且缺文件 → 静默（生成任务可能还在运行，20:45 会自动检查）


if __name__ == "__main__":
    main()
