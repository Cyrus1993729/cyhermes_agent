---
name: bilibili-understand
description: "【全量 AI 视频理解】下载 B 站视频→转文字（ASR）→逐帧截图（OCR）→AI 摘要。适用于投资分析/教程/数据密集型视频。| 跟 bilibili-content-extraction 的区别：那个是轻量信息提取（搜索/评论/字幕），不走下载和 ASR，适合快速扫一眼；这个是全量深度理解管线，耗时长但覆盖全。"
version: 1.1.0
platforms: [windows]
metadata:
  hermes:
    tags: [bilibili, video, understanding, multimodal, asr, ocr, summary, investment]
    related_skills: [video-understand-core, bilibili-content-extraction]
    requires: [video-understand-core]
---

# B站视频理解 (Bilibili Video Understanding)

When the user wants to fully understand a B站 video — not just read comments, but process audio + visual content and generate a structured AI summary — use this skill.

## Trigger Conditions

- User sends a B站 video URL or BV号
- User asks to "分析这个B站视频", "总结这个视频", "理解这个视频内容"
- User wants data/charts extracted from a B站 video

## How It Works

This skill delegates to the shared `video-understand-core` pipeline engine:

```
1. Download (bilibili-api-python, 免登) → video.mp4
2. Extract audio → audio.wav (16000Hz mono)
3. ASR (faster-whisper tiny, auto + VAD; ≥3min → 120s chunked) → timestamped transcript
4. Extract frames (ffmpeg, 0.5fps) → pHash dedup → unique frames
5. OCR (RapidOCR, EasyOCR fallback) → on-screen text per frame
6. Comments (bilibili-api-python, 高赞top15) → viewer supplement
7. DeepSeek integration → structured JSON summary
8. Output markdown report → ~/video-summaries/
```

**Key features:**
- **No login required** — uses bilibili-api-python for CDN download
- **Visual content captured** — OCR reads on-screen text, data, and charts
- **Comments as supplement** — 高赞评论单独标注为"观众补充"
- **Caching** — each step cached, re-runs skip completed steps
- **Cost**: ~¥0.005 (short) to ~¥0.025 (10+ min) per video (DeepSeek API only)

## Verified Tests

| Video | Duration | Cost | Outcome |
|:---|:---|---:|:---|
| BV1YmJp6MEMC | 56s | ¥0.0049 | Full pipeline pass, 27 ASR segments, 25 frames |
| BV1GrJE6dE7r | 10.3 min | ¥0.0243 | 6 chunks, 312 segments, 12130 tokens ✅ |
| BV1VtVr6GEJf | 13.1 min | ¥0.0250 | 7 chunks, 588 segments, OCR skipped (talking-head → quick_summary.py) |
| BV1fUQZBxEZN | 9.5 min | ¥0.0206 | 5 chunks, 219 segments, 96 frames OCR (code/data video) → 10305 tokens |

## Usage

### Two paths: choose based on video type

**Data/code/chart videos** (投资分析、编码演示、图表密集) → full pipeline with OCR:
```bash
python C:\Users\Administrator\AppData\Local\hermes\skills\video-understand-core\scripts\pipeline.py BVxxxxx --platform bilibili
```

**Talking-head / interview / dialogue videos** (对话、访谈、播客 — 画面文字少) → skip OCR:
```bash
python C:\Users\Administrator\AppData\Local\hermes\skills\video-understand-core\scripts\quick_summary.py BVxxxxx
```
The quick_summary path reads cached download + ASR, fetches comments, and sends directly to DeepSeek. Saves 10-30 minutes on videos with 100+ unique frames but minimal on-screen text. Requires that download + ASR be cached first (run pipeline.py once, or the required steps will auto-execute).

### From a full URL

First extract the BV号 from the URL (e.g., `https://www.bilibili.com/video/BV1GrJE6dE7r` → `BV1GrJE6dE7r`), then run the command above.

### Force re-run (skip cache)

```bash
python .../pipeline.py BVxxxxx --platform bilibili --no-cache
```

## Prerequisites

The pipeline checks and auto-handles:
- **Proxy**: Clash at 127.0.0.1:7897 (set in pipeline.py)
- **API Key**: `DEEPSEEK_API_KEY` environment variable
- **Dependencies**: faster-whisper, rapidocr-onnxruntime, imagehash, bilibili-api-python (already installed)
- **ffmpeg**: Bundled via imageio-ffmpeg (auto-detected)
- **HuggingFace models**: Downloaded on first run via proxy (do NOT use hf-mirror.com)

## Output

A markdown report at `~/video-summaries/<BVID>_<title>.md` containing:

| Section | Content |
|:---|:---|
| 📝 概述 | 3-5 sentence overview |
| 🔑 核心要点 | 5-8 key points |
| 📋 内容章节 | Timestamped chapter breakdown |
| 📊 数据提取 | Numbers/data extracted from speech + screen |
| 💬 观众共识 | High-like comment consensus (if any) |
| 🎯 结论 | Final takeaway |

## Pitfalls

| Pitfall | Solution |
|:---|:---|
| **`compute_type='int8'` deadlocks on this CPU** | Always use `auto`. int8 causes silent hang — `transcribe()` returns but generator never yields. |
| **CDN URL过期** | Pipeline auto-downloads immediately; if fails, re-run (fresh URLs fetched) |
| **长视频(>1h)** | Transcript truncated to 40K chars for DeepSeek; later versions will do map-reduce |
| **OCR数字误读** | OCR data marked `[OCR]` in output, model instructed to cross-check with speech |
| **Whisper幻觉** | VAD filter removes silence/BGM segments, reducing hallucination |
| **首次运行慢** | First run downloads faster-whisper model (~500MB) and RapidOCR model (~100MB). **Use proxy (127.0.0.1:7897), do NOT use hf-mirror.com** — mirror returns `FileMetadataError`. Proxy direct loads in ~6s. |
| **200+帧OCR超时（~30分钟）** | 对话/访谈类视频OCR价值低，跳过即可。使用 `quick_summary.py`（见 video-understand-core skill）仅跑 ASR + 评论 → DeepSeek。录屏/代码类视频值得等 OCR（~12分钟/96帧）。 |
| **RapidOCR 帧数过多导致超时** | ~8s/帧。对话视频 pHash dedup 后仍可能 200+ 帧 → OCR 30 分钟。**判断方法**：帧数 >80 且为对话/访谈视频 → 用 `quick_summary.py` 跳过 OCR。帧数 <50 或图表/代码/数据密集视频 → 接受 OCR 耗时。 |
| **后台模式下 stdout 被缓冲** | `terminal(background=true)` 可能完全不显示 Python pipeline 输出。**进度监控改用缓存文件**：轮询 `download.json` → `asr.json` → `frames.json` → `ocr.json` → `comments.json` → `summary.json`。`process(action='wait', timeout=N)` + 检查文件存在性是最可靠方式。 |

## Agent Instructions

When the user triggers this skill:

### Phase 0: Triage (MANDATORY — do NOT skip to analysis)

User's priority for forwarded videos: **① 有没有投资/金融价值 → ② 能不能复刻（环境匹配）→ ③ 才展开细节**。

Before running the pipeline:
1. Use vision_analyze or search to get the video's topic, title, and creator
2. **Judge value first**: is this a financial/investment topic relevant to the user (gold ETF, 积存金, A-share, low-frequency investor)? If the video is about US stocks, high-frequency trading, or topics completely mismatched with the user's profile — say so immediately. Don't run the pipeline.
3. **Judge replicability**: if the user asks "can we build this", assess environment fit (Java? Docker? Python? data source?) before committing to analysis.
4. Only proceed to full pipeline analysis if both ① and ② are positive.

### Phase 1: Pipeline (only if Phase 0 clears)

1. Load `video-understand-core` first (shared pipeline engine)
2. Extract BV号 from the user's message (regex: `BV[0-9A-Za-z]{10}`)
3. **Assess video type**: if talking-head/interview/dialogue with likely minimal on-screen text → use `quick_summary.py`. If data/chart/code-heavy → use full `pipeline.py`.
4. Run the chosen command
5. **Monitor progress actively**: poll cache files every 30-60s, report step completions. Do NOT go silent.
6. Read the generated markdown report from `~/video-summaries/`
7. Present the report to the user in the chat

If the pipeline fails:
- Check proxy connectivity (ping DeepSeek API)
- Check `DEEPSEEK_API_KEY` is set
- On Windows, ensure git-bash paths work (use forward slashes or cygpath)
- If OCR times out, kill and re-run with `quick_summary.py`

**Never ask the user to watch the video themselves. The pipeline handles everything.**

## References

- `references/quant-trading-system-architecture.md` — 量化回测系统架构评审（小宇量化 BV1fUQZBxEZN，含 Opus 4.8 金融视角评分）
- See `video-understand-core` skill for shared pipeline engine details, pitfall table, and timing estimates.

## 🧩 工作流配方

**任务**：B站视频深度分析
**加载顺序**：
1. `video-understand-core` — 共享管线引擎（下载/ASR/OCR/摘要）
2. `bilibili-understand` — 本 skill：B站特定逻辑（API 限流/字幕/BV号解析）
3. 视频涉及金融/投资/产业链主题 → 叠加 `deep-analysis-workflow` 做框架审视
4. 视频涉及 AI/技术/新工具 → 无现成框架时触发 `deep-analysis-workflow`（先向 Claude 借框架再审视）
**交付**：平台分段 + MEDIA 文件（格式见 task-wrapup「分段交付」章节）
**收尾**：检查 `post-task-review`
