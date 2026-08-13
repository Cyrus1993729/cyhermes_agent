#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DeepSeek 延迟探测（日报 cron 第 0 步用）
输出格式（供 agent 判断）:
  OK <秒>     → 正常，继续用当前模型
  SLOW <秒>   → 超过阈值（30s），应切换 qwen 引擎
  ERROR <原因> → 不可用/超时，应切换 qwen 引擎
阈值 30s：正常日延迟 2-15s，过载日 60-265s（8/10、8/12 实测）。
探测请求带 25s 超时，DeepSeek 慢时不会拖住日报任务。
"""
import sys, time, json, urllib.request

KEY_PATH = r'C:\Users\Administrator\Desktop\各类api key\deepseek api key.txt'
THRESHOLD = 30.0  # 秒

try:
    with open(KEY_PATH, encoding='utf-8') as f:
        key = f.read().strip()
except Exception as e:
    print(f'ERROR 无法读取 DeepSeek key 文件: {e}')
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
    with urllib.request.urlopen(req, timeout=25) as resp:
        elapsed = time.time() - t0
        if resp.status == 200 and elapsed <= THRESHOLD:
            print(f'OK {elapsed:.1f}')
        else:
            print(f'SLOW {elapsed:.1f} http={resp.status}')
except Exception as e:
    print(f'ERROR {type(e).__name__}')
