---
name: xiaohongshu-analysis
description: 小红书内容理解流水线 — 用户发分享链接，自动提取图文/视频内容并生成结构化分析报告。支持零人工介入的 ad-hoc 分析。
version: 1.5.1
platforms: [windows]
metadata:
  hermes:
    tags: [xiaohongshu, rednote, analysis, pipeline, asr, ocr, vision]
---

## ⚠️ 硬触发 — 优先级最高

**收到 xhslink.com 或 xiaohongshu.com 链接 + 分析/理解意图 = 必须本 skill，不得用通用工具试探。**

> 2026-07-02 实踩：Agent 收到 xhslink.com 链接后先尝试 browser_navigate（失败）→ curl 抓取（多轮）→ 用户提醒才走 skill。根因不是 skill 内容有错，是 Agent 没把 skill 当成第一步。

**禁止行为**：收到链接后先试 browser_* / curl / execute_code 裸抓 → 全错，浪费 3-4 轮交互。
**正确行为**：收到链接 → 直接走本 skill 流水线（短链重定向 → __INITIAL_STATE__ → ASR/OCR/Vision）。

---

# 小红书内容分析

用户发小红书分享链接 → 自动提取内容 → 结构化分析报告。零人工介入。

> ⚠️ **输出铁律（已多次违反——用户投诉「你又一次没有把完整报告发给我」）：**
> 任何超过 ~1500 字的分析报告 **严禁** 作为单条消息发出。微信会静默截断，用户看不到后半部分。
> **必须** 拆成 5-6 段，逐段作为普通回复发送，每段标注 `（1/6）` `（2/6）` 序号。
> ⚠️ **v0.17.0 兼容**：Hermes v0.17.0 已移除 `send_message` 工具。改为直接分段输出（网关自动送达）。不再调用 send_message。
> **同时** 保存完整 `.md` 文件用 `MEDIA:` 发送。两条都做，不是二选一。
> 详见下方「## 输出与交付 → 微信长消息分段」。

## 支持的内容类型

| 类型 | 处理方式 |
|:---|:---|
| 图文帖子 | 下载图片 → Vision 识图 → DeepSeek 总结 |
| 视频帖子 | 下载视频 → ASR（faster-whisper）+ OCR（RapidOCR）→ DeepSeek 总结 |

## 使用方式

```
用户发来小红书分享链接（含 xhslink.com 短链或完整 URL）
  → 自动解析 → 提取内容 → 输出分析报告
```

触发条件：用户消息中包含 `xhslink.com` 链接 或 `xiaohongshu.com` 链接，且表达了分析/理解的意图。

## 快速判定：先读 desc 再决定是否下载视频

视频帖的 `desc`（正文）质量差异很大，分两种情况处理：

| desc 质量 | 处理策略 | 示例 |
|:---|:---|:---|
| **信息密集**（列出关键信息） | 先基于 desc + 封面 Vision 做初步分析，判断是否需要视频细节再决定是否下载 | Hermes Studio 帖的 desc 列出了完整更新日志 |
| **信息稀疏**（只有话题标签） | 必须下载视频 → ASR + OCR | Scrapling 帖的 desc 只有 #Github #数据爬取 等标签 |

**判断标准**：desc 超过 100 字且包含具体工具名/产品名/步骤 → 先不下载视频，优先用 cover image 的 Vision + desc 文本分析。这可以在 2-3 个 turn 内完成，而非等待 2-5 分钟的 ASR。

## 外部资源追踪

当帖子引用外部项目（GitHub 仓库、网站、工具等）但未提供完整 URL 时，应主动发现并评估这些资源，纳入分析报告。

> 📎 详细发现流程和搜索策略见 [`references/github-repo-discovery.md`](references/github-repo-discovery.md)

关键原则：
- 帖子配图往往是关键信息载体 → Vision 优先识别
- GitHub API 对中文搜索支持极差 → 优先用 DuckDuckGo web 搜索
- 找到项目后批量拉取 stars/forks/README/文件树 → 纳入报告

## 架构

```
[xhslink.com 短链]
    ↓ HTTP GET + dump headers 获取 Location（⚠️ HEAD 返回 404！）
[xiaohongshu.com 真实笔记页]
    ↓ HTML 解析 __INITIAL_STATE__（修复 JS undefined→null）
[标题 / 正文 / 图片URL / 视频URL / 互动数据]
    ↓
    ├── 图文帖 → 下载图片 → Vision 识图 → DeepSeek 总结
    └── 视频帖 → 下载视频 → ffmpeg 抽音频+抽帧
                    ├── faster-whisper tiny (auto, chunked 120s)
                    ├── pHash 去重 + RapidOCR
                    └── DeepSeek 整合总结
```

## 关键实现细节

### xhslink.com 短链重定向（⚠️ HEAD 返回 404）

xhslink.com 的 **HEAD 请求返回 404**，不能用 `curl -sI`。必须用 GET + header dump：

```python
import re
# 错误做法：curl -sI → 404（HEAD 被拒绝）
# 正确做法：GET + -D 导出头信息
headers = terminal(f'curl -s -D - -o /dev/null "{link}"', timeout=15)['output']
loc = re.search(r'(?i)^location:\\s*(.+)$', headers, re.MULTILINE)
real_url = loc.group(1).strip().split('\\r')[0] if loc else None
```

拿到 `real_url` 后直接用 `curl -s -L` 请求 xiaohongshu.com 页面（不需要再跟一层重定向）。

### `__INITIAL_STATE__` JSON 提取（⚠️ 不要用 `.+?` 正则！）

小红书页面 `__INITIAL_STATE__` JSON 通常 800KB+。正则 `({.+?});` 的惰性匹配会在第一个空 `{}` 处停止。**必须用花括号计数器**：

```python
import re, json

with open('page.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

m = re.search(r'window\.__INITIAL_STATE__\s*=\s*', html)
if not m:
    raise Exception('__INITIAL_STATE__ not found')

start = m.end()
depth = 0
end = start
for i in range(start, min(len(html), start + 5000000)):
    if html[i] == '{': depth += 1
    elif html[i] == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break

json_str = html[start:end]

# JavaScript `undefined` → JSON `null`
json_str = re.sub(r':\s*undefined', ':null', json_str)

data = json.loads(json_str)
```

> **原因（2026.7.1 实踩）**：惰性正则 `({.+?});` 在 847KB 页面中遇到首个 `{}` 即停止，导致 `json.loads` 只拿到空对象。花括号计数器精确匹配完整的顶层 JSON。

### 视频下载
- 视频 URL 在 `note.video.media.stream.h264[0].masterUrl`
- 请求必须带 `Referer: https://www.xiaohongshu.com/`
- 住宅 IP 无需 cookie，数据中心 IP 可能触发验证码

### 音频分块
- faster-whisper 不支持 `start`/`duration` 参数
- 需用 ffmpeg `-f segment -segment_time 120` 物理切片，再逐段转录

### 批量处理多个帖子

当用户一次发来多个链接时：

1. **元数据提取**：在一个 `execute_code` 中串行提取所有帖子的元数据（每个 curl 2-3s，不耗时）
2. **图文帖**：图片下载和 Vision 调用可并行，不依赖视频处理
3. **视频帖**：**每个视频独立一个 `execute_code`**，不要在单次脚本中跑多个视频的 ASR+OCR — 300s 超时不够双视频
4. **并行策略**：元数据提取 + 图片 Vision + 单个视频 ASR 可同时进行；多个视频 ASR 必须串行分步
5. **外部搜索**：等元数据/ASR 完成后，用 `delegate_task` 对每个帖子独立搜索补充资料

## 缓存

`~/.hermes/cache/xhs-pipeline/<note_id>/`

步骤文件：
- `meta.json` — 解析后的帖子元数据
- `video.mp4` — 下载的视频（如有）
- `audio.wav` — 提取的音频
- `asr.json` — 语音转录结果
- `frames/` — 抽取的帧
- `ocr.json` — 画面 OCR 结果
- `images/` — 图文帖的图片
- `summary.json` — 最终分析报告

## 依赖

- Python 3.11+: faster-whisper, rapidocr-onnxruntime, imagehash, Pillow, openai
- ffmpeg: imageio-ffmpeg 自带（`imageio_ffmpeg.get_ffmpeg_exe()` 获取路径）
- DeepSeek API key: `C:\Users\Administrator\deepseek_key.txt`

## 代理

小红书国内 CDN 直连，不需要代理。DeepSeek API 也不需要代理。全程不走代理。

## 外部项目发现

当笔记引用了 GitHub 等外部项目但图片不含完整 URL 时，参考 [github-repo-discovery.md](references/github-repo-discovery.md) 的搜索策略（DuckDuckGo 是中文内容最可靠的后备方案）。

## 常见陷阱

### __INITIAL_STATE__ 数据路径：noteDetailMap 在 data['note'] 下，非顶层

首次解析 `__INITIAL_STATE__` 时，`noteDetailMap` 位于 `data['note']['noteDetailMap']`（嵌套在 `note` 键下），**不是** 顶层 `data['noteDetailMap']`。

```python
data = json.loads(json_str)

# ❌ 错误：直接取顶层
note_data = data.get('noteDetailMap', {})  # → 始终为空

# ✅ 正确：在 note 键下
note_data = data.get('note', {}).get('noteDetailMap', {})
for note_id, nd in note_data.items():
    note = nd.get('note', {})  # 实际的帖子数据
    desc = note.get('desc', '')
    # ...
```

**原因**：小红书页面版本不同，`__INITIAL_STATE__` 的结构会变。旧版可能 `noteDetailMap` 在顶层，新版在 `note` 下。**优先尝试 `data['note']['noteDetailMap']`**。

### OCR 依赖缺失时优雅降级

`rapidocr_onnxruntime` 可能未安装。ASR 提取帧后 OCR 调用应做存在性检查，而非直接 import 报错：

```python
try:
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    result, elapse = engine(frame_path)
    # ...处理OCR结果
except (ImportError, ModuleNotFoundError):
    print('rapidocr_onnxruntime not installed — skipping OCR')
    # 回退方案：用 Vision API（需联网）或跳过，不中断流程
```

从成功ASR中提取关键专有名词时（如MCP、Codex、Claude等），优先用 **cover image Vision** 或 **关键帧 Vision** 识别——比OCR更可靠，尤其当画面是UI截图而非纯文本时。

## 常见陷阱（旧条目保持）

### ASR 转录的项目名不可信：必须模糊搜索

视频 ASR（faster-whisper tiny）对英文专有名词转录误差大。例如 "Agent-Reach" 被转录为 "Agent reach"。用 ASR 原文直接搜 GitHub API 会找不到。

**模糊搜索策略**（按优先级）：
1. 尝试多种变体：加连字符（`agent-reach`）、去空格（`agentreach`）、拆分（`agent reach`）
2. 用功能描述搜：ASR 通常会正确转录功能描述（如"刷小红书逛B站"），用描述关键词 + `in:description` 过滤
3. 扩展时间窗口：项目可能创建于更早时间，`created:>2026-02-01` 比 `2026-06-01` 更安全
4. 遍历高星 agent 项目：`agent in:name stars:>7000` 然后逐个检查描述中是否有关键词

### ASR 乱码时用帧 Vision 识别项目名（比模糊搜索更可靠）

当 faster-whisper tiny 的中文转录严重失真（如本次 Scrapling 视频，大量片段不可读），**从视频中抽帧用 Vision 识图往往能直接看到 GitHub 页面截图上的项目名**：

1. 用 ffmpeg 抽帧（`fps=0.5` → 每2秒一帧）
2. Vision 分析前几帧——帖子通常在开头展示项目主页截图
3. 如果项目名显示在截图中（如 "D4Vinci / Scrapling"），直接用 GitHub API 拉取 → 跳过模糊搜索

这比用乱码 ASR 文本去模糊搜索 GitHub 快得多，且准确率更高。帧 Vision 和 ASR 可以并行进行，不必等 ASR 完成。

> 📎 详细外部项目发现策略见 [`references/github-repo-discovery.md`](references/github-repo-discovery.md)

### xhslink.com 重定向：HEAD 返回 404，必须用 GET

`curl -sI`（HEAD 请求）对 xhslink.com 返回 `HTTP/1.1 404 Not Found`，但 GET 请求正常返回 302。

**正确做法：**
```bash
# ❌ 错误：HEAD 请求
curl -sI "http://xhslink.com/o/xxxxx" | grep -i "^location:"

# ✅ 正确：GET + dump headers
curl -s -D - -o /dev/null "http://xhslink.com/o/xxxxx" | grep -i "^location:"
```

然后在 Python 中用 `re.search(r'(?i)^location:\\s*(.+)$', headers, re.MULTILINE)` 提取真实 URL。

### 页面重取必须用完整 URL（⚠️ 不带参数的 base URL 会失败）

首次页面抓取拿到 `__INITIAL_STATE__` 后，如果后续需要重新请求页面（如刷新过期的媒体 URL），**必须使用包含 `xsec_token` 等参数的完整重定向 URL**，不能只用 `https://www.xiaohongshu.com/discovery/item/{note_id}`。

```python
# ❌ 错误：不带参数重取，noteDetailMap 可能不包含目标 note_id
base_url = f"https://www.xiaohongshu.com/discovery/item/{note_id}"
curl -s -L "{base_url}"  # → 可能拿不到正确的 __INITIAL_STATE__

# ✅ 正确：用首次重定向得到的完整 URL（含 xsec_token/share_id/apptime 等）
curl -s -L "{full_redirect_url}"  # → 正确解析
```

**原因**：小红书的 xsec_token 是一次性访问令牌，不带它时页面可能返回不同结构或空数据。

### 媒体 CDN URL 过期 → 重取页面刷新

`__INITIAL_STATE__` 中提取的图片/视频 CDN URL 带有时效性 `sign` 参数。如果下载返回 0 字节或 403：

1. **不要反复重试同一 URL**——签名已过期
2. **用完整 URL 重新请求页面**（见上一条）→ 解析新的 `__INITIAL_STATE__` → 获取新签名的媒体 URL
3. 立即下载（新签名也有时效，尽快完成）

### ffmpeg 路径（Windows）

Windows 上 ffmpeg 通常不在 PATH。通过 imageio-ffmpeg 获取：

```bash
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
# 典型输出：C:\Users\...\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
```

在后续命令中使用完整路径：`"{ffmpeg_path}" -i "{video}" ...`

## 已知限制

| 限制 | 说明 |
|:---|:---|
| 登录墙 | 部分帖子需要登录才能看，需提供 cookie（未来版本） |
| 视频时效 | CDN URL 带 sign 参数有时效，下载需在获取后尽快完成 |
| 评论 | 网页版评论需登录，当前版本不抓评论 |
| ASR 精度 | faster-whisper tiny 模型中文识别有误差，关键内容 OCR 可校正 |
| **Hermes 0.17.0 send_message 移除** | v0.17.0 把 `send_message` 从 Agent 工具箱中移除（网关发送能力仍在）。报告通过 `send_message` 分段的逻辑会失效。修复方案：直接把报告作为普通回复输出，由网关自动送达，不再手动调用 send_message 分段。升级到 0.17.0 后需要更新 SKILL.md 中的发送逻辑。 |

## Windows 批处理脚本编码坑（跨任务通用）

在中文 Windows 上写 `.bat` 文件时，**UTF-8 编码的中文字符会被 cmd.exe 按 GBK 解析，产生乱码并被当成命令执行**（如 `echo` → `iiii`）。

修复方案（二选一）：
1. **全英文脚本 + `chcp 65001 >nul`**（推荐）：脚本内容全部用英文，第一行 `@echo off` 后加 `chcp 65001 >nul`
2. GBK 编码保存：用 `encoding='gbk'` 写入文件

> 此坑在 2026-06-21 Hermes 升级脚本编写时踩过，v4 (中文) → v5 (全英文) 才解决。以后写 Windows 批处理脚本默认用英文。

## ⚠️ v0.17.0 兼容性：send_message 工具已移除

**影响范围：** Hermes Agent v0.17.0 移除了 Agent 可调用的 `send_message` 工具。本 Skill 中「微信分段发送」步骤依赖 `send_message`，升级后将失效。

**症状：** 分析功能正常，但报告的微信发送步骤会报错（工具不存在）。

**临时方案：** 将报告作为普通回复输出（Markdown 格式），网关会自动送达。删掉显式 `send_message` 调用即可。

**修复命令（升级后）：** 告诉 Hermes「修复小红书分析的 send_message 问题」，Agent 会读取 SKILL.md 并替换发送步骤。

**本 Skill 的当前代码已包含 send_message 显式调用路径，待升级后修复。参见 [`references/send_message-migration.md`](references/send_message-migration.md)。

## GitHub README 拉取（⚠️ 两大坑）

### 坑①：API base64 响应含控制字符 → json.loads 崩溃

GitHub API `/repos/{owner}/{repo}/readme` 返回的 base64 编码内容在约 20,000 字符处含有控制字符（`\x00-\x1f`），导致 `json.loads()` 抛出 `Invalid control character`。`re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)` 清洗也无效——JSON 结构本身已被破坏。

**正确做法：** 用 `curl -o` 保存原始响应到文件，再用 `python -c` 在 **terminal** 中解码（不要用 `execute_code`，见下一条）：

```bash
# ✅ 正确：保存文件 → terminal 中 python -c 解码
curl -s --max-time 15 "https://api.github.com/repos/{owner}/{repo}/readme" -o ~/repo_readme.json
python -c "
import json, base64, re, os
path = os.path.expanduser('~/repo_readme.json')
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw)
data = json.loads(raw)
content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
print(content[:8000])
"
```

### 坑②：execute_code 看不到 terminal 保存的文件

Windows 上 `execute_code`（Python sandbox）和 `terminal`（MSYS bash）有**不同的文件系统视图**。`terminal` 保存到 `~/file.json` 或 `/tmp/file.json` 的文件，`execute_code` 中的 Python 无法访问。

**原则：** 需要跨工具共享文件时，用 `terminal` + `python -c` 一步完成（如上例），不要分两步（terminal 保存 → execute_code 读取）。

#### ⚠️ 坑②.5：terminal 内 `python -c` 也看不到 MSYS `/tmp/` 路径

即使都在 `terminal` 内部，`python`（Windows 原生程序）和 `ls`/`curl`（MSYS 程序）的路径系统不同。`curl -o /tmp/file.html` 正常保存（MSYS 将 `/tmp/` 映射到 `C:\...\Temp\`），但 `python -c "open('/tmp/file.html')"` 会报 `FileNotFoundError`——Python 不理解 MSYS 的路径映射。

**症状示例（2026.6.27 MoA 帖子分析实踩）：**
```bash
# ✅ MSYS 程序能看懂 /tmp
$ ls -la /tmp/xhs_moa_post.html
-rw-r--r-- 1 ... 873793 Jun 27 11:01 /tmp/xhs_moa_post.html

# ❌ Python 看不懂同一个 /tmp 路径
$ python -c "open('/tmp/xhs_moa_post.html')"
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/xhs_moa_post.html'

# ✅ 用 Windows 原生路径即可
$ python -c "open(r'C:\Users\Administrator\AppData\Local\Temp\xhs_moa_post.html')"
# 正常工作
```

**正确做法（二选一）：**
```bash
# 方案A：在 python -c 中使用 Windows 原生路径
python -c "open(r'C:\Users\Administrator\AppData\Local\Temp\file.html')"

# 方案B：用 os.path.expanduser 代替 /tmp
python -c "import os; open(os.path.expanduser('~/file.html'))"
```

**注意：** `~/` 在 terminal 的 `python -c` 中**通常**可用（MSYS 翻译 `$HOME` 到 Windows 路径），但 `/tmp/` 不可用。最稳妥的做法始终是用 Windows 绝对路径或 `os.path.expanduser('~/...')`。

### 坑③：raw.githubusercontent.com 对部分仓库返回空

对大仓库（如 `garrytan/gbrain`），`curl -sL https://raw.githubusercontent.com/{owner}/{repo}/master/README.md` 返回空。但 GitHub API contents 端点正常工作。

**正确做法：** 优先用 API `/repos/{owner}/{repo}/contents/README.md`，再用上述文件保存+解码方式处理。

## Windows Hermes 运维

> 📎 升级步骤、Python 切换、批处理脚本编写、gateway 操作铁律见 [`references/windows-hermes-operations.md`](references/windows-hermes-operations.md)

## 输出与交付

### 微信长消息分段（⚠️ 高频踩坑）
> 1. 这篇报告超过 1500 字吗？→ **必须分段**（微信会静默截断）
> 2. 用户上一次投诉过「没有收到完整报告」吗？→ 如果你已经踩过一次坑，**不要踩第二次**

### 微信长消息分段（⚠️ 高频踩坑 — 2026.6.21 再次被用户投诉）

微信对单条消息有长度限制。长分析报告（>2000 字）会**静默截断**——用户看不到后半部分，且不会收到任何提示。**不要在聊天区直接发长报告**（即使 markdown 渲染正常，送达也不完整）。

**真实翻车记录：** 2026.6.21「5大神器」分析报告作为一条消息发出→截断→用户说"你又一次没有把完整报告发给我"。补发MEDIA文件→用户再次说"我还是希望你通过微信消息的方式也给我发一份"——最终分段6条才满足。

**如果用户说"没收到完整报告"/"你又一次没有发完整"：** 说明消息被截断了。**立即分段重发**，不要只补发 MEDIA 文件。用户要的是微信内能直接读到的分段文本 + MEDIA 文件（**两条都做，立刻分段**）。

**交付策略（两条都做，不是二选一）：**

1. **主交付：分段发送**（用户明确偏好微信内阅读）
   - 将报告拆成 5-6 段，每段标注 `（1/6）` `（2/6）` 等序号
   - ⚠️ **v0.17.0：不再使用 `send_message` 工具**（已移除）。直接将分段内容作为普通回复逐条输出，网关会自动送达当前通道。
   - 段与段之间稍有间隔，最后一段附加行动号召
   - **不用等用户反馈——直接分段。不要先发一条完整的测试"能不能收到"**

2. **辅助交付：保存 `.md` 文件** → 用 `MEDIA:` 路径发送，供用户保存/转发/打印

**拆分原则：** 按逻辑段落切分（帖子信息/项目1/项目2/…/总结），每段控制在微信可完整显示的长度内。

**触发条件：** 任何输出报告超过约 1500 字时必须分段。宁可多拆一段，不要赌单条能过。**报告写完后，先数估算字数，再决定发送策略。**

### ⚠️ iLink 限流导致分段丢失（2026.6.21 实战：累计 429 次 rate limit）

即使分段发送，**iLink（微信）有严格限流**。本会话累计 429 次 rate limit 事件。多段消息在 1-2 秒内连续发出时，前 2-3 段可能到达，后几段被限流丢弃。

**缓解措施：**
- 段与段之间加 3-5 秒间隔（不要连续 `send_message`）
- 如果用户反馈「没收到完整报告」，检查是否是分段丢失而非单条截断
- 关键结论放在前 2 段（确保用户至少看到核心信息）
- 最后一段始终包含 `.md` 文件路径，确保用户有完整版可访问

### 🚨 send_message 工具在 v0.17.0 被移除

Hermes v0.17.0 中 `send_message` 不再作为 Agent 可调用工具。本 Skill 的输出交付章节依赖 `send_message` 做微信分段发送——**升级到 0.17.0 后该步骤会失效。**

**迁移方案：** 升级完成后，将 Skill 中的 `send_message` 调用改为「将分段内容作为普通文本回复，网关自动通过当前通道送达」。外部项目追踪、架构图中的 `send_message` 引用同理。

> 📎 Hermes 升级完整指南见 [`references/hermes-upgrade-0.14-to-0.17.md`](references/hermes-upgrade-0.14-to-0.17.md)
> 📎 升级脚本模板见 [`templates/upgrade_hermes_0170.bat`](templates/upgrade_hermes_0170.bat) 和 [`templates/switch_hermes_python312.bat`](templates/switch_hermes_python312.bat)

### 输出格式

```markdown
# 小红书内容分析报告

## 📋 帖子信息
（标题、作者、互动数据等）

## 一、内容概览
（一句话概括）

## 二、核心内容
（2-3 个要点）

## 三、详细分析
（视频：ASR+OCR 整合 / 图文：Vision 识图）

## 四、关键观点/结论
（提取的核心论点）

## 五、价值评估
（实操价值、可复刻性、适合人群）

## 🔧 技术复盘
（步骤耗时、成本）
```

## 验证测试

| 帖子 | 类型 | 时长 | ASR | OCR | 成本 |
|:---|:---|:---|---:|:---:|---:|
| 6a2f394e000000002102170b | 视频 | 364s | ✅ (87 seg) | ✅ (16帧) | ¥0.022 |

## 🧩 工作流配方

**任务**：小红书内容分析
**加载顺序**：
1. `xiaohongshu-analysis` — 本 skill：链接解析→下载→ASR/OCR/Vision→内容报告
2. **框架审视（条件触发）**：帖子涉及以下主题时，叠加 `deep-analysis-workflow`：
   - 金融/投资/黄金/产业链 → 加载已有框架（gold-macro-framework / investment-analysis）
   - AI/技术/新工具/商业 → **无现成框架时走 deep-analysis-workflow**（先向 Claude 借框架骨架，再填数据审视）
   - 判断标准：帖子 desc 中出现投资术语/公司名/产品名/技术概念 → 触发
3. 分析结论涉及操作建议时，触发 `decision-gate`
**交付**：微信分段（本 skill「输出与交付」章节是微信分段的标准参考，其他输出型 skill 引用此处）
**收尾**：任务完成后检查 `post-task-review` 触发条件，满足则生成复盘

## 🔗 横切约定

本 skill 的「输出与交付」章节是**所有输出型 skill 的微信分段标准参考**。其他 skill（serenity-tweet-analysis、gold-investment-analysis、bilibili-understand、supply-chain-ripple-analysis）的交付格式均引用此处，避免各自重复维护。
