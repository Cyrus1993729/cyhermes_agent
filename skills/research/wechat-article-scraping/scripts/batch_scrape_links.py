#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch_scrape_links.py — 从链接清单批量扒公众号文章，一篇一个 .md

用法：
    python batch_scrape_links.py links.txt --out "C:/Users/Administrator/Desktop" [--date 2026-11-18]

输入 links.txt：每行一个 https://mp.weixin.qq.com/s/xxx
    · 自动清 CRLF（Windows 记事本清单必踩：`\r` 进 URL → curl 静默失败、一个文件都不写）
    · 空行、非 http 行直接跳过

产出：<out>/<抓取日>_<公众号>_<标题>.md（Windows 非法字符已替换）
     每篇打印一行回执：http=200 bytes=3900000 正文字数=4189 -> 文件名

依赖：curl（Win10+ 自带）、同目录的 extract_wechat_article.py
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

CURL_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
BAD = '<>:"/\\|?*'                      # Windows 文件名非法字符
HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, 'extract_wechat_article.py')


def safe(name: str) -> str:
    for c in BAD:
        name = name.replace(c, '＿' if c == '?' else '_')
    return name.strip().rstrip('.')


def fetch(url: str, dst_html: str):
    """curl 整页。必须 -sS（裸 -s 会把失败吞掉）并回传 http_code/size。"""
    r = subprocess.run(
        ['curl', '-sS', '--noproxy', '*', '--max-time', '60',
         '-H', 'User-Agent: ' + CURL_UA,
         '-o', dst_html, '-w', '%{http_code} %{size_download}', url],
        capture_output=True, text=True)
    out = (r.stdout or '').strip().split()
    code = out[0] if out else 'ERR'
    size = int(out[1]) if len(out) > 1 and out[1].isdigit() else 0
    if r.returncode != 0:
        print('   curl 返回码 %d: %s' % (r.returncode, (r.stderr or '').strip()[:200]))
    return code, size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('links', help='每行一个文章链接的 txt')
    ap.add_argument('--out', default='.', help='落盘目录（默认当前目录）')
    ap.add_argument('--date', default=datetime.date.today().isoformat(), help='文件名前缀日期，默认今天')
    ap.add_argument('--workdir', default=None, help='中间 html/md 缓存目录')
    a = ap.parse_args()

    work = a.workdir or os.path.join(os.environ.get('TEMP') or os.environ.get('TMP') or '.', 'wx_batch')
    os.makedirs(work, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)

    urls = []
    with open(a.links, encoding='utf-8', errors='ignore') as f:
        for line in f:
            u = line.replace('\r', '').strip()
            if u.startswith('http'):
                urls.append(u)
    print('链接数 %d -> 输出目录 %s' % (len(urls), a.out))

    ok = 0
    for i, url in enumerate(urls, 1):
        tag = 'a%02d' % i
        html = os.path.join(work, tag + '.html')
        md = os.path.join(work, tag + '.md')
        code, size = fetch(url, html)
        if size < 50_000:
            print('%s http=%s bytes=%d  !! 体积异常（<50KB，多半被 UA 拦或链接失效）%s' % (tag, code, size, url))
            continue
        subprocess.run([sys.executable, EXTRACT, html, md, url], capture_output=True, text=True)
        if not os.path.exists(md):
            print('%s 提取失败（extract_wechat_article.py 未产出）%s' % (tag, url))
            continue
        text = open(md, encoding='utf-8').read()
        title = next((l[2:].strip() for l in text.split('\n') if l.startswith('# ')), tag)
        m = re.search(r'公众号：(.+?)（', text)
        acct = m.group(1) if m else '未知公众号'
        body = re.sub(r'^>.*$', '', text, flags=re.M).replace('[图片]', '')
        n = len(re.sub(r'\s', '', body))
        dst = os.path.join(a.out, '%s_%s_%s.md' % (a.date, safe(acct), safe(title)))
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(text)
        ok += 1
        print('%s http=%s bytes=%d 正文%d字 -> %s' % (tag, code, size, n, os.path.basename(dst)))

    print('完成：%d/%d 篇落盘' % (ok, len(urls)))
    if ok < len(urls):
        print('⚠ 有未落盘的篇目，逐行看上面的回执，别直接回报「已全部完成」')
    return 0 if ok == len(urls) else 1


if __name__ == '__main__':
    sys.exit(main())
