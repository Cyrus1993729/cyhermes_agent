---
name: video-understand-core
description: Shared video understanding pipeline engine — download, ASR, OCR, AI summary for B站/小红书/YouTube.
version: 1.4.1
platforms: [windows]
metadata:
  hermes:
    tags: [video, pipeline, bilibili, xiaohongshu, youtube, asr, ocr, multimodal]
---

# Video Understanding Core

Shared pipeline engine: download → ASR → frame extraction → OCR → AI summary.

Supports B站 (bilibili) — full pipeline with download/ASR/OCR. 小红书 uses a fundamentally different approach (HTML parsing + Vision/Playwright screenshot), see references.

## Architectures

### B站 (video-first)

```
bilibili-api-python → audio(WAV) → faster-whisper ASR (tiny+auto+VAD, ≥3min chunked)
                   → frames(JPG) → pHash dedup → RapidOCR
                   → comments(高赞) → DeepSeek integration
```

### 小红书 (image+text-first, ad-hoc)

```
用户分享链接(xsec_token已内置) → HTTP GET 笔记页
  ├─ L1 HTML解析: window.__INITIAL_STATE__ → title/desc/图片URL → Vision + DeepSeek
  └─ L2 兜底: Playwright截图 → Vision 读图 (对页面改版免疫)
```

See `references/xiaohongshu-architecture.md` for full technical design (Claude Code Opus review, 2026-06-16).
See `references/xiaohongshu-implementation.md` for concrete code patterns, verified test, and pitfalls discovered during implementation.

### YouTube (authentication-gated)

```
YouTube links → oembed API (metadata fallback, no auth needed)
             → yt-dlp --cookies (full access: download → ASR pipeline)
             → Otherwise: title-based analysis with DeepSeek
```

YouTube now requires authentication for ALL video data access (even public metadata beyond oembed). Without cookies/OAuth, only the oembed API works (title + author + thumbnail). For full pipeline (download → ASR → OCR → summary), user must provide cookies or manually download.

See `references/youtube-limitations.md` for the full breakdown of what works and what doesn't (verified 2026-07-09).

## Two paths

### Full pipeline (data/chart/code-heavy videos)

```bash
python scripts/pipeline.py BVxxxxx --platform bilibili
```

Runs all steps: download → audio → ASR → frames → OCR → comments → summary.

### Quick path (talking-head/conversation videos)

```bash
python scripts/quick_summary.py BVxxxxx
```

Skips OCR. Uses cached ASR + comments → DeepSeek summary. Downloads and ASR run if not cached.

### Decision rule

| Video type | Frame count | Action |
|:---|---:|:---|
| Talking-head / interview / dialogue | >50 | Use quick_summary.py |
| Screen recording / charts / data dense | any | Full pipeline (OCR worth it) |
| Short news clip (<2 min) | <30 | Either path fine |

## Usage

Do NOT load this skill directly. Load `bilibili-understand` (facade) instead.

```bash
python scripts/pipeline.py <BVID> --platform bilibili        # Full
python scripts/quick_summary.py <BVID>                        # Skip OCR
```

## ⚠️ Agent behavior: Progress monitoring (MANDATORY)

- **Do NOT** use `terminal(background=true)` for pipeline — Python stdout is fully buffered, zero output captured
- **DO** use `terminal(foreground, timeout=600)` with file redirect (`> file 2>&1`)
- **DO** poll cache files as progress indicator: `download.json` → `asr.json` → `frames.json` → `ocr.json` → `comments.json` → `summary.json`
- **DO** report actual progress with step names and numbers
- **Do NOT** say "running in background, will notify" and go silent
- If no cache file appears within 2 min, kill and diagnose

## Cache

`~/.hermes/cache/video-pipeline/<bvid>/`

Steps (write order): `download.json` → `asr.json` → `frames.json` → `ocr.json` → `comments.json` → `summary.json`

## Key Configuration

DeepSeek API key priority:
1. `DEEPSEEK_API_KEY` env (≥10 chars, reject junk)
2. `C:\Users\Administrator\deepseek_key.txt`
3. `C:\Users\Administrator\BiliSum\.env` → `VIDEO_SUM_LLM_API_KEY=` line

**Do NOT** use `export FOO=$(cmd)` in git-bash — it truncates. Read key in Python from file.
**Do NOT** use MSYS `/tmp/` paths in Python — resolves to `C:\tmp\`. Use `Path.home()` or Windows absolute paths.

## Requirements

- Python 3.11: faster-whisper, rapidocr-onnxruntime, imagehash, bilibili-api-python
- ffmpeg (imageio-ffmpeg bundled)
- Proxy: 127.0.0.1:7897 (Clash Verge)
- DeepSeek API key

## Model Configuration

- **ASR**: faster-whisper `tiny` + `compute_type='auto'` — ONLY working combination. `int8`/`int8_float16` deadlock.
- **OCR**: RapidOCR (≈8s/frame), EasyOCR fallback. Frame count >100 for talking-head = skip OCR.
- **Audio >3 min**: auto-split 120s chunks, `del model` after each chunk.
- **Never**: `taskkill /F /IM python.exe` — kills agent. Use `taskkill /PID <pid>`.

## Pitfalls

| Pitfall | Solution |
|:---|:---|
| **Background mode no stdout** | Python buffers fully. Use foreground + file redirect, or poll cache JSON files. |
| **RapidOCR ~8s/frame** | >100 frames ≈ 13+ min. Talking-head videos: use `quick_summary.py`. Screen-recording: accept the wait. |
| **`compute_type='int8'` deadlock** | `transcribe()` returns but generator never yields. Always `auto`. |
| **OCR skips useful data** | For chart/code videos, OCR extracts numbers from screen. Worth the wait (e.g. 96 frames → 12 min for quant trading demo). |
| **HF_ENDPOINT mirror unstable** | `hf-mirror.com` → `FileMetadataError`. Use proxy direct to HuggingFace, no `HF_ENDPOINT`. |
| **`DEEPSEEK_API_KEY` truncated** | git-bash `export` truncates to 3 chars. Pipeline rejects <10 chars, falls back to file. |
| **CDN URL expires** | `get_download_url()` URLs ~30min TTL. Pipeline downloads immediately; re-run if fails. |
| **Long video truncation** | Transcript >40K chars truncated. >1hr needs map-reduce (future). |
| **`bilibili_api` no `get_comments()`** | Use REST: `api.bilibili.com/x/v2/reply/main?oid={aid}&type=1&mode=3&ps=15`. |
| **`imagehash` import scope** | Need `import imagehash as ihash` inside `extract_keyframes` function. |
| **First run model download** | faster-whisper tiny (~500MB) + RapidOCR ONNX (~100MB). ~30-60s first time. |
| **`__INITIAL_STATE__` JSON parse fails** (小红书) | JSON contains JS `undefined` values. Replace `:undefined` → `:null` before `json.loads()`. Also use brace-counting (not regex) to extract the full nested JSON. |
| **faster-whisper `start` param fails** (小红书) | `transcribe()` doesn't support `start`/`duration`. Use ffmpeg physical split: `ffmpeg -f segment -segment_time 120`. Then transcribe each chunk with manual time offset. |
| **小红书视频 CDN 403** | Must include `Referer: https://www.xiaohongshu.com/` header when downloading. CDN URL has limited TTL — download immediately after extraction. |
| **YouTube LOGIN_REQUIRED** | All unauthenticated access blocked as of 2026-07. oembed API still works for metadata (title/author). Full access needs cookies/OAuth. See `references/youtube-limitations.md`. |

## Output

`~/video-summaries/<BVID>_<title>.md`:
- Overview / Key points / Timestamped chapters
- Data extraction (OCR + ASR, source-annotated)
- Viewer consensus (comments)
- Token usage and cost metadata

## Verified Tests

| Video | Duration | ASR | Frames | OCR | Tokens | Cost | Notes |
|:---|:---|---:|---:|:---:|---:|---:|:---|
| BV1YmJp6MEMC | 56s | ~3s | 25 | ✓ | 2432 | ¥0.0049 | Short, full pipeline |
| BV1GrJE6dE7r | 620s | ~5 min | 25 | ✓ | 12130 | ¥0.0243 | 6 chunks |
| BV1VtVr6GEJf | 788s | ~7 min | 218 | ⏭️ | 12503 | ¥0.0250 | Talking-head, quick_summary |
| BV1fUQZBxEZN | 569s | ~4 min | 96 | ✓ | 10305 | ¥0.0206 | Screen-recording, OCR worth it |
| XHS `6a2f394e...` | 364s | ~67s (4 chunk) | 18→16 | ✓ | 11020 | ¥0.0220 | 小红书教程, 完整链路(下载+ASR+OCR+总结) |

## Timing Estimates (tiny + auto + chunked)

| Video | Chunks | ASR | OCR (25f) | Total |
|:---|---:|---:|---:|---:|
| 1 min | 1 | ~3s | ~15s | ~30s |
| 6 min | 3 | ~2.5 min | ~30s | ~3.5 min |
| 10 min | 5 | ~4 min | ~45s | ~5.5 min |
| 20 min | 10 | ~8 min | ~1 min | ~10 min |

Timeout = video_minutes × 45 + 120s minimum.
OCR with large frame count (96+) adds ~8-12 min.
