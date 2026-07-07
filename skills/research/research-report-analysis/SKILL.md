---
name: research-report-analysis
description: 分析图像型/扫描版 PDF 研报（投行报告、Chartbook 等）。系统化流程：文件定位→目录导航→逐页视觉识别→定位目标内容。适用于投资研究场景中需要从大型 PDF 中提取特定数据/图表的任务。
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [pdf, investment, vision, research, chartbook]
---

# Research Report Analysis

图像型 PDF 研报的系统化分析流程。适用于摩根士丹利、J.P. Morgan、中金等投行研报（通常为扫描版，文字不可直接提取）。

## 触发条件

- 用户上传 PDF 研报并询问具体内容
- 需要在大型 Chartbook 中定位特定图表/数据
- PDF 文字提取失败（PyPDF2/pdfplumber 返回空）需要回退到视觉识别

## 工作流

### 1. 文件定位

Windows 上投行研报文件名常含全角字符（`：` U+FF1A），用精确路径传给 PyMuPDF 会失败。

```python
import os, glob

# 用 os.listdir + 子串匹配，不要用精确路径
desktop = os.path.expanduser('~/Desktop/pdf')
for f in os.listdir(desktop):
    if 'J.P. Morgan' in f:  # 子串匹配
        pdf_path = os.path.join(desktop, f)
```

### 2. 判断 PDF 类型

```python
import fitz
doc = fitz.open(pdf_path)

# 验证是否图像型
page = doc[0]
text = page.get_text()
if not text.strip() or len(text) < 50:
    # 图像型 PDF → 走视觉识别
else:
    # 文字型 PDF → 可直接搜索
```

### 3. 确定搜索范围

先读目录页（通常第 2-3 页），了解报告结构，锁定目标章节。

```python
# 批量转换目标章节页面为图片
pix = page.get_pixmap(dpi=150)  # 150 DPI 足够 OCR 识别
pix.save(f'page_{i+1}.png')
```

- **DPI 选择**: 150 适合文字识别；200+ 适合精细图表
- **文件大小参考**: 150 DPI，A4 页面约 300KB-2MB

### 4. 逐页视觉搜索

用 `vision_analyze` 逐页提取，每次携带关键词提示：

```
"提取所有文字。关注是否涉及['关键词1', '关键词2']相关内容。"
```

**策略**：
- 目录页 → 锁定章节范围（如 "2. Sales"）
- 跳过明显不相关的章节首尾页
- 在目标章节内逐页排查
- 命中后提取详细内容

### 5. 深度提取

定位到目标页面后，追加详细提取请求：

```
"请尽可能详细地提取这一页的所有内容：
1. 左上角图表的标题、数据点、趋势
2. 右上角图表的标题和数据
3. 底部注释的完整文字
4. 所有数据来源标注"
```

## YouTube 辅助

投行研报常有 YouTuber 做讲解。获取字幕辅助定位：

```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import ProxyConfig

class MyProxy(ProxyConfig):
    def to_requests_dict(self):
        return {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}

api = YouTubeTranscriptApi(proxy_config=MyProxy())
transcript_list = api.list(video_id)
```

**注意**: YouTube 可能因 IP 封锁拒绝请求。优先直接分析 PDF，YouTube 仅作辅助参考。

## 备选 YouTube 方案

```bash
yt-dlp --skip-download --write-auto-subs --sub-lang zh-Hans,zh,en \
  --proxy 127.0.0.1:7897 --cookies-from-browser chrome \
  -o output "https://youtu.be/VIDEO_ID"
```

## 依赖

```bash
uv pip install PyMuPDF youtube-transcript-api
```

## 常见研报结构

| 投行 | 典型结构 |
|:---|:---|
| J.P. Morgan Chartbook | 封面→目录→National forecast→Sales→Where's bottom?→Construction→Supply→Policy→Risk→Long-term |
| Morgan Stanley | 封面→摘要→正文分析→相关报告→披露 |

## 陷阱

| 陷阱 | 解决 |
|:---|:---|
| PyMuPDF 提示文件不存在 | 文件名含全角字符 → 用 os.listdir + 子串匹配 |
| pdfplumber/PyPDF2 返回空文本 | 图像型 PDF → 用 fitz 转图片 + vision_analyze |
| pdf2image 报 poppler 缺失 | 用 PyMuPDF (`fitz`) 代替，无需 poppler |
| YouTube 字幕 API 被封锁 | 先试直连，不行就走代理 + ProxyConfig 子类 |
| 67 页 Chartbook 逐页看太慢 | 先看目录→锁定章节→只转换目标章节页面 |
