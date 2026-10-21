# HTML → PNG 渲染（Windows + 中国网络）

## 问题

`playwright install chromium` 在国内失败：npmmirror CDN 缺版本（404）、Azure 源返回 400。

## 解决方案

使用系统自带 Edge，不额外下载 Chromium：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 800, "height": 600})
    page.goto(f"file:///{html_path}", wait_until="networkidle")
    full_height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": 800, "height": full_height})
    page.screenshot(path=png_path, full_page=True)
    browser.close()
```

安装：`pip install playwright`（不需要 `playwright install chromium`）

## 报告排版偏好

用户偏好多卡片式布局（深色主题、每标的独立卡片、估值颜色标签），不偏好 `<pre>` 标签直接灌文本。参考 `C:\Users\Administrator\Desktop\存储产业链深度研究_v2.html`。
