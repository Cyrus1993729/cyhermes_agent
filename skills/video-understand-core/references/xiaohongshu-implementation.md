# 小红书内容分析 — 实现细节与已验证模式

> 2026-06-16 实测验证。基于真实帖子 `6a2f394e000000002102170b` 的全链路测试。

## 已验证的链路

```
xhslink.com 短链 → 302重定向(带xsec_token) → 笔记页HTML
  → brace-counting 提取 __INITIAL_STATE__ JSON
  → replace('undefined', 'null') → json.loads()
  → 提取 title/desc/图片URL/视频URL
  → 视频下载(带Referer) → ffmpeg 物理切片 → faster-whisper ASR
  → ffmpeg 抽帧 → pHash 去重 → RapidOCR → DeepSeek 总结
```

**全部步骤通过，零人工介入。**

## JSON 解析：关键坑

### 坑1：正则非贪婪截断

```python
# ❌ 错误：{.*?} 遇到嵌套对象中的第一个 } 就停了
match = re.search(r'__INITIAL_STATE__\s*=\s*({.*?})', body, re.DOTALL)

# ✅ 正确：从 = 位置开始数括号匹配
match = re.search(r'window\.__INITIAL_STATE__\s*=\s*', body)
start = match.end()
depth = 0
for i in range(start, len(body)):
    c = body[i]
    # 处理转义和字符串（跳过字符串内容中的 { }）
    if c == '\\': escape_next = True; continue
    if c == '"' and not escape_next: in_string = not in_string; continue
    if in_string: continue
    if c == '{': depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0: end = i + 1; break
json_str = body[start:end]
```

### 坑2：JS `undefined` 不是合法 JSON

```python
# __INITIAL_STATE__ 是 JS 对象字面量，包含 undefined
# json.loads() 会报错：Expecting value at pos 3799

# ✅ 修复：替换 JS-isms
import re
fixed = re.sub(r':\s*undefined', ':null', json_str)
fixed = re.sub(r':\s*NaN', ':null', fixed)
state = json.loads(fixed)
```

### 提取内容的标准路径

```python
note_map = state.get("note", {}).get("noteDetailMap", {})
note_id = list(note_map.keys())[0]
note = note_map[note_id].get("note", {})

title = note.get("title")
desc = note.get("desc")
note_type = note.get("type")  # "normal" = 图文, "video" = 视频
user = note.get("user", {}).get("nickname")
tags = [t.get("name") for t in note.get("tagList", [])]
interact = note.get("interactInfo", {})  # likedCount, collectedCount, commentCount

# 图片
images = note.get("imageList", [])
for img in images:
    url = img.get("urlDefault") or img.get("url")

# 视频
video = note.get("video", {})
stream = video.get("media", {}).get("stream", {})
# 优选顺序：h264 > h265 > av1
for codec in ["h264", "h265", "av1"]:
    if codec in stream and stream[codec]:
        master_url = stream[codec][0].get("masterUrl")
        break
duration = video.get("videoDuration", 0)
cover = video.get("image", {}).get("urlList", [None])[0]
```

## 视频下载

```python
headers = {
    "User-Agent": "Mozilla/5.0 ... Chrome/131 ...",
    "Referer": "https://www.xiaohongshu.com/",  # 必须！否则 403
}
# CDN URL 从 __INITIAL_STATE__ 提取，有时效性，尽快下载
# 住宅 IP 下无验证码问题
```

## ASR：小红书视频与 B站的关键差异

### 坑3：faster-whisper 不支持 start/duration 参数

```python
# ❌ 错误（B站 pipeline 的写法在这里不适用）
segments, info = model.transcribe(audio_path, start=120, duration=120)

# ✅ 正确：用 ffmpeg 物理切片，然后逐段转写
# ffmpeg -i audio.wav -f segment -segment_time 120 -c copy chunk_%03d.wav

for i, chunk_file in enumerate(sorted(chunks)):
    model = WhisperModel("tiny", device="cpu", compute_type="auto")
    segments, info = model.transcribe(chunk_path, beam_size=5, vad_filter=True)
    for seg in segments:
        # 手动加时间偏移
        adjusted_start = chunk_offset + seg.start
        ...
    del model; gc.collect()  # 段间释放内存
```

### 切片时间偏移

```python
chunk_duration = 120  # 秒
time_offset = 0
for i, chunk_file in enumerate(chunks):
    # transcribe 返回的是相对于 chunk 文件开头的时间
    # 需要加上 chunk 的起始偏移
    adjusted_start = time_offset + seg.start
    time_offset += chunk_duration  # 下一段
```

## 抽帧与 OCR

小红书视频通常 3-10 分钟，教程类需要看屏幕内容（代码/框架/分析结论）。

```bash
# 每 20 秒抽一帧（6 分钟 ≈ 18 帧），pHash 去重后通常剩 12-16 帧
ffmpeg -i video.mp4 -vf "fps=1/20" -q:v 3 frames/frame_%03d.jpg
```

```python
# pHash 去重 (hamming distance < 8 视为重复)
import imagehash
h = imagehash.phash(Image.open(path))
if abs(h - existing_hash) < 8: skip  # duplicate

# RapidOCR
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
result, _ = ocr(image_path, text_score=0.5)
```

**注意**：教程类视频 OCR 量可能很大（帧帧都有文字）。实测 16 帧 OCR + ASR → 喂给 DeepSeek 总共约 10,000 input tokens。

## 成本

| 步骤 | 工具 | 成本 |
|:---|:---|:---|
| HTML 解析 | Python stdlib | 免费 |
| 视频下载 | urllib | 免费（带宽） |
| ASR | faster-whisper tiny (CPU) | 免费（本地） |
| OCR | RapidOCR | 免费（本地） |
| 总结 | DeepSeek chat | ~¥0.02/视频 |
| **合计** | | **~¥0.02/视频** |

## 已验证测试

| 帖子 | 类型 | 时长 | ASR | OCR | Tokens | 成本 | 备注 |
|:---|---:|---:|---|---:|---:|---:|
| `6a2f394e...` | 视频 | 6分4秒 | 87段, 2247字 (4 chunk) | 16帧去重后16帧 | 11,020 | ¥0.022 | 教程类, OCR+ASR 全量 |

## 与 B站 pipeline 的代码复用

小红书视频下载后，**ASR/OCR/总结三层可以完全复用 B站 pipeline 的代码**：

- ASR: 同 faster-whisper tiny + auto（仅切片方式不同，需 ffmpeg 物理切片）
- OCR: 同 RapidOCR + pHash 去重
- 总结: 同 DeepSeek prompt 模板（但需要传入帖子正文作为额外上下文）

**差异只在「获取内容」这一步**：B站用 API 下载，小红书用 HTML 解析。
