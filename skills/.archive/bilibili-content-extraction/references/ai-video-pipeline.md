# AI 视频全自动理解流水线

> **最后更新**: 2026-06-15 (Claude Opus 4.8 评审后修订)
> **验证状态**: B站已验证 ✅ | 小红书暂缓 ⏸️

## 概述

零人工干预的视频完整理解方案：语音转写 + OCR画面文字 + LLM 结构化整合。
已验证在 Windows 上成功运行，单次 10 分钟视频总成本约 ¥0.01-0.02。

**当前状态**: 
- B站：bilibili-api-python 免登下载可靠 → 可落地
- 小红书：yt-dlp extractor 因站点反爬升级失效 ([#15572](https://github.com/yt-dlp/yt-dlp/issues/15572)) → 暂缓

## 核心流水线

```
B站 BV号
  │
  ├─→ [1] bilibili-api-python 下载视频 (免登)
  ├─→ [2] ffmpeg 提取音频 + 关键帧 (fps=0.5 + pHash去重)
  │
  ├─→ [3] faster-whisper 本地转写 (int8 + VAD)
  ├─→ [4] RapidOCR 帧内文字抽取
  └─→ [5] DeepSeek 整合总结 (ASR + OCR + 高赞评论)
```

### 不再使用 VLM

2026-06-15 决策: 投资/数据型视频不使用 Kimi VLM 做画面理解。
详见 `references/vlm-vs-ocr-analysis.md` — VLM 本质是高级 OCR, 不会做量化图表分析。
OCR 更准确、更便宜。

## 依赖

```bash
pip install faster-whisper rapidocr-onnxruntime imageio-ffmpeg bilibili-api-python
```

## 详细步骤

### Step 1: 下载视频 (bilibili-api-python)

不需要登录、不需要 cookies、不触发 412 风控。

```python
from bilibili_api import video
import aiohttp, asyncio

async def download(bvid):
    v = video.Video(bvid=bvid)
    info = await v.get_info()
    cid = info['pages'][0]['cid']
    url_data = await v.get_download_url(cid=cid)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
        'Referer': 'https://www.bilibili.com/',
    }
    # Download DASH streams (video.m4s + audio.m4s)
    # Merge: ffmpeg -i video.m4s -i audio.m4s -c copy output.mp4
```

### Step 2: 提取音频 + 关键帧 + 去重

```bash
# 音频 (16kHz 单声道 WAV，喂 faster-whisper)
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# 关键帧 (fps=0.5 = 每2秒1帧)
ffmpeg -i video.mp4 -vf "fps=0.5" -q:v 2 frames/frame_%04d.jpg

# pHash 去重: 相邻帧汉明距离 ≤8 视为相同，丢弃
# 保底最少保留 10 帧
```

### Step 3: faster-whisper 转写

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    "audio.wav",
    language="zh",
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)

for segment in segments:
    print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
```

- `small` model + `int8` = CPU 上 2-4x 加速
- VAD (Voice Activity Detection) 跳过静音/BGM → 减少幻觉
- 首次运行需下载模型 → 走代理或 `HF_ENDPOINT=https://hf-mirror.com`

### Step 4: RapidOCR 帧文字抽取

```python
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()

for fname in sorted(os.listdir(frames_dir)):
    result, _ = engine(fpath)
    if result:
        for box, text, conf in result:
            if conf > 0.5 and len(text.strip()) > 1:
                print(f'[{conf:.2f}] {text}')
```

- 纯 wheel 安装，零编译
- 精度 ≈ PaddleOCR (PP-OCR 模型)
- OCR 数字标注为"低置信，需与口播交叉验证"

### Step 5: DeepSeek 整合总结

```python
# API: https://api.deepseek.com/v1/chat/completions
# Model: deepseek-chat
# 输入: ASR 转录 + OCR 文字 + 高赞评论(可选, 单独标注)
# 输出: 结构化总结 (时间轴 + 关键结论)
```

高赞评论 (top 10-15) 可选加入，但必须放在独立的 provenance block 中，标注为"观众补充（未经核实）"。

## B站 弹幕 + 评论

- 弹幕: **不入流水线** — 对投资内容基本是噪声
- 评论: 高赞前 10-15 条可加入，**必须**单独标注来源，不与口播混在一起
- 评论抓取: `api.bilibili.com/x/v2/reply/main?oid=<aid>&type=1&mode=3&ps=20`

## 长视频处理

超过 30 分钟的视频需分段处理 (map-reduce):
1. 按每 ~15 分钟分段
2. 每段独立生成摘要
3. 各段摘要合并后再做一次总摘要

短于 30 分钟的直接一次性处理。

## 代理配置

| 环节 | 代理策略 |
|:---|:---|
| B站 API (bilibili-api-python) | 直连 (DIRECT) |
| faster-whisper 模型下载 | `HF_ENDPOINT=https://hf-mirror.com` 或代理 |
| RapidOCR 模型下载 | 代理 |
| DeepSeek API | 代理 `HTTPS_PROXY=http://127.0.0.1:7897` |

在共享内核模块中统一封装代理配置，启动时做连通性自检。

## Windows 注意事项

### EasyOCR PermissionError (备选方案时)

Windows 上 EasyOCR 下载模型后清理 temp.zip 时会被 Defender 锁定。
**解决**: 复制 .pth 到干净目录，用 `model_storage_directory` 参数。

### ffmpeg 路径

`imageio-ffmpeg` 的二进制名为 `ffmpeg-win-x86_64-v7.1.exe`，不是 `ffmpeg.exe`。
复制并重命名为 `ffmpeg.exe` 放在同一目录。

## 成本对照

| 步骤 | 技术 | 成本 |
|:---|:---|:---|
| 转写 | faster-whisper local | ¥0 |
| OCR | RapidOCR local | ¥0 |
| 整合 | DeepSeek API | ~¥0.01 |
| **合计** | | **≈ ¥0.01** |

## 小红书状态

小红书视频理解关注但不阻塞。待 yt-dlp extractor 修复或其他免登下载方案出现后跟进。
当前可用替代方案:
- 用户手动粘贴小红书视频关键内容
- B站上有同内容转载的可通过 B站 skill 分析
