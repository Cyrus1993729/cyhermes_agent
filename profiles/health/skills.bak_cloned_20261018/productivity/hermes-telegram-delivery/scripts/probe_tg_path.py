#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""线路抖动定位探针：是整条线路在丢，还是只有某一个目标在丢？

用法（在 hermes venv 或任意 python3.8+ 下跑）：
    python probe_tg_path.py                        # 默认 80 样本 / 15 并发
    python probe_tg_path.py --samples 400 --workers 20
    python probe_tg_path.py --targets "name=url" "name2=url2"

核心判据（2026-10-08 实测经验）：
  * 串行小样本（~50 次）看不到 ~1% 的失败率 —— **至少 300-400 次采样再下结论**
  * 必须带对照站点，否则分不清「线路 / 目标 / 单点」
  * 失败率不随并发变化 = 每条新连接固定失败概率（不是限流/拥塞）

逐 IP 定位（怀疑某个 IP）需要改写 Host + SNI，本脚本不覆盖，
见 references/bot-api-ip-routing-diagnosis.md 第六步的 httpx 写法。
"""
import argparse
import collections
import json
import ssl
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROXY = "http://127.0.0.1:10808"

DEFAULT_TARGETS = [
    ("api.telegram.org", "https://api.telegram.org/"),
    ("core.telegram.org", "https://core.telegram.org/"),
    ("telegram.org", "https://telegram.org/"),
    ("t.me", "https://t.me/"),
    ("www.google.com(对照)", "https://www.google.com/"),
    ("api.github.com(对照)", "https://api.github.com/"),
]

_lock = threading.Lock()


def classify(exc):
    """把异常分成可读的类别；URLError 的原因才是真错（SSLError/TimeoutError...）。"""
    reason = getattr(exc, "reason", None)
    if reason is not None:
        return f"{type(exc).__name__}({type(reason).__name__})"
    return type(exc).__name__


def probe(url, proxy, timeout):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
    )
    try:
        opener.open(url, timeout=timeout).read()
        return "ok"
    except urllib.error.HTTPError:
        return "ok"  # 4xx/5xx 说明连接与握手都成功了
    except Exception as exc:  # noqa: BLE001 - 分类统计就是目的
        return classify(exc)


def measure(url, samples, workers, proxy, timeout):
    counter = collections.Counter()

    def one(_):
        result = probe(url, proxy, timeout)
        with _lock:
            counter[result] += 1

    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, range(samples)))
    return counter, time.time() - started


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default=PROXY)
    ap.add_argument("--samples", type=int, default=80)
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--targets", nargs="*", default=None,
                    help="name=url 或直接 url；缺省用默认对照集")
    args = ap.parse_args()

    if args.targets:
        targets = []
        for item in args.targets:
            name, _, url = item.partition("=")
            targets.append((name, url) if url else (name, name))
    else:
        targets = DEFAULT_TARGETS

    print(f"代理 {args.proxy} | 每目标 {args.samples} 次 | 并发 {args.workers}\n")
    print(f"{'目标':26s} {'成功':>5s} {'失败':>5s} {'失败率':>7s} {'耗时':>7s}  明细")
    worst = 0.0
    for name, url in targets:
        counter, elapsed = measure(url, args.samples, args.workers,
                                   args.proxy, args.timeout)
        ok = counter.pop("ok", 0)
        bad = sum(counter.values())
        rate = bad / max(1, ok + bad)
        worst = max(worst, rate)
        print(f"{name:26s} {ok:5d} {bad:5d} {rate:7.1%} {elapsed:6.1f}s  {dict(counter)}")

    print()
    if worst >= 0.02:
        print(f"→ 最高失败率 {worst:.1%}：存在真实丢连接问题，"
              f"对比各目标即可判断是线路还是单点（详见 references）。")
    else:
        print(f"→ 全部目标失败率 <2%（最高 {worst:.1%}）。"
              f"但注意：样本 <300 时不足以断定『线路干净』。")


if __name__ == "__main__":
    main()
