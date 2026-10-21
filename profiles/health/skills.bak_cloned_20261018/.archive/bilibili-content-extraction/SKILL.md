---
name: bilibili-content-extraction
description: Extract structured information from B站 (Bilibili) videos when you can't watch them — search, comments, AI summaries, subtitles. Covers API quirks, rate-limiting workarounds, and fallback strategies. For full video understanding (ASR+OCR+AI summary), use bilibili-understand skill (loads video-understand-core pipeline).
---

# B站内容提取 (Bilibili Content Extraction)

When you need to extract structured information (store names, dishes, prices, reviews) from B站 videos
but can't watch them directly. Use B站 APIs to gather metadata, comments, AI summaries, and subtitles
as proxy data sources.

## ⚡ Quick routing: full video understanding vs targeted extraction

**If the user wants to fully understand a video (audio + visual, timestamps, structured summary):**
→ Use the **self-built AI pipeline** (see `references/ai-video-pipeline.md`).

  **Canonical pipeline (architecture decision 2026-06-15, reviewed by Claude Opus 4.8):**
  ```
  bilibili-api-python download (免登, B站) / yt-dlp (备用)
      → audio: faster-whisper int8 + VAD (hallucination reduction, 2-4x speedup)
      → frames: ffmpeg fps=0.5 extract → pHash dedup (≤8 Hamming distance) → RapidOCR
      → integration: ASR transcript + OCR text + 高赞评论(独立标注) → DeepSeek
  ```
  **VLM (Kimi/Claude vision) is NOT the right tool for investment/data videos.** See `references/vlm-vs-ocr-analysis.md` for the full analysis — VLM architecture ceiling: describes, never computes. OCR is more accurate AND 5-10x cheaper.
  
  **OCR engine decision (2026-06-15):** RapidOCR (primary — ONNX-based, Paddle accuracy without Paddle install hell, `pip install rapidocr-onnxruntime`). EasyOCR (fallback — already documented, torch-based). NOT PaddleOCR (Windows install fragility, inappropriate for this environment).
  
  **B站 subtitles are UNRELIABLE without login** — treat ASR as the primary path. Native subtitles are an opportunistic optimization; never block the pipeline on them.
  
  **B站 弹幕 are noise for investment content** — do NOT include in pipeline. 高赞评论 (top 10-15) are useful but MUST be in a separate provenance block marked as "观众补充（未经核实）".
  
  **小红书 is deferred** (2026-06-15): yt-dlp XiaohongShu extractor is currently broken due to site security changes. GitHub issue [#15572](https://github.com/yt-dlp/yt-dlp/issues/15572) tracks this. Build B站 skill first; revisit 小红书 when yt-dlp extractor is fixed or an alternative download method becomes available.
  
  **Frame deduplication is MANDATORY** — see pitfall #26. Without pHash dedup, OCR will scan duplicate frames, wasting time and producing noise.
  
  **Proxy unification is REQUIRED** — see pitfall #25. Three subsystems need proxy (HuggingFace model download, DeepSeek API, RapidOCR model download); B站 download needs DIRECT. Encapsulate in shared core module.
  
  Proven on Windows (bilibili-api-python), ¥0.01-0.02/video, no third-party bug dependencies.
  BiliSum was evaluated (★329) — abandoned due to unfixable ffmpeg subprocess bugs on Windows.
  Full Claude Opus 4.8 architecture review: `references/claude-architecture-review.md`.

**If the user wants targeted extraction (comments, danmaku, metadata, store names, prices):**
→ Continue with this skill's API-based workflow below. No full download/transcription needed.

## Trigger conditions

- User asks you to find information from B站 videos / UP主
- You need to extract店名, 地址, 菜名, 价格, 评价 from video content
- Any task involving Chinese video platform research where playback isn't feasible

## Core workflow

### Step 1: Find the UP主's UID

Use the search API to find the user first:

```
api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword=<URL-encoded name>
```

From the response, extract `data.result[0].mid` — this is the UID needed for space queries.

Known UIDs (save time):
- JASON刘雨鑫 (XFUN吃货俱乐部主持人): 403082144

### Step 2: Search for videos by topic

Two approaches — prefer the first:

**A) Search API (more reliable, less rate-limited):**
```
api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=<UP主名+地点>&page=1
```
Returns `data.result[]` with title, bvid, author, tag, play count, description.

**B) bilibili-api-python library (handles WBI signing automatically — PREFERRED for space queries AND video downloads):**
```python
from bilibili_api import user, video, sync
from bilibili_api.user import VideoOrder

u = user.User(uid)
videos = sync(u.get_videos(ps=30, pn=1, order=VideoOrder.PUBDATE))
# WARNING: order must be VideoOrder.PUBDATE enum, NOT raw string 'pubdate'
# WARNING: bilibili_api is async — use sync() or asyncio.run()

# For downloading video: get direct CDN stream URLs (bypasses yt-dlp 412)
v = video.Video(bvid="BV...")
info = await v.get_info()
cid = info['pages'][0]['cid']
url_data = await v.get_download_url(cid=cid)
dash = url_data['dash']  # Contains 'video' and 'audio' arrays with 'baseUrl' for each quality
# Download these URLs directly with requests.get() + proper headers
# CDN URLs expire in ~30 min — use immediately
```
The library bypasses WBI signature failures (-352) that plague raw API calls. `get_download_url()` is the cleanest way to get video stream URLs — no yt-dlp needed for direct downloads.

**C) Direct player API for subtitles:**
```
api.bilibili.com/x/player/v2?bvid=<BVID>&cid=<cid>
```
Returns `data.subtitle.subtitles[]` with `subtitle_url` for each language. Most short-form videos have no subtitles — expect empty results.

**D) Space API (often triggers 412/风控, use B above instead):**
```
api.bilibili.com/x/space/wbi/arc/search?mid=<UID>&keyword=<topic>&order=pubdate&ps=30&pn=1
```
This endpoint frequently returns "风控校验失败" — use approach B (`bilibili-api-python`) instead.

### Step 3: Get video details

```
api.bilibili.com/x/web-interface/view/detail?bvid=<BVID>
```
Returns `data.View` with full metadata including aid (needed for comments).

### Step 4: Extract content from comments (MOST IMPORTANT)

Video descriptions are almost always **empty** on B站 for short-form 探店 videos. The comment section is the richest data source:

```
api.bilibili.com/x/v2/reply/main?oid=<aid>&type=1&mode=3&ps=20
```

- `mode=3`: hot排序 (recommended)
- Filter replies with `like >= 20` or `rcount >= 3` for signal
- Strip HTML tags with `re.sub(r'<[^>]+>', '', msg)`
- Comments often contain: store names, prices, local opinions, corrections to the UP主's take

#### Sub-reply mining (楼中楼) — CRITICAL for addresses

When a top-level comment asks "在哪?" or "店名叫什么?", the answer is often in a **sub-reply**:

```
api.bilibili.com/x/v2/reply/reply?oid=<aid>&type=1&root=<rpid>&ps=10
```

- Target top-level comments with `rcount >= 5` (many replies = likely a Q&A thread)
- Filter sub-replies for location/address keywords: `店, 地址, 位置, 在哪, 路, 街, 号, 码头, 市场, 小区`
- A single sub-reply mentioning "照片顶上有个XX小区,结合店名搜一下吧" can unlock the entire location puzzle
- Sub-replies are also the best source for price confirmations and local perspective corrections

### Step 5: Danmaku (弹幕) analysis

Danmaku provides real-time viewer reactions pinned to video timestamps — useful for price/quality signals:

**Via bilibili_api (preferred):**
```python
from bilibili_api import video
v = video.Video(bvid="BV...")
dms = await v.get_danmakus(page_index=0)
for dm in dms:
    print(f"{dm.text}")  # dm.text is the danmaku content
```

**Via you-get (XML format):**
```bash
you-get --format=dash-flv360-AV1 -o /tmp "https://www.bilibili.com/video/BV..."
# This also downloads the .cmt.xml danmaku file
```
The XML has timestamps: `d p="SECONDS,1,25,..."` — the first number is the second in the video.

Keywords to filter danmaku for: `贵, 便宜, 钱, 元, 块, 坑, 良心, 好吃, 在哪, 码头, 地址`

### Step 6: Location geocoding via OSM Nominatim

For addresses extracted from comments, use OpenStreetMap Nominatim (free, no API key):

```
https://nominatim.openstreetmap.org/search?q=<URL-encoded Chinese query>&format=json&accept-language=zh
```

- **Must use proxy** (e.g., Clash Verge port 7897) — OSM times out on direct connections from China
- Chinese POI coverage is limited but landmarks work: 渔人码头, 马栏广场, 长山岛
- Combine with `urllib.request.ProxyHandler` in Python
- Fall back to constructing district-level addresses from confirmed neighborhood names

### Step 7: Validate location tags with related videos

B站 video tags can be misleading (e.g., a video tagged "大连" might actually be about 延吉). To verify:

1. Check `api.bilibili.com/x/web-interface/view/detail?bvid=<BVID>` → `data.Related[]`
2. If all related videos are about a different city, the tag is likely wrong
3. Cross-reference with comment content: if comments keep mentioning a different city, exclude the video

### Step 8: Video download + transcription (last resort)

When all proxy data sources are exhausted, download the video and transcribe. The full pipeline:

**8A. Tools required:**
```bash
pip install faster-whisper rapidocr-onnxruntime imageio-ffmpeg
# faster-whisper: 2-4x faster than openai-whisper, built-in VAD skips silence/BGM
# rapidocr-onnxruntime: ONNX-based, Paddle accuracy without Paddle install pain
# imageio-ffmpeg bundles ffmpeg binary — no separate ffmpeg install needed on Windows
```

**8B. Download audio-only (for transcription):**
```bash
yt-dlp --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  --add-header "Referer:https://www.bilibili.com/" \
  --add-header "Origin:https://www.bilibili.com" \
  -f "bestaudio[ext=m4a]/bestaudio" \
  --extract-audio --audio-format mp3 \
  -o "output.mp3" \
  "https://www.bilibili.com/video/BV..."
```
- `--add-header` with Referer+Origin is CRITICAL to bypass 412 on video format listing
- B站 is a domestic Chinese site — route `api.bilibili.com` through DIRECT connection (not proxy)
- Audio-only download is ~7MB for a 10-minute video — much faster than full video

**8C. Download full video (for visual frame extraction):**
```python
import asyncio
from bilibili_api import video
import requests

async def main():
    v = video.Video(bvid='BV...')
    info = await v.get_info()
    cid = info['pages'][0]['cid']
    url_data = await v.get_download_url(cid=cid)
    dash = url_data['dash']
    
    # Get DASH stream URLs (video + audio separate)
    video_url = dash['video'][0]['baseUrl']  # 480p usually the first
    audio_url = dash['audio'][0]['baseUrl']
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    }
    
    # Download segments
    r_v = requests.get(video_url, headers=headers, timeout=120)
    r_a = requests.get(audio_url, headers=headers, timeout=120)
    
    # Save and merge with ffmpeg
    ...
    
asyncio.run(main())
```
- `bilibili-api-python` handles WBI signing, returns direct CDN URLs — bypasses yt-dlp 412 issues
- DASH streams are separate video/audio `.m4s` segments — must merge with ffmpeg
- CDN URLs are short-lived (~30 min) — download immediately after fetching

**8D. ffmpeg on Windows without system install:**
```python
import imageio_ffmpeg
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
# Returns: C:\...\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
```
- The binary is named `ffmpeg-win-x86_64-v7.1.exe`, not `ffmpeg.exe` — whisper's subprocess call needs `ffmpeg` on PATH
- Workaround: copy to `ffmpeg.exe` in same dir and add to PATH, OR use the full path in subprocess calls
- `pip install imageio-ffmpeg` is all you need — no winget/choco/scoop required

**8E. Extract key frames from video (timestamp-guided, NOT blind extraction):**

CRITICAL: Do NOT use blind time-based extraction (`fps=1/20`). Charts and data tables often appear for only 3-8 seconds — blind extraction at 20s intervals will MISS them. Instead, use whisper timestamps to identify data-rich segments, then extract frames at those precise seconds.

**Phase 1 — Run whisper first and identify data-rich timestamps from the transcript:**
Whisper outputs like `[00:01:20.000 --> 00:01:25.000]`. Scan the transcript for segments where the speaker discusses data, charts, results, or numbers. Key cue phrases: "图表", "数据", "显示", "百分比", "胜率", "跑赢", "跑输", "样本", "结果", "表格", "看一下", "可以看"。

**Phase 2 — Extract frames at specific timestamps (NOT intervals):**
```bash
# For each data-rich timestamp, extract exactly ONE frame:
ffmpeg -ss 80 -i video.mp4 -frames:v 1 frame_080.jpg   # 1:20
ffmpeg -ss 160 -i video.mp4 -frames:v 1 frame_160.jpg  # 2:40
ffmpeg -ss 240 -i video.mp4 -frames:v 1 frame_240.jpg  # 4:00
```
- `-ss` is the second offset — compute from whisper timestamps (MM:SS → seconds)
- `-frames:v 1` extracts exactly one frame at that position
- This yields 5-10 targeted frames instead of 30+ blind frames — faster OCR, zero missed charts
- Larger JPG file size ≈ more visual information (charts, text overlays, UI screens). Prioritize frames >30KB for OCR.

**8F. Transcribe with faster-whisper (preferred over openai-whisper):**

faster-whisper is ~2-4x faster on CPU (int8 quantization) AND has built-in Silero VAD that skips silence/BGM — this reduces hallucination (openai-whisper tends to "invent" subtitles during silence/BGM segments).

```bash
pip install faster-whisper
```

```python
from faster_whisper import WhisperModel

# int8 quantization — 2-4x faster, near-zero accuracy loss for small model
model = WhisperModel("small", device="cpu", compute_type="int8")

# VAD filters silence/BGM → fewer hallucinations
segments, info = model.transcribe(
    "audio.wav",
    language="zh",
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)

for segment in segments:
    print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
```

- First run downloads model from HuggingFace — **must use proxy** (`HTTPS_PROXY=http://127.0.0.1:7897`). Do NOT use `hf-mirror.com` — tested 2026-06-15 and found unreliable (returns `FileMetadataError: Distant resource does not seem to be on huggingface.co`). Proxy direct to HuggingFace loads model in ~6s.
- `small` model + `int8` = sweet spot: fast enough for CPU, accurate for Chinese
- VAD reduces hallucination — critical for investment videos with background music
- Fallback: keep `openai-whisper` (`small` model) as documented; it's already installed and verified

**8G. Full pipeline order (MANDATORY dual-mode: audio + visual):**

CRITICAL: Audio transcription alone is INSUFFICIENT. You MUST capture visual content — charts, data tables, system UIs, price tickers, P&L screenshots are INVISIBLE to audio. The user explicitly expects you to understand BOTH what was said AND what was shown on screen.

1. Download audio (fast, 7MB) → start whisper transcription (slow, background)
2. Download video + extract frames (medium, done in parallel while whisper runs)
3. Read whisper transcript when ready
4. **OCR all frames** for on-screen text — this captures data that audio CANNOT: charts, tables, UI labels, numbers
5. Correlate transcript timestamps with key frames for full context
6. Present BOTH the transcribed narrative AND the OCR-extracted data/charts to the user

**8H. OCR on video frames (required, not optional):**

**Primary: RapidOCR** — ONNX-based, PaddleOCR accuracy, zero compilation, `pip install rapidocr-onnxruntime`.

```bash
pip install rapidocr-onnxruntime
```

```python
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()

for fname in sorted(os.listdir(frames_dir)):
    result, _ = engine(fpath, use_det=True, use_cls=True, use_rec=True)
    if result:
        for box, text, conf in result:
            if conf > 0.5 and len(text.strip()) > 1:
                print(f'[{conf:.2f}] {text}')
```

- `rapidocr-onnxruntime` — pure wheel install, no paddlepaddle, no C++ build
- Chinese accuracy ≈ PaddleOCR (shares same PP-OCR model)
- CPU speed: faster than EasyOCR (ONNX runtime optimization)
- **No temp.zip Defender lock** issue (unlike EasyOCR on Windows)
- First run downloads ONNX models — may need proxy

**Fallback: EasyOCR** — torch-based, already documented, good Chinese recognition. Use `['ch_sim', 'en']` to catch mixed Chinese/English/digit text:

```python
import easyocr
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
results = reader.readtext('frame.jpg', detail=0)
```

**CRITICAL: Frame deduplication before OCR** — ffmpeg extracts at fps=0.5 (2 frames/sec), then pHash (perceptual hash) removes frames with Hamming distance ≤8 from their predecessor. This prevents OCR'ing the same scene 60 times. See pitfall #26.

**Windows-specific EasyOCR setup (CRITICAL):**

EasyOCR downloads models to `~/.EasyOCR/model/` on first run. On Windows, antivirus/Defender locks the temp download file (`temp.zip`), causing `PermissionError` on cleanup. The download succeeds but the error crashes the script.

**Workaround — copy models to a fresh directory and use `model_storage_directory`:**
```bash
# After models are downloaded (even if the first run crashed), copy them:
mkdir -p /tmp/easyocr_models
cp ~/.EasyOCR/model/*.pth /tmp/easyocr_models/
```
```python
import easyocr
reader = easyocr.Reader(
    ['ch_sim', 'en'],
    gpu=False,
    model_storage_directory='/tmp/easyocr_models'  # bypass locked temp.zip
)
```

**Path mapping — MSYS `/tmp` ≠ Python `C:\tmp`:**

On Windows MSYS/bash, `/tmp` is mapped to `C:\Users\<user>\AppData\Local\Temp\`. But Python (running in the same venv) resolves `/tmp` literally as `C:\tmp\` — which doesn't exist. Always use **Windows absolute paths** for frame files passed to Python OCR:
```python
# WRONG — Python resolves this as C:\tmp\... (file not found)
frames_dir = '/tmp/bilibili_frames'

# RIGHT — use cygpath or hardcoded Windows path
# First: cygpath -w /tmp → C:\Users\ADMINI~1\AppData\Local\Temp
frames_dir = 'C:/Users/Administrator/AppData/Local/Temp/bilibili_frames'
```
Also use forward slashes: `C:/Users/...` — works in both Python and MSYS without escaping.

- `gpu=False` on CPU. OCR of 5-10 timestamp-guided frames takes ~30-60 seconds total
- First run downloads detection model (~100MB) + recognition model (~22MB) — allow 2-3 min
- `easyocr.Reader(['ch_sim', 'en'])` handles mixed Chinese/English text on charts
- Confidence threshold 0.2 is looser than 0.3 — catches more text fragments from UI/charts
- **File size heuristic**: larger JPG files at same resolution = more visual information (charts, dense text). Prioritize OCR on frames >30KB

Alternative: pytesseract is faster but requires separate tesseract binary install AND has poorer Chinese accuracy:
```bash
# Windows: winget install "Tesseract OCR" or choco install tesseract
# Linux: apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract
```
Prefer EasyOCR unless tesseract is already installed and configured for Chinese.

### Step 9: AI summaries and subtitles (low success rate, needs auth)
```
api.bilibili.com/x/web-interface/view/conclusion?bvid=<BVID>
api.bilibili.com/x/player/v2?bvid=<BVID>&cid=<cid>
```
These often return empty or require login. The `bilibili_api` methods `get_subtitle()` and `get_ai_conclusion()` also need credentials. Don't rely on them.

### Pitfalls

| Pitfall | Solution |
|---------|----------|
| **412 Precondition Failed** | B站 rate limits aggressively. Some endpoints (space/wbi) are stricter than others. Rotate between search/type and search/all/v2. Add 1-1.5s delays between requests. If you hit 412, wait 5s and retry with a different endpoint. |
| **yt-dlp 412 on video formats** | yt-dlp gets 412 when listing video formats even when audio downloads work. Fix: add `--add-header "Referer:https://www.bilibili.com/" --add-header "Origin:https://www.bilibili.com"`. Without these headers, format listing fails even with valid user-agent. |
| **CDN video URLs expire quickly** | DASH stream URLs from `get_download_url()` expire in ~30 minutes. Download immediately after fetching — don't store and reuse. If download times out, re-fetch fresh URLs. |
| **imageio-ffmpeg binary named differently** | The bundled ffmpeg binary is `ffmpeg-win-x86_64-v7.1.exe`, not `ffmpeg.exe`. Whisper's subprocess call requires `ffmpeg` on PATH. Workaround: `cp ffmpeg-win-x86_64-v7.1.exe ffmpeg.exe` in the same directory, then add to PATH. |
| **VideoOrder must be enum, not string** | `bilibili_api` `get_videos(order=VideoOrder.PUBDATE)` — passing raw string `'pubdate'` raises `AttributeError: 'str' object has no attribute 'value'`. Always use the enum. |
| **Whisper small model vs tiny** | `tiny` model (~72MB) is fast but poor for Chinese. `small` model (~461MB) is the sweet spot — 5-10min CPU transcription for a 10min video, much better accuracy. Use `--model small --language zh`. |
| **B站 needs DIRECT connection (no proxy)** | B站 is a Chinese domestic site. Routing through Clash/international proxy causes 412/blocked errors. Use direct connection for `api.bilibili.com` calls. This is the #1 cause of mysterious 412 failures. |
| **Search API returns irrelevant results** | The `keyword` parameter on search/type does a broad match. Always filter results by `author` field to ensure they're from the target UP主. |
| **Video descriptions are empty** | This is NORMAL on B站 — most UP主s don't write descriptions. Fall back to comments immediately; don't waste time retrying desc endpoints. |
| **B站/小红书官方AI总结需登录（已确认）** | B站 AI总结 API (`x/web-interface/view/conclusion/get`) 返回 `-403 访问权限不足`。小红书 "问一问" AI 重定向到登录页 (`error_code=300017`)。两者均需已登录 cookie，且即使登入后自动化调用仍有风控风险（-352）。**不建议依赖官方AI功能** — 走自建流水线更稳定。 |
| **Chinese search engines return SPA pages** | Baidu, Sogou, 360 all return JS-rendered SPAs that curl can't parse. Don't try to scrape them. Use B站's own APIs instead, or search via subagent with browser tools. |
| **Location tags can be misleading** | B站 video tags are user-added and sometimes wrong (e.g., a 延吉 video tagged 大连). Validate by checking `view/detail` → `Related[]` videos and comment content. |
| **whisper needs ffmpeg** | `openai-whisper` requires ffmpeg to extract audio. On Windows, use `imageio-ffmpeg` (pip install, no system tool needed). Without ffmpeg, whisper fails with `FileNotFoundError` on subprocess. |
| **OSM Nominatim times out without proxy** | OpenStreetMap's geocoding API is blocked from mainland China. Always route through proxy. |
| **B站合集 API triggers 风控** | The `space/wbi/season/list` endpoint is aggressively rate-limited. Use `view/detail` instead. |
| **Sub-replies hold the answers** | Top-level comments often ask "在哪?" but the answer is in sub-replies. Always fetch sub-replies for comments with `rcount >= 5`. |
| **Xiaohongshu notes require app cookies (for API/scraping)** | XHS web API returns 404/登录 redirect without valid X-S/X-T signatures. You CANNOT scrape XHS note pages or call their API directly. **However, yt-dlp natively supports XiaoHongShu** (`yt-dlp --list-extractors | grep XiaoHongShu`). Use yt-dlp for video download instead of trying to scrape the page. For note text/metadata beyond the video, ask user or find reposts on Bilibili. |
| **Transcription misses ALL visual data** | Charts, data tables, P&amp;L screens, system UI, price tickers, spreadsheet screenshots, and on-screen numbers are INVISIBLE to audio transcription. When a video discusses data/results/system output, OCR of frames is NOT optional — it's required to fully answer the user. The user explicitly expects multi-modal understanding: what was said AND what was shown. Skipping frame OCR when the video has visual data is a failure mode. |
| **EasyOCR error loop — temp.zip locked on Windows** (step 8H) | On Windows, EasyOCR's model download writes `temp.zip` to `~/.EasyOCR/model/` then tries to `os.remove()` it. Windows Defender/Antivirus locks the zip during scan, causing `PermissionError: [WinError 32]` EVERY run even after the `.pth` file was successfully extracted. This looks like a download failure loop — it's not; the model IS downloaded but the stale `temp.zip` blocks init. **Fix**: (a) Copy `.pth` files to a clean directory like `/tmp/easyocr_models/`, (b) delete the original `temp.zip` if possible, (c) pass `model_storage_directory='/tmp/easyocr_models'` to `easyocr.Reader()`. This avoids the locked file entirely. |
| **MSYS /tmp path invisible to Python OCR** (step 8H) | When running Python from MSYS bash on Windows, `/tmp/frames/file.jpg` resolves to `C:\tmp\...` inside Python — a path that doesn't exist. Always use Windows absolute paths for frame files when calling EasyOCR from Python scripts launched via terminal. Use `cygpath -w /tmp` to get `C:\Users\...\AppData\Local\Temp` and construct `C:/Users/Administrator/...` paths. |
| **MSYS /tmp path mismatch in Python** | On MSYS/bash, `/tmp` maps to `C:\Users\<user>\AppData\Local\Temp\`. But Python (same venv) resolves `/tmp` literally as `C:\tmp\` — file-not-found. Always use Windows absolute paths (`C:/Users/...`) or run `cygpath -w /tmp` first. |
| **Blind frame extraction misses key frames** | Using `fps=1/20` (1 frame every 20s) will miss charts/data shown for 3-8 seconds. Use whisper timestamps: identify data-rich segments first, then extract at those specific seconds (`ffmpeg -ss <seconds> -frames:v 1`). Cue words: "图表", "数据", "胜率". |
| **Transcription misses ALL visual data** | Charts, data tables, P&amp;L screens, system UI, price tickers, spreadsheet screenshots, and on-screen numbers are INVISIBLE to audio. When a video discusses data/results/system output, OCR of frames is NOT optional — it's required to fully answer the user. The user explicitly expects multi-modal understanding: what was said AND what was shown.
| **小红书 yt-dlp extractor currently broken (2026-06)** | yt-dlp的 `XiaoHongShu` extractor因小红书反爬安全升级失效，返回 `No video formats found`。即使带cookie也被DPAPI解密拦截。GitHub issue [#15572](https://github.com/yt-dlp/yt-dlp/issues/15572) 跟踪中。**小红书视频理解暂缓，优先做B站。** 当yt-dlp修复或找到替代下载方案后再回访小红书。
| **Proxy configuration scattered across subsystems** | 三处需要代理（HuggingFace模型下载、DeepSeek API、RapidOCR模型下载），一处需要直连（B站api.bilibili.com）。对非程序员用户是常见致败点。**必须**在共享内核中统一代理配置并做连通性自检，失败时给人话错误而非traceback。国内镜像优先（`HF_ENDPOINT=https://hf-mirror.com` 比走代理更稳）。
| **Frame deduplication missing → OCR waste** | ffmpeg按fps=0.5抽帧（2帧/秒）会产生大量重复帧。不做phash去重会导致同一个画面被OCR 60次——浪费时间且制造噪声。强制要求：抽帧后用phash（汉明距离≤8判定为相同）去重，只对画面变化点做OCR。保底最少10帧。
| **OCR digit misreading is a real risk for investment videos** | OCR 容易把 `8`/`B`、`0`/`O`、`%`/`。`、小数点丢失。投资视频的数字不可靠会导致错误结论。**必须**让DeepSeek把OCR数字标注为"低置信度，需与口播交叉验证"，不要让模型直接用OCR数字下结论。
| **ASR is the primary path; subtitles are opportunistic** | B站字幕列表走player API带wbi签名，免登不稳定。不要把流水线卡在字幕获取上。ASR当可靠主路径，原生字幕当"拿到就省一步"的优化，拿不到静默回退。
| **faster-whisper int8 hangs on some Windows CPUs** | 在这台机器上 `compute_type='int8'` 会导致 `transcribe()` 返回后迭代器永不产出——模型加载成功但转录卡死。**根因**：CT2 int8 与特定 CPU 的组合 bug。**修复**：改用 `compute_type='auto'`。已验证 `tiny`+`auto` 可正常工作（2分钟音频约45秒）。已从 pipeline.py 全局切换为 `tiny`+`auto`。
| **Chunked ASR for long audio (>3 min)** | 长音频 (>180s) 自动用 ffmpeg segment 切成 120s 块，逐块转录后合并时间戳。每块处理完后释放模型内存 (`del model`)，避免长音频 OOM。短音频 (<180s) 仍用直接转录。pipeline.py 中 `run_asr()` 自动判断。
| **taskkill /F /IM python.exe kills the agent** | 在 Windows 上 `taskkill /F /IM python.exe` 会杀死包括 Hermes Agent 自身在内的所有 Python 进程，导致断连。**永不用此命令。** 杀特定进程只能用 PID：`taskkill /PID <pid>`。

## Request headers template

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
}
```

## Verification

After collecting data, cross-reference:
1. Comments from multiple videos mentioning the same store/location
2. High-like comments (>100 likes) from self-identified locals — these carry more weight
3. Tag any claim that comes ONLY from comments (not video content) as "评论区来源, 待确认"

## Food Research Specialization (美食探店)

When the task is specifically food/travel review extraction (探店, 测评), adapt the output for consumer-facing use:

- **Output language**: Chinese, formatted for non-technical end users
- **Output structure**: 店名 → 具体位置/到达方式 → 特色菜/参考价格 → 博主评价 + 弹幕/评论共识 → 实用Tips → 附B站视频链接
- **Search completeness**: 一个地点博主可能拍了多个视频（不同角度/不同店）。标题里没写地名的视频可能在tag里有。多轮不同关键词搜索，不要漏。
- **Distinguish confidence levels**: ⭐ Confirmed (from comments/sub-replies, verifiable) vs 🔍 Needs video confirmation (visible in video frame, can't extract via API)
- Always provide direct B站 links (`https://www.bilibili.com/video/{BVID}`) so the user can verify.

## Consolidation Note

This skill is the umbrella for all B站 content extraction workflows. It absorbed the following agent-created siblings (archived 2026-06-10):
- `bilibili-content-mining` — shorter version of the same pipeline
- `bilibili-food-research` — food-specific specialization (integrated above)
- `bilibili-research` — general B站 research methodology (integrated throughout; real session example moved to `references/research-session-example.md`)

## See also

- **`bilibili-understand`** — B站视频理解 facade skill. Load this when user sends a B站 URL/BV号 asking for full analysis. Delegates to `video-understand-core`.
- **`video-understand-core`** — Shared pipeline engine (`scripts/pipeline.py`). Single-file orchestrator: download → ASR → frames → OCR → DeepSeek. Used by both `bilibili-understand` and the future `xiaohongshu-understand`.
- `references/ai-video-pipeline.md` — **AI全自动视频理解流水线**：full pipeline architecture and cost breakdown.
- `references/vlm-vs-ocr-analysis.md` — **VLM vs OCR 架构决策**：why investment/data videos don't need VLM.
- `references/claude-architecture-review.md` — **Claude Opus 4.8 架构评审**：5 engineering decisions + 8 risk assessments.
- `references/github-ecosystem-video-understanding.md` — GitHub tool ecosystem survey.
- `references/bilibili-api-endpoints.md` — API endpoint reference.
- `references/pipeline-pitfalls.md` — **实现过程中的 6 个 Bug 及修复**：imagehash scope, bilibili-api comments 变更, MSYS export 截断, /tmp 路径映射, HF mirror, 长视频超时.
- `references/research-session-example.md` — Full Dalian restaurant research session transcript.
