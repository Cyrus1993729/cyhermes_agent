# Pipeline Implementation Pitfalls (2026-06-16)

## Bug 1: faster-whisper `int8` compute_type hangs

**Symptom**: `model.transcribe()` returns instantly, but the iterator produces zero segments — transcription never starts.

**Root cause**: CT2 (CTranslate2) `int8` quantization incompatible with this specific Windows CPU. Model loads fine (6s), but actual inference hangs silently.

**Fix**: Switch to `compute_type='auto'`. The `auto` setting picks the best available compute type for the hardware.

**Impact**: Required downgrading from `small` to `tiny` model on this machine (small+auto too slow for 2min chunks). Tiny+auto handles 2min audio in ~45s.

## Bug 2: bilibili-api `get_comments()` API changed

**Symptom**: `AttributeError: 'Video' object has no attribute 'get_comments'`

**Root cause**: The `bilibili-api-python` library removed/changed the method name.

**Fix**: Use direct REST API instead:
```python
resp = requests.get(
    f"https://api.bilibili.com/x/v2/reply/main?oid={aid}&type=1&mode=3&ps={limit}",
    headers={"User-Agent": "...", "Referer": f"https://www.bilibili.com/video/{bvid}"}
)
```

## Bug 3: `imagehash` module scope in `extract_keyframes()`

**Symptom**: `name 'imagehash' is not defined` despite top-level import.

**Root cause**: The module-level `import imagehash` was shadowed or not visible inside the function scope when `pipeline.py` is imported as a module from a different entry point.

**Fix**: Added `import imagehash as ihash` inside `extract_keyframes()` function body. Also moved `from PIL import Image` into function scope.

## Bug 4: `DEEPSEEK_API_KEY` truncated by bash export

**Symptom**: DeepSeek API returns 401 with message "api key: *** is invalid". Key reads as 3 characters.

**Root cause**: bash `export DEEPSEEK_API_KEY=...` with `$()` substitution failed silently, assigning literal `KEY` (3 chars) to env var.

**Fix**: Pipeline reads key from multiple fallback paths, in priority order:
1. `os.environ.get("DEEPSEEK_API_KEY")` — if ≥10 chars (filters junk)
2. `Path.home() / "deepseek_key.txt"` — plain text file
3. `Path("C:/Users/Administrator/deepseek_key.txt")` — Windows absolute path
4. `Path("C:/Users/Administrator/BiliSum/.env")` — parse `VIDEO_SUM_LLM_API_KEY=` from .env

## Bug 5: MSYS `/tmp` path invisible to Python

**Symptom**: `FileNotFoundError` when Python code references `/tmp/deepseek_key.txt` even though `cat /tmp/deepseek_key.txt` works in bash.

**Root cause**: On MSYS/git-bash, `/tmp` maps to `C:\Users\<user>\AppData\Local\Temp\`. But Python resolves `/tmp` literally as `C:\tmp\` — which doesn't exist.

**Fix**: Always use Windows absolute paths (`C:/Users/...`) in Python code, never MSYS-style Unix paths. Use `cygpath -w /tmp` to translate if needed.

## Bug 6: HF mirror unreliable — proxy direct is stable

**Symptom**: `huggingface_hub.errors.FileMetadataError: Distant resource does not seem to be on huggingface.co` when using `HF_ENDPOINT=https://hf-mirror.com`.

**Root cause**: The hf-mirror.com CDN returns inconsistent results from China.

**Fix**: Do NOT set `HF_ENDPOINT`. Rely on proxy (`HTTPS_PROXY=http://127.0.0.1:7897`) to reach HuggingFace directly. Model loads in ~6s via proxy.

## Bug 7: Long audio times out with `small` model

**Symptom**: 16-minute video (10min audio, 19MB WAV) times out at 600s — no segments produced.

**Root cause**: `small` model with `auto` compute_type is too slow on this machine (~1x real time for 10s test). For 600s audio, this means 600+ seconds of processing.

**Fix**: Two-part solution:
1. **Chunked ASR**: Audio >180s auto-splits into 120s chunks via ffmpeg segment mode (`-f segment -segment_time 120`). Each chunk processed sequentially, memory freed after each chunk (`del model`). Chunks combined with time offset.
2. **Downgrade to `tiny` model**: 2min chunk takes ~45s with `tiny`+`auto`. For 10min audio = 6 chunks × 45s = 270s (~4.5 min). Acceptable trade-off for this hardware.
