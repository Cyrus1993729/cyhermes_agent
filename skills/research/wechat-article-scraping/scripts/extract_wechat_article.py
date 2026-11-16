# -*- coding: utf-8 -*-
"""extract_wechat_article.py — 微信文章（mp.weixin.qq.com/s/xxx）离线 HTML → Markdown

用法：
    curl -s --noproxy '*' 'https://mp.weixin.qq.com/s/xxx' \
      -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' \
      -o wx.html
    python extract_wechat_article.py wx.html out.md https://mp.weixin.qq.com/s/xxx

产出：
  · 元数据头（标题/公众号/公众号ID/作者/发布时间/原文链接/图片数）
  · 正文（段落 + 小标题分层 + [图片] 占位）
  · 文中图片原始链接清单
  · 终端打印：元数据 JSON + 缺句校验结果

为什么要这个脚本：`web_extract` 抓微信文章会**静默截断**正文（2026-11-12 实测 4277 字 vs
实际 4533 字，停在句子中间且不报错）。正式交付一律走「curl 全文 + 本脚本 + 缺句校验」。
"""
import datetime
import html as H
import json
import os
import re
import sys
from html.parser import HTMLParser

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(SRC)[0] + '.md'
URL = sys.argv[3] if len(sys.argv) > 3 else ''

raw = open(SRC, encoding='utf-8', errors='ignore').read()
if len(raw) < 50_000:
    print('!! HTML 只有 %d 字节，大概率是被 UA 拦截的空壳页（正常 1-4 MB）。换 Chrome UA 重下。' % len(raw))


def var(name):
    m = re.search(r'var\s+%s\s*=\s*"([^"]*)"' % name, raw)
    if m:
        return H.unescape(m.group(1))
    m = re.search(r"%s\s*[:=]\s*'([^']*)'" % name, raw)
    return H.unescape(m.group(1)) if m else ''


def inner(pattern):
    m = re.search(pattern, raw, re.S)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''


title = var('msg_title')
nickname = var('nickname')
js_name = inner(r'<a[^>]*id="js_name"[^>]*>(.*?)</a>')
author = inner(r'<span[^>]*id="js_author_name"[^>]*>(.*?)</span>')
user_name = var('user_name')
ct = var('create_time')
try:
    dt = datetime.datetime.fromtimestamp(int(ct)).strftime('%Y-%m-%d %H:%M')
except Exception:
    dt = ''

class _Extract(HTMLParser):
    """按 div 深度计数截取 #js_content —— 不用 `(.*?)</div>\\s*<script`。

    🔴 2026-11-12: 那个非贪婪正则会在正文里第一个「</div><script」处提前闭合，
    且**不报错**（外面看是「提取成功」，实际后半篇没了）。深度计数才可靠。
    """
    VOID = {'br', 'img', 'hr', 'meta', 'link', 'input', 'source'}
    BLOCK = {'p', 'section', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'li',
             'blockquote', 'tr', 'figure'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.inside = False
        self.done = False
        self.buf = []
        self.imgs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.inside:
            if a.get('id') == 'js_content':
                self.inside, self.depth = True, 1
            return
        if self.done:
            return
        if tag not in self.VOID:
            self.depth += 1
        if tag == 'img':
            u = a.get('data-src') or a.get('src') or ''
            if u.startswith('http'):
                self.imgs.append(u.replace('&amp;', '&'))
            self.buf.append('\n[图片]\n')
        elif tag == 'br':
            self.buf.append('\n')
        elif tag in self.BLOCK:
            self.buf.append('\n')

    def handle_endtag(self, tag):
        if not self.inside or self.done:
            return
        if tag not in self.VOID:
            self.depth -= 1
            if self.depth <= 0:
                self.done = True
                return
        if tag in self.BLOCK:
            self.buf.append('\n')

    def handle_data(self, data):
        if self.inside and not self.done:
            self.buf.append(data)

    def text(self):
        return ''.join(self.buf)


_ep = _Extract()
_ep.feed(raw)
body = _ep.text()
imgs = _ep.imgs
# 微信表情图不是内容图，剔除（否则「图片数」虚高、文末清单全是表情）
imgs = [u for u in imgs if 'res.wx.qq.com' not in u]
print('body_len', len(body))

t = body
t = H.unescape(t).replace('\u200b', '').replace('\xa0', ' ')
lines = [ln.strip() for ln in t.split('\n')]
lines = [ln for ln in lines if ln]
DROP = {'预览时标签不可点', '微信扫一扫关注该公众号', '继续滑动看下一个',
        '轻触阅读原文', '向上滑动看下一个'}
lines = [ln for ln in lines if ln not in DROP]

# ---- 分层：文首目录转列表，正文章节转 ## / ### ----
# 「一：」和「一、」两种都有；分隔符里必须带「、」，2026-11-12 第三篇就栽在这
SEC = re.compile(r'^([一二三四五六七八九十]{1,2})\s*[：，,:、]')
SUB = re.compile(r'^\d+[\.、]\s*\S')
STEP = re.compile(r'^第[一二三四五六七八九十\d]{1,2}步[\s　]*\S')  # 「第一步 先看清盘子有多大」这类也当小标题

# 文首目录识别：开头连续 N 行章节标题（N≥2）且后面还有章节标题 → 这一整段是目录。
# 🔴 不要用「同一句标题在文末再出现一次」来判：目录常常和正文标题措辞不同
#    （目录「四：运营是执行岗位和维护岗位」vs 正文「四：运营是执行岗位和优化岗位」），会漏判。
toc = set()
i0 = next((i for i, ln in enumerate(lines) if SEC.match(ln)), None)
if i0 is not None and i0 <= 12:
    j = i0
    while j < len(lines) and SEC.match(lines[j]):
        toc.add(j)
        j += 1
    rest = [k for k in range(j, len(lines)) if SEC.match(lines[k])]
    if len(toc) < 2 or not rest:      # 只有一行 / 后面没正文标题 → 不算目录
        toc = set()
out = []
for i, s in enumerate(lines):
    if SEC.match(s):
        out.append(('- ' if i in toc else '## ') + s)
    elif STEP.match(s) and len(s) <= 30:
        out.append('### ' + s)
    elif SUB.match(s) and len(s) <= 26 and s[-1] in '。？' and '元' not in s:
        out.append('### ' + s)
    else:
        out.append(s)
body_md = re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()

head = ['# %s' % (title or '(无标题)'), '',
        '> 公众号：%s（%s）' % (js_name or nickname, user_name),
        '> 作者：%s' % (author or '（未标注）'),
        '> 发布时间：%s' % (dt or '（未取到）'),
        '> 原文链接：%s' % (URL or '（未提供）'),
        '> 抓取时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        '> 图片数：%d' % len(imgs), '', '---', '']
doc = '\n'.join(head) + body_md + '\n'
if imgs:
    doc += '\n---\n\n## 文中图片链接（按出现顺序）\n\n'
    doc += ''.join('%d. %s\n' % (i, u) for i, u in enumerate(imgs, 1))

open(OUT, 'w', encoding='utf-8').write(doc)

# ---- 缺句校验 ----
plain = re.sub(r'\s+', '', re.sub(r'[\u200b\xa0]', '', H.unescape(re.sub(r'<[^>]+>', '', body))))
docn = re.sub(r'\s+', '', doc)
missing = [s for s in re.split(r'[。！？\n]', plain) if len(s) >= 8 and s not in docn]

print('chars', len(doc), 'imgs', len(imgs))
print('缺句校验：疑似缺失 %d 段（因 ## / - 前缀断开的属假阳性，扫一遍即可）' % len(missing))
for s in missing[:10]:
    print('   ?', s[:60])
print(json.dumps({'title': title, 'js_name': js_name, 'author': author,
                  'create_time': dt, 'user_name': user_name,
                  'saved': OUT}, ensure_ascii=False, indent=1))
