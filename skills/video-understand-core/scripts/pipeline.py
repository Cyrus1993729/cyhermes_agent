#!/usr/bin/env python3
"""
Video Understanding Pipeline — shared core engine
Supports: bilibili (today), xiaohongshu (future)
Git-bash/MSYS on Windows, Clash proxy 7897
"""

import os, sys, json, hashlib, time, subprocess, asyncio, re, shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import traceback

# ── Config ──────────────────────────────────────────────
PROXY = "http://127.0.0.1:7897"
CACHE_ROOT = Path(os.environ.get("VIDEO_CACHE", 
    os.path.expanduser("~/.hermes/cache/video-pipeline")))
# Read DeepSeek key robustly - try env, then file, then hardcoded path
DEEPSEEK_KEY = (os.environ.get("DEEPSEEK_API_KEY", "") or "").strip()
if len(DEEPSEEK_KEY) < 10:  # too short = junk
    # Fallback: try reading from known key file locations
    for kf in [
        Path.home() / "deepseek_key.txt",
        Path("C:/Users/Administrator/deepseek_key.txt"),
        Path("C:/Users/Administrator/BiliSum/.env"),
    ]:
        if kf.exists():
            content = kf.read_text(encoding="utf-8").strip()
            if kf.suffix == ".env":
                # Parse .env file for key
                import re
                m = re.search(r'VIDEO_SUM_LLM_API_KEY=(.+)', content)
                if m:
                    DEEPSEEK_KEY = m.group(1).strip()
                    break
            else:
                DEEPSEEK_KEY = content
                break
HF_ENDPOINT = ""  # 走代理直连，hf-mirror.com 不稳定
OUTPUT_DIR = Path(os.environ.get("VIDEO_OUTPUT",
    os.path.expanduser("~/video-summaries")))

# ── Helpers ─────────────────────────────────────────────
def _proxy_env() -> dict:
    """Return environment dict with proxy set."""
    env = os.environ.copy()
    env["HTTP_PROXY"] = PROXY
    env["HTTPS_PROXY"] = PROXY
    if HF_ENDPOINT:
        env["HF_ENDPOINT"] = HF_ENDPOINT
    return env

def _run(cmd: List[str], timeout: int = 300, cwd: str = None) -> Tuple[int, str, str]:
    """Run a command and return (code, stdout, stderr)."""
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=timeout, cwd=cwd,
                       env=_proxy_env())
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def _cache_path(bvid: str, step: str) -> Path:
    """Get cache file path for a pipeline step."""
    d = CACHE_ROOT / bvid
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{step}.json"

def _cache_get(bvid: str, step: str) -> Optional[dict]:
    """Read cached step result, or None."""
    p = _cache_path(bvid, step)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None

def _cache_put(bvid: str, step: str, data: dict):
    """Write step result to cache."""
    _cache_path(bvid, step).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ── FFmpeg ──────────────────────────────────────────────
def _ffmpeg_bin() -> str:
    """Find ffmpeg binary (imageio-ffmpeg bundled)."""
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

# ── Step 1: Download ────────────────────────────────────
def bilibili_download(bvid: str, cache_dir: Path) -> Dict:
    """Download B站 video using bilibili-api-python. Returns {video_path, title, duration}."""
    cached = _cache_get(bvid, "download")
    if cached:
        print(f"[download] Using cached: {cached.get('video_path')}")
        return cached

    from bilibili_api import video, sync

    print(f"[download] Fetching video info for {bvid}...")
    v = video.Video(bvid=bvid)
    info = sync(v.get_info())
    title = info['title']
    cid = info['pages'][0]['cid']
    duration = info['duration']

    print(f"[download] Title: {title}")
    print(f"[download] Getting CDN URLs (cid={cid})...")
    url_data = sync(v.get_download_url(cid=cid))
    dash = url_data['dash']

    # Pick best quality (up to 720p to keep file reasonable)
    video_streams = sorted(dash.get('video', []), key=lambda x: x.get('bandwidth', 0))
    audio_streams = sorted(dash.get('audio', []), key=lambda x: x.get('bandwidth', 0))
    if not video_streams or not audio_streams:
        raise RuntimeError("No video/audio streams available")

    vid_url = video_streams[-1]['baseUrl']  # highest quality
    aud_url = audio_streams[-1]['baseUrl']

    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
    }

    video_file = cache_dir / "video.m4s"
    audio_file = cache_dir / "audio.m4s"
    merged_file = cache_dir / "video.mp4"

    if not merged_file.exists():
        print(f"[download] Downloading video segment...")
        r = requests.get(vid_url, headers=headers, timeout=120)
        video_file.write_bytes(r.content)

        print(f"[download] Downloading audio segment...")
        r = requests.get(aud_url, headers=headers, timeout=120)
        audio_file.write_bytes(r.content)

        print(f"[download] Merging with ffmpeg...")
        ffmpeg = _ffmpeg_bin()
        subprocess.run([ffmpeg, "-y", "-i", str(video_file), "-i", str(audio_file),
                        "-c", "copy", str(merged_file)], capture_output=True, timeout=60)
        video_file.unlink(missing_ok=True)
        audio_file.unlink(missing_ok=True)

    result = {
        "video_path": str(merged_file),
        "audio_path": str(merged_file),  # same file
        "title": title,
        "duration": duration,
        "bvid": bvid,
        "downloaded_at": datetime.now().isoformat()
    }
    _cache_put(bvid, "download", result)
    print(f"[download] Done: {merged_file}")
    return result

# ── Step 2: Audio extraction ────────────────────────────
def extract_audio(video_path: str, bvid: str, cache_dir: Path) -> str:
    """Extract 16kHz mono WAV for ASR."""
    wav_path = cache_dir / "audio.wav"
    if wav_path.exists():
        print(f"[audio] Using cached: {wav_path}")
        return str(wav_path)

    ffmpeg = _ffmpeg_bin()
    print(f"[audio] Extracting WAV for ASR...")
    subprocess.run([
        ffmpeg, "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(wav_path)
    ], capture_output=True, timeout=120)
    return str(wav_path)

# ── Step 3: ASR (faster-whisper, chunked for long audio) ──
def run_asr(audio_path: str, bvid: str) -> Dict:
    """Transcribe audio with faster-whisper, auto-chunking for long audio."""
    cached = _cache_get(bvid, "asr")
    if cached:
        print(f"[asr] Using cached transcript ({len(cached.get('segments',[]))} segments)")
        return cached

    # Check audio duration
    import wave
    with wave.open(audio_path, 'rb') as w:
        duration = w.getnframes() / w.getframerate()

    # For audio > 3 min, use chunked processing to avoid memory exhaustion
    if duration > 180:
        print(f"[asr] Audio {duration:.0f}s, using chunked mode (120s chunks)")
        return _run_asr_chunked(audio_path, bvid, duration)
    else:
        print(f"[asr] Audio {duration:.0f}s, direct transcription")
        return _run_asr_direct(audio_path, bvid)

def _run_asr_direct(audio_path: str, bvid: str) -> Dict:
    """Transcribe short audio directly."""
    from faster_whisper import WhisperModel

    print(f"[asr] Loading faster-whisper (tiny, auto)...")
    model = WhisperModel("tiny", device="cpu", compute_type="auto")

    print(f"[asr] Transcribing (VAD enabled)...")
    segments_out = []
    full_text = []
    segments, info = model.transcribe(
        audio_path,
        language="zh",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5)
    )

    for seg in segments:
        segments_out.append({
            "start": round(seg.start, 1),
            "end": round(seg.end, 1),
            "text": seg.text.strip()
        })
        full_text.append(f"[{seg.start:.1f}s-{seg.end:.1f}s] {seg.text.strip()}")

    # Free model memory
    del model

    result = {
        "full_text": "\n".join(full_text),
        "segments": segments_out,
        "duration": info.duration,
        "language": info.language,
    }
    _cache_put(bvid, "asr", result)
    print(f"[asr] Done: {len(segments_out)} segments, lang={info.language}")
    return result

def _run_asr_chunked(audio_path: str, bvid: str, total_duration: float) -> Dict:
    """Transcribe long audio by splitting into 120s chunks."""
    from faster_whisper import WhisperModel
    import tempfile

    chunk_sec = 120
    ffmpeg = _ffmpeg_bin()
    cache_dir = CACHE_ROOT / bvid
    chunks_dir = cache_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Split audio
    print(f"[asr] Splitting audio into {chunk_sec}s chunks...")
    subprocess.run([
        ffmpeg, "-y", "-i", audio_path,
        "-f", "segment", "-segment_time", str(chunk_sec),
        "-c", "copy", str(chunks_dir / "chunk_%03d.wav")
    ], capture_output=True, timeout=60)

    chunk_files = sorted(chunks_dir.glob("chunk_*.wav"))
    print(f"[asr] {len(chunk_files)} chunks")

    # Process each chunk
    print(f"[asr] Loading faster-whisper (tiny, auto)...")
    model = WhisperModel("tiny", device="cpu", compute_type="auto")

    all_segments = []
    all_text = []
    time_offset = 0.0

    for i, chunk_path in enumerate(chunk_files):
        print(f"[asr] Chunk {i+1}/{len(chunk_files)} (offset={time_offset:.0f}s)...", flush=True)
        segments, info = model.transcribe(
            str(chunk_path),
            language="zh",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5)
        )
        count = 0
        for seg in segments:
            all_segments.append({
                "start": round(time_offset + seg.start, 1),
                "end": round(time_offset + seg.end, 1),
                "text": seg.text.strip()
            })
            all_text.append(f"[{time_offset+seg.start:.1f}s-{time_offset+seg.end:.1f}s] {seg.text.strip()}")
            count += 1
        print(f"[asr]   {count} segments", flush=True)
        time_offset += chunk_sec

    del model

    result = {
        "full_text": "\n".join(all_text),
        "segments": all_segments,
        "duration": total_duration,
        "language": info.language if 'info' in dir() else "zh",
    }
    _cache_put(bvid, "asr", result)
    print(f"[asr] Done: {len(all_segments)} segments total")
    return result

# ── Step 4: Frame extraction + dedup ─────────────────────
def extract_keyframes(video_path: str, bvid: str, cache_dir: Path,
                      asr_data: Dict = None) -> List[Dict]:
    """Extract frames with ffmpeg, dedup with pHash, return unique frame paths."""
    frames_dir = cache_dir / "frames"
    cached = _cache_get(bvid, "frames")
    if cached:
        fr = cached.get("frame_files", [])
        if fr and Path(fr[0]).exists():
            print(f"[frames] Using cached: {len(fr)} frames")
            # return full paths
            return [{"path": f, "timestamp": t, "size_kb": s}
                    for f, t, s in zip(fr, cached.get("timestamps", []),
                                       cached.get("sizes", []))]

    frames_dir.mkdir(exist_ok=True)
    from PIL import Image
    import imagehash as ihash
    ffmpeg = _ffmpeg_bin()

    print(f"[frames] Extracting frames at 0.5 fps...")
    subprocess.run([
        ffmpeg, "-y", "-i", video_path,
        "-vf", "fps=0.5",
        "-q:v", "2",
        str(frames_dir / "frame_%04d.jpg")
    ], capture_output=True, timeout=120)

    # pHash dedup
    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"[frames] Extracted {len(frame_files)} frames, dedup with pHash...")

    unique = []
    last_hash = None
    for f in frame_files:
        try:
            img = Image.open(f)
            h = str(ihash.phash(img))
            if last_hash is None or _hamming_distance(h, last_hash) > 8:
                timestamp = _frame_number_to_timestamp(f.stem, fps=0.5)
                size_kb = round(f.stat().st_size / 1024, 1)
                unique.append({
                    "path": str(f),
                    "hash": h,
                    "timestamp": timestamp,
                    "size_kb": size_kb,
                })
                last_hash = h
            else:
                f.unlink()  # delete duplicate
        except Exception as e:
            print(f"[frames]  Skip {f.name}: {e}")

    # Keep at least 10 frames
    if len(unique) < 10:
        print(f"[frames] Only {len(unique)} unique frames, keeping all")

    print(f"[frames] Dedup: {len(frame_files)} → {len(unique)} unique frames")

    result = {
        "frame_files": [u["path"] for u in unique],
        "timestamps": [u["timestamp"] for u in unique],
        "sizes": [u["size_kb"] for u in unique],
        "hashes": [u["hash"] for u in unique],
    }
    _cache_put(bvid, "frames", result)
    return unique

def _hamming_distance(a: str, b: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")

def _frame_number_to_timestamp(stem: str, fps: float) -> float:
    """frame_0120 → seconds since start."""
    try:
        num = int(stem.split("_")[-1])
        return round(num / fps, 1)
    except:
        return 0.0

# ── Step 5: OCR ─────────────────────────────────────────
def run_ocr(frames: List[Dict], bvid: str) -> List[Dict]:
    """Run RapidOCR on deduplicated frames. Falls back to EasyOCR."""
    cached = _cache_get(bvid, "ocr")
    if cached:
        print(f"[ocr] Using cached: {len(cached.get('results',[]))} frames processed")
        return cached.get("results", [])

    # Try RapidOCR first
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        engine_name = "RapidOCR"
        print(f"[ocr] Using {engine_name}")
    except Exception as e:
        print(f"[ocr] RapidOCR failed ({e}), falling back to EasyOCR...")
        return _run_easyocr(frames, bvid)

    results = []
    for i, f in enumerate(frames):
        img_path = f["path"]
        if not Path(img_path).exists():
            continue
        try:
            ocr_result, _ = engine(img_path)
            texts = []
            if ocr_result:
                for box, text, conf in ocr_result:
                    if conf > 0.5 and len(text.strip()) > 1:
                        texts.append({"text": text.strip(), "confidence": round(conf, 2)})
            results.append({
                "timestamp": f["timestamp"],
                "path": img_path,
                "texts": texts,
                "engine": engine_name,
            })
            if (i+1) % 5 == 0:
                print(f"[ocr]  {i+1}/{len(frames)} frames done...")
        except Exception as e:
            print(f"[ocr]  Frame {i+1} error: {e}")

    print(f"[ocr] Done: {len(results)} frames processed")
    _cache_put(bvid, "ocr", {"results": results, "engine": engine_name})
    return results

def _run_easyocr(frames: List[Dict], bvid: str) -> List[Dict]:
    """Fallback OCR using EasyOCR."""
    import easyocr
    engine = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    engine_name = "EasyOCR"

    results = []
    for i, f in enumerate(frames):
        img_path = f["path"]
        if not Path(img_path).exists():
            continue
        try:
            ocr_result = engine.readtext(img_path, detail=1)
            texts = []
            for bbox, text, conf in ocr_result:
                if conf > 0.3 and len(text.strip()) > 1:
                    texts.append({"text": text.strip(), "confidence": round(conf, 2)})
            results.append({
                "timestamp": f["timestamp"],
                "path": img_path,
                "texts": texts,
                "engine": engine_name,
            })
            if (i+1) % 5 == 0:
                print(f"[ocr]  {i+1}/{len(frames)} frames done...")
        except Exception as e:
            print(f"[ocr]  Frame {i+1} error: {e}")

    print(f"[ocr] Done: {len(results)} frames processed")
    _cache_put(bvid, "ocr", {"results": results, "engine": engine_name})
    return results

# ── Step 6: Comments ─────────────────────────────────────
def fetch_bilibili_comments(bvid: str, limit: int = 15) -> List[Dict]:
    """Fetch top comments from B站 video."""
    cached = _cache_get(bvid, "comments")
    if cached:
        print(f"[comments] Using cached: {len(cached.get('comments',[]))} comments")
        return cached.get("comments", [])

    from bilibili_api import video, sync
    import requests

    print(f"[comments] Fetching video info for aid...")
    v = video.Video(bvid=bvid)
    info = sync(v.get_info())
    aid = info['aid']

    print(f"[comments] Fetching top comments (aid={aid})...")
    result = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://www.bilibili.com/video/{bvid}",
        }
        resp = requests.get(
            f"https://api.bilibili.com/x/v2/reply/main?oid={aid}&type=1&mode=3&ps={limit}",
            headers=headers, timeout=15
        )
        data = resp.json()
        replies = data.get('data', {}).get('replies', [])
        for r in replies[:limit]:
            result.append({
                "user": r['member']['uname'],
                "content": re.sub(r'<[^>]+>', '', r['content']['message']),
                "likes": r.get('like', 0),
                "replies_count": r.get('rcount', 0),
                "time": r.get('ctime', ''),
            })
        print(f"[comments] Done: {len(result)} comments")
    except Exception as e:
        print(f"[comments] Failed: {e}")

    _cache_put(bvid, "comments", {"comments": result})
    return result

# ── Step 7: DeepSeek Integration ─────────────────────────
def deepseek_summarize(asr_data: Dict, ocr_data: List[Dict],
                       comments: List[Dict], title: str, duration: int,
                       bvid: str) -> Dict:
    """Send ASR transcript + OCR text + comments to DeepSeek for structured summary."""
    cached = _cache_get(bvid, "summary")
    if cached:
        print(f"[summary] Using cached summary")
        return cached

    key = os.environ.get("DEEPSEEK_API_KEY", "") or DEEPSEEK_KEY
    if not key:
        print("[summary] No DEEPSEEK_API_KEY set, skipping summary")
        return {"error": "No API key", "summary_text": "", "structured": {}}

    # Build context
    transcript = asr_data.get("full_text", "")
    # Truncate if too long (DeepSeek context: 64K, leave room for prompt)
    if len(transcript) > 40000:
        transcript = transcript[:40000] + "\n[... 转录截断，视频过长 ...]"

    # Build OCR summary
    ocr_summary = []
    for f in ocr_data:
        texts = [t['text'] for t in f.get('texts', [])]
        if texts:
            ocr_summary.append(f"[{f['timestamp']}s] {' | '.join(texts)}")
    ocr_text = "\n".join(ocr_summary[:50])  # limit OCR lines

    # Comments summary
    comment_summary = []
    for c in comments[:10]:
        comment_summary.append(f"  [{c['likes']}👍] {c['user']}: {c['content']}")
    comment_text = "\n".join(comment_summary)

    prompt = f"""你是B站视频分析助手。请根据以下信息生成结构化总结（中文）。

【视频信息】
标题：{title}
时长：{duration}秒
BV号：{bvid}

【口播转录（ASR）】
{transcript}

【画面文字（OCR）】
{ocr_text if ocr_text else "（无画面文字）"}

【观众评论（高赞，仅供参考，非视频作者观点）】
{comment_text if comment_text else "（无评论）"}

请输出JSON格式：
{{
  "overview": "3-5句中文概述，总结视频核心内容和结论",
  "key_points": ["要点1", "要点2", ...], 5-8个
  "chapters": [
    {{"time": "mm:ss", "title": "章节标题", "summary": "内容概述"}}
  ],
  "data_mentions": ["视频中提到的数据/数字（来自OCR或口播）"],
  "viewer_consensus": "评论区的共识或分歧（如有）",
  "conclusion": "视频的最终结论或观点"
}}

注意：
- chapters的time必须精确到秒，基于ASR时间戳
- data_mentions中标注来源：[OCR]表示来自画面文字，[口播]表示来自语音，[评论]表示来自观众
- viewer_consensus若评论为噪声则写"无明显共识"
- 口播转录可能含同音错字，请根据上下文修正明显错误"""

    import requests
    try:
        print(f"[summary] Sending to DeepSeek ({len(transcript)} chars)...")
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
            proxies={"http": PROXY, "https": PROXY} if PROXY else None,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']
        summary = json.loads(content)

        usage = data.get("usage", {})
        result = {
            **summary,
            "_meta": {
                "tokens": usage.get("total_tokens", 0),
                "cost_estimate": f"¥{usage.get('total_tokens', 0) * 0.000002:.4f}",
                "model": "deepseek-chat",
                "transcript_chars": len(transcript),
                "ocr_lines": len(ocr_text.split("\n")) if ocr_text else 0,
                "comments_count": len(comments),
            }
        }
        _cache_put(bvid, "summary", result)
        print(f"[summary] Done: {usage.get('total_tokens', '?')} tokens")
        return result
    except Exception as e:
        print(f"[summary] Failed: {e}")
        return {"error": str(e), "summary_text": "", "structured": {}}

# ── Formatters ───────────────────────────────────────────
def format_markdown(summary: Dict, meta: Dict) -> str:
    """Format the pipeline output as a Markdown report."""
    lines = []
    lines.append(f"# 📺 {meta.get('title', '视频理解报告')}")
    lines.append("")
    lines.append(f"> BV号: `{meta.get('bvid', '?')}` | 时长: {meta.get('duration', '?')}s | 平台: B站")
    meta_info = summary.get("_meta", {})
    if meta_info:
        tokens = meta_info.get("tokens", 0)
        cost = meta_info.get("cost_estimate", "")
        lines.append(f"> Token: {tokens} | 成本: {cost}")
    lines.append("")

    if summary.get("overview"):
        lines.append("## 📝 概述")
        lines.append("")
        lines.append(summary["overview"])
        lines.append("")

    if summary.get("key_points"):
        lines.append("## 🔑 核心要点")
        lines.append("")
        for i, p in enumerate(summary["key_points"], 1):
            lines.append(f"{i}. {p}")
        lines.append("")

    if summary.get("chapters"):
        lines.append("## 📋 内容章节")
        lines.append("")
        for ch in summary["chapters"]:
            t = ch.get("time", "?")
            title = ch.get("title", "")
            s = ch.get("summary", "")
            lines.append(f"| `{t}` | **{title}** | {s} |")
        lines.append("")

    if summary.get("data_mentions"):
        lines.append("## 📊 数据提取")
        lines.append("")
        for d in summary["data_mentions"]:
            lines.append(f"- {d}")
        lines.append("")

    if summary.get("viewer_consensus"):
        lines.append("## 💬 观众共识")
        lines.append("")
        lines.append(f"> {summary['viewer_consensus']}")
        lines.append("")

    if summary.get("conclusion"):
        lines.append("## 🎯 结论")
        lines.append("")
        lines.append(summary["conclusion"])
        lines.append("")

    lines.append("---")
    lines.append(f"*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · video-understand-core*")

    return "\n".join(lines)

# ── Main Pipeline ────────────────────────────────────────
class VideoPipeline:
    """Orchestrate the full video understanding pipeline."""

    def __init__(self, bvid: str, platform: str = "bilibili"):
        self.bvid = bvid
        self.platform = platform
        self.cache_dir = CACHE_ROOT / bvid
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.meta: Dict = {}
        self.summary: Dict = {}

    def run(self) -> Path:
        """Run the full pipeline and return path to output markdown."""
        print(f"\n{'='*60}")
        print(f"Video Pipeline: {self.platform} / {self.bvid}")
        print(f"Cache: {self.cache_dir}")
        print(f"{'='*60}\n")

        # Step 1: Download
        if self.platform == "bilibili":
            dl = bilibili_download(self.bvid, self.cache_dir)
        else:
            raise NotImplementedError(f"Platform {self.platform} not yet supported")
        self.meta = dl

        # Step 2: Extract audio
        audio = extract_audio(dl["video_path"], self.bvid, self.cache_dir)

        # Step 3: ASR
        asr = run_asr(audio, self.bvid)

        # Step 4: Frames + dedup
        frames = extract_keyframes(dl["video_path"], self.bvid, self.cache_dir, asr)

        # Step 5: OCR
        ocr = run_ocr(frames, self.bvid)

        # Step 6: Comments
        comments = fetch_bilibili_comments(self.bvid)

        # Step 7: DeepSeek summary
        summary = deepseek_summarize(
            asr, ocr, comments,
            dl["title"], dl["duration"], self.bvid
        )
        self.summary = summary

        # Format and save
        md = format_markdown(summary, dl)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', dl["title"])[:50]
        out_path = OUTPUT_DIR / f"{self.bvid}_{safe_title}.md"
        out_path.write_text(md, encoding="utf-8")

        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete!")
        print(f"Output: {out_path}")
        print(f"{'='*60}\n")

        return out_path


# ── CLI entry ────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Video Understanding Pipeline")
    p.add_argument("bvid", help="B站 BV号")
    p.add_argument("--platform", default="bilibili", choices=["bilibili", "xiaohongshu"])
    p.add_argument("--output", help="Output directory")
    p.add_argument("--no-cache", action="store_true", help="Skip cache")
    args = p.parse_args()

    if args.output:
        OUTPUT_DIR = Path(args.output)
    if args.no_cache:
        # Clear cache for this video
        cache_d = CACHE_ROOT / args.bvid
        if cache_d.exists():
            shutil.rmtree(cache_d)
            print(f"Cleared cache: {cache_d}")

    pipeline = VideoPipeline(args.bvid, args.platform)
    out = pipeline.run()
    print(f"Report saved to: {out}")
