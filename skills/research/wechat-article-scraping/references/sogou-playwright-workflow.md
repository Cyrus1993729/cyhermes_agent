# Sogou + Playwright 搜狗搜微信文章 — 完整工作流

## 环境准备

```bash
uv pip install playwright
# 不需要 playwright install chromium — 用系统已安装的 Chrome
```

## 关键发现

1. **搜狗页面是纯 JS 渲染**：curl/requests 静态请求拿不到任何结果，必须用 Playwright
2. **文章链接在 `.txt-box h3 a`** 元素中，href 是搜狗加密跳转 `/link?url=...`
3. **跳转后到达 `mp.weixin.qq.com/s?src=11&timestamp=...&signature=...`** 签名链接
4. **跳转 token 有时效性**：必须在同一次 Playwright 会话中立即跟随跳转
5. **翻页 URL 格式**：`?query=...&page=2&ie=utf8`

## 工作脚本模板

### 脚本 1：合并搜索+跳转（获取文章列表+真实 URL）

```python
"""Combined: search + immediate redirect following in same session."""
import asyncio
import json
import os
import re
import sys
sys.stdout.reconfigure(line_buffering=True)
from playwright.async_api import async_playwright

QUERY = "公众号名称"          # ← 改这里
OUTPUT_DIR = "C:/Users/Administrator/output"
MAX_PAGES = 3
NOISE_KEYWORDS = []           # ← 加噪音关键词

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        
        all_articles = []
        seen_titles = set()
        
        for pagenum in range(1, MAX_PAGES + 1):
            search_url = f"https://weixin.sogou.com/weixin?type=2&s_from=input&query={QUERY}&ie=utf8&page={pagenum}"
            
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            
            if 'antispider' in page.url.lower() or '验证' in await page.title():
                break
            
            links = await page.query_selector_all('.txt-box h3 a, .news-list2 li .txt-box h3 a')
            if not links:
                links = await page.query_selector_all('h3 a[href*="link?url="]')
            if not links:
                break
            
            page_articles = []
            for link in links:
                title = (await link.inner_text()).strip()
                href = await link.get_attribute('href')
                if not title or not href or title in seen_titles:
                    continue
                seen_titles.add(title)
                page_articles.append({'title': title, 'href': href})
            
            for art in page_articles:
                if any(kw in art['title'] for kw in NOISE_KEYWORDS):
                    continue
                
                full_url = f"https://weixin.sogou.com{art['href']}" if art['href'].startswith('/') else art['href']
                
                try:
                    await page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2000)
                    
                    if 'antispider' in page.url.lower():
                        continue
                    
                    if 'mp.weixin.qq.com' in page.url:
                        content = await page.content()
                        
                        biz_match = re.search(r'var\s+biz\s*=\s*"([^"]+)"', content)
                        ct_match = re.search(r'var\s+ct\s*=\s*["\']?(\d+)["\']?', content)
                        if not ct_match:
                            ct_match = re.search(r'create_time\s*=\s*["\']?(\d+)["\']?', content)
                        
                        article_data = {
                            'title': art['title'],
                            'mp_url': page.url,
                            'biz': biz_match.group(1) if biz_match else None,
                            'create_time': int(ct_match.group(1)) if ct_match else None,
                        }
                        all_articles.append(article_data)
                        
                except Exception as e:
                    print(f"Error: {e}")
                
                await asyncio.sleep(1)
            
            await asyncio.sleep(3)
        
        await browser.close()
        
        # 保存结果
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, 'articles.json'), 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        # 按 biz 过滤（保留目标公众号的文章）
        target_biz = all_articles[0]['biz'] if all_articles else None
        if target_biz:
            filtered = [a for a in all_articles if a.get('biz') == target_biz]

if __name__ == "__main__":
    asyncio.run(main())
```

### 脚本 2：逐篇抓取正文

```python
"""Extract article content from mp.weixin.qq.com pages."""
import asyncio
import json
import os
import re
from datetime import datetime
from playwright.async_api import async_playwright

INPUT_FILE = "articles.json"
OUTPUT_DIR = "./articles"

def clean_html(html):
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome", headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        for i, article in enumerate(articles):
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            
            title = article['title']
            url = article['mp_url']
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 正文在 #js_content 中
            elem = await page.query_selector('#js_content')
            raw_html = await elem.inner_html() if elem else ""
            
            if not raw_html:
                elem = await page.query_selector('.rich_media_content')
                raw_html = await elem.inner_html() if elem else ""
            
            clean_text = clean_html(raw_html)
            
            if clean_text and len(clean_text) > 50:
                # 保存为 Markdown
                dt = datetime.fromtimestamp(article.get('create_time', 0)).strftime('%Y-%m-%d')
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]
                md_file = os.path.join(OUTPUT_DIR, f"{i+1:02d}_{dt}_{safe_title}.md")
                
                md_content = f"# {title}\n\n**日期**: {dt}\n**来源**: 微信公众号\n\n---\n\n{clean_text}\n"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
            
            await context.close()
            await asyncio.sleep(1.5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 过滤搜狗噪音的策略

### 方法1：biz 验证（推荐）
跟随跳转后从页面源码提取 `var biz`，与已知目标公众号 biz 对比：
```python
biz_match = re.search(r'var\s+biz\s*=\s*"([^"]+)"', content)
if biz_match and biz_match.group(1) == TARGET_BIZ:
    # 确认为目标公众号文章
```

### 方法2：噪音关键词黑名单（快速但不够通用）
```python
NOISE_KEYWORDS = ['补阳还五汤', '停杯投箸', '茶境一味', ...]
if any(kw in title for kw in NOISE_KEYWORDS):
    skip  # 跳过不相关文章
```

## 常见问题

### 后台进程无输出
即使加了 `python -u` 和 `sys.stdout.reconfigure(line_buffering=True)`，后台进程可能仍无输出。改用**前台模式 + 充足超时**：
```bash
python -u scraper.py 2>&1  # 前台，timeout=300
```

### Chrome profile 锁定
```python
# 如果用户正在使用 Chrome，这会失败
context = await p.chromium.launch_persistent_context(
    user_data_dir=r"%LOCALAPPDATA%\Google\Chrome\User Data",
    channel="chrome",
)
# 改用默认临时 profile + 用户手动登录 mp.weixin.qq.com
```

### 搜狗反爬检测
- 随机页间延迟 2-4 秒
- 每个文章使用新的 browser context
- 反爬触发后等待 8-10 秒
- URL 中的 token 参数每次请求都在变化，这说明 token 是动态生成的
