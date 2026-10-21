# Playwright + Edge Fallback (China / GFW)

## Problem

`playwright install chromium` fails in China because:
- Default CDN `cdn.npmmirror.com` (npm mirror) often returns 404 for the specific Chromium build version
- Official CDN `playwright.azureedge.net` is blocked/returns GatewayExceptionResponse through proxy

## Solution: Use system Edge browser

On Windows, Microsoft Edge is pre-installed. Playwright supports it via the `channel` parameter — no separate Chromium download needed.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="msedge",   # use system Edge, not downloaded Chromium
        headless=True
    )
    page = browser.new_page(viewport={"width": 800, "height": 600})
    page.goto("file:///C:/path/to/file.html", wait_until="networkidle")
    
    # Full page screenshot
    page.screenshot(path="output.png", full_page=True)
    browser.close()
```

## Installation

```bash
pip install playwright
# SKIP: python -m playwright install chromium
# Use Edge instead — no browser download needed
```

## Edge Path on Windows

- `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`
- `C:/Program Files/Microsoft/Edge/Application/msedge.exe`

## Pitfalls

- Edge channel may not support all Chromium flags — test `headless=True` first
- Full-page screenshots need `page.evaluate("document.body.scrollHeight")` to detect height
- File URLs need forward slashes: `file:///C:/Users/...` (not backslash)
