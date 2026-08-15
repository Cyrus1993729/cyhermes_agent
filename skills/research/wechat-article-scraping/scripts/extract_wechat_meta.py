#!/usr/bin/env python
"""从下载的微信文章 HTML 中一键提取元数据。

用法:
    curl -s --noproxy '*' 'https://mp.weixin.qq.com/s/xxx' \
      -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' \
      -o wx_article.html
    python extract_wechat_meta.py wx_article.html

注意: 不带浏览器 UA 抓到的页面只有 ~2KB（"未知错误，请稍后再试"），提取不到任何字段。
"""
import re
import sys
from datetime import datetime


def main(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        html = f.read()

    m = re.search(r'var\s+user_name\s*=\s*"([^"]+)"', html)
    print("账号ID:", m.group(1) if m else "N/A")

    m = re.search(r'var\s+create_time\s*=\s*"(\d+)"', html)
    if m:
        ts = int(m.group(1))
        print("发布时间:", datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
    else:
        print("发布时间: N/A")

    m = re.search(r'id="js_name"[^>]*>\s*([^<]+?)\s*<', html)
    print("公众号:", m.group(1).strip() if m else "N/A")

    m = re.search(r'id="js_author_name"[^>]*>\s*([^<]+?)\s*<', html)
    print("作者:", m.group(1).strip() if m else "N/A")

    m = re.search(r'<h1[^>]*id="activity-name"[^>]*>\s*([^<]+?)\s*<', html)
    print("标题:", m.group(1).strip() if m else "N/A")

    m = re.search(r'var\s+__biz\s*=\s*"([^"]+)"', html) or re.search(r'var\s+biz\s*=\s*"([^"]+)"', html)
    print("biz:", m.group(1) if m else "N/A")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
