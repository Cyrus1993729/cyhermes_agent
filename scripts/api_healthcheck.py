#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenCode Go (deepseek-v4-flash) API 健康检查 (cron no_agent 模式: 慢/失败才告警, 正常静默)
测真实生成延迟: >30s 或请求失败 → 输出告警。
2026-08-16 迁移: DeepSeek 官方 API → OpenCode Go 套餐 (https://opencode.ai/zen/go/v1, 走代理 7897)
2026-08-17 改进: ①失败后 3s 重试一次(瞬时故障不打扰, 用户策略"先重试不轻易兜底") ②告警带 HTTP 状态码+响应体(区分 401/403/429/5xx) ③去掉误导性的"日报已切 qwen3.7-max 兜底"文案(本脚本不切任何东西, 日报引擎切换由 cron prompt 的 api_probe 判定负责)
"""
import sys, time, json, urllib.request, urllib.error

KEY_PATH = r'C:\Users\Administrator\Desktop\各类api key\opencode go api key.txt'
THRESHOLD = 30  # 秒, 超过视为"慢"
API_URL = 'https://opencode.ai/zen/go/v1/chat/completions'
PROXY = 'http://127.0.0.1:7897'

try:
    key = open(KEY_PATH, encoding='utf-8').read().strip()
except Exception as e:
    print(f'⚠️ API健康检查：无法读取 OpenCode Go key 文件 ({e})')
    sys.exit(0)


def probe(timeout):
    """单次探测。返回 (status, code, elapsed, detail)
    status: 'ok' | 'http' (HTTPError) | 'err' (其他异常)"""
    body = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    }).encode('utf-8')
    proxy_handler = urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json', 'User-Agent': 'curl/8.0.0'},
    )
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return ('ok', resp.status, time.time() - t0, None)
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = e.read().decode('utf-8', errors='replace')[:150]
        except Exception:
            pass
        return ('http', e.code, time.time() - t0, detail)
    except Exception as e:
        return ('err', None, time.time() - t0, str(e)[:150])


def describe(status, code, detail):
    if status == 'ok':
        return f'HTTP {code}'
    if status == 'http':
        return f'HTTP {code} {detail}'.strip()
    return f'{detail}'


s, c, el, d = probe(60)

if s == 'ok':
    # 正常 → 只有慢才告警
    if el > THRESHOLD:
        print(f'⚠️ OpenCode Go API 响应慢：{el:.0f} 秒（阈值 {THRESHOLD}s，重试 1 次确认）。')
    # 否则静默
else:
    # 首次失败 → 3s 后重试 1 次（瞬时故障不打扰用户；连续失败才告警）
    time.sleep(3)
    s2, c2, el2, d2 = probe(30)
    if s2 == 'ok' and el2 <= THRESHOLD:
        pass  # 重试成功 → 瞬时抖动，静默
    else:
        first = describe(s, c, d)
        second = describe(s2, c2, d2) if s2 != 'ok' or el2 > THRESHOLD else f'OK({el2:.0f}s)'
        print(f'⚠️ OpenCode Go API 连测两次异常：首次 {first}；重试 {second}。')
        print('   日报任务会自动重试生成（17:10）并有备用渠道兜底；若此类告警连续多次出现，请排查主链路（网关状态/key/代理）。')