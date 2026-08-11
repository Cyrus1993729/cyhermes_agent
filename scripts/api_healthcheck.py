#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DeepSeek API 健康检查 (cron no_agent 模式: 慢/失败才告警, 正常静默)
测真实生成延迟: >30s 或请求失败 → 输出告警。cron 任务已配置 qwen3.7-max 兜底。
"""
import sys, time, json, urllib.request

KEY_PATH = r'C:\Users\Administrator\Desktop\各类api key\deepseek api key.txt'
THRESHOLD = 30  # 秒, 超过视为"慢"

try:
    key = open(KEY_PATH, encoding='utf-8').read().strip()
except Exception as e:
    print(f'⚠️ API健康检查：无法读取 DeepSeek key 文件 ({e})')
    sys.exit(0)

body = json.dumps({
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 5,
}).encode('utf-8')

req = urllib.request.Request(
    'https://api.deepseek.com/v1/chat/completions',
    data=body,
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
)

t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        elapsed = time.time() - t0
        if resp.status != 200:
            print(f'⚠️ DeepSeek API 异常：HTTP {resp.status}。日报已切 qwen3.7-max 兜底，无需操作。')
        elif elapsed > THRESHOLD:
            print(f'⚠️ DeepSeek API 响应慢：{elapsed:.0f} 秒（阈值 {THRESHOLD}s）。日报已切 qwen3.7-max 兜底，无需操作。')
        # 正常 → 静默
except Exception as e:
    print(f'⚠️ DeepSeek API 不可用：{type(e).__name__}。日报已切 qwen3.7-max 兜底，无需操作。')
