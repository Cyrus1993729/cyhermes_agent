# -*- coding: utf-8 -*-
"""Fetch a URL and print clean text (fallback for unregistered extract backend).
Usage: python fetch.py <url> [max_chars]"""
import sys, io, re, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fetch(url, timeout=45):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    # decode: try utf-8, then gbk
    for enc in ('utf-8', 'gbk', 'gb18030'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')

def clean(html):
    html = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', html)
    html = re.sub(r'(?s)<!\[CDATA\[.*?\]\]>', ' ', html)
    html = re.sub(r'(?s)<!--.*?-->', ' ', html)
    html = re.sub(r'<br\s*/?>', '\n', html)
    html = re.sub(r'</(p|div|h[1-6]|li|tr|section)>', '\n', html)
    html = re.sub(r'<[^>]+>', '', html)
    html = re.sub(r'&nbsp;?', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'&quot;', '"', html)
    html = re.sub(r'[ \t]+', ' ', html)
    lines = [l.strip() for l in html.split('\n') if l.strip()]
    return '\n'.join(lines)

if __name__ == '__main__':
    url = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 16000
    try:
        text = clean(fetch(url))
        print(f"URL: {url}\nCHARS: {len(text)}\n{'='*60}")
        print(text[:n])
    except Exception as e:
        print(f"ERR {url}: {e}")