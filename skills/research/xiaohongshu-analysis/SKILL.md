---
name: xiaohongshu-analysis
description: 小红书内容理解流水线 — 用户发分享链接，自动提取图文/视频内容并生成结构化分析报告。支持零人工介入的 ad-hoc 分析。
version: 1.6.0
platforms: [windows]
metadata:
  hermes:
    tags: [xiaohongshu, rednote, analysis, pipeline, asr, ocr, vision]
---

## ⚠️ 硬触发 — 优先级最高

**收到 xhslink.com 或 xiaohongshu.com 链接 + 分析/理解意图 = 必须本 skill，不得用通用工具试探。**

> 2026-07-02 实踩：Agent 收到 xhslink.com 链接后先尝试 browser_navigate（失败）→ curl 抓取（多轮）→ 用户提醒才走 skill。根因不是 skill 内容有错，是 Agent 没把 skill 当成第一步。

**禁止行为**：收到链接后先试 browser_* / curl / execute_code 裸抓 → 全错，浪费 3-4 轮交互。
**正确行为**：收到链接 → 直接走本 skill 流水线（短链重定向 → __SETUP_SERVER_STATE__（优先）或 __INITIAL_STATE__（回退）→ ASR/OCR/Vision）。

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

## 视频下载决策流程（四步，不循环）

> 核心原则：**不问「视频里有没有我需要的东西」，而问「我的分析产物还缺什么」**。
> 不循环的关键——先无条件跑免费的（desc+封面），再用缺口触发下载。判断对象从「视频内容」换成「分析产物的槽位缺口」。

### 0. 先定 Schema（分析产物必填槽位）

一份工具类帖子的合格分析必须填满以下槽位：

| 槽位 | 必填 | 典型来源 |
|:---|:---|:---|
| 工具/产品名 | ✅ | desc / 封面 |
| 解决什么问题 | ✅ | desc |
| 关键操作步骤/核心机制 | ✅ | desc / 封面 / 视频 |
| 效果/数据/对比 | 选填 | 视频/封面 |
| 价格/获取方式/GitHub | 选填 | desc |
| 与其他工具的关系 | 选填 | desc / 视频 |

> 槽位可按帖子类型调整：教程类可能「关键步骤」权重更高，观点类可能「核心论点」代替「操作步骤」。

### 1. 第一步（定量）：desc 信息密度

| desc 质量 | 条件 | 策略 |
|:---|:---|:---|
| **信息稀疏** | ≤100 字 或 无具体名词（仅话题标签） | **直接下载视频** → ASR + OCR |
| **信息密集** | >100 字 + 含具体工具名/产品名/步骤 | 进第二步，不下载 |

### 2. 第二步（信号）：估「视频边际信息期望」

用以下信号判断视频里出现「desc+封面没有的必填信息」的概率。**注意：这不是在猜视频内容，而是在估 desc+封面 的自足程度。**

| 信号 | 边际低 → 可跳过视频 | 边际高 → 视频可能补缺口 |
|:---|:---|:---|
| **封面类型** | 架构图/流程图/步骤九宫格/满屏文字截图 | 人物出镜/氛围图/悬念标题党封面 |
| **desc 结论完整度** | 有因果闭环（"用X做了Y，结果Z"） | 只有钩子（"这个方法太绝了"）/ 明示「详见视频」 |
| **帖子类型** | 工具介绍/新品速览/观点输出 | 分步教程/操作演示/Vlog |
| **结构线索** | 编号步骤 + 参数/链接 + 完整流程 | 大量话题标签但无实质句子 |
| **作者风格** | 已知「长图文+视频补充」型作者 | 已知「干货全在视频」型作者（先验可缓存） |

**输出**：综合信号给出边际期望判断——低/中/高。

### 3. 第三步（执行）：无条件跑首遍

不管边际期望高低，先基于 **desc + 封面 Vision** 填槽。按 Schema 逐槽评估：
- 已填满 + 置信度高 → ✅
- 有内容但置信度低 → ⚠️
- 空 → ❌

### 4. 第四步（缺口触发）：用缺口拉视频

```
必填槽位全部填满且置信度 ≥ 高
  → 🟢 不下载，直接出分析报告

必填槽位有空缺或低置信
  → 结合第二步的边际期望：
      边际期望 中/高 → 🔴 下载视频（视频很可能补上缺口）
      边际期望 低     → 🟡 不下载，但标注「该信息帖子未提供」
                        （缺口存在但视频大概率也没有 → 避免白下）
```

> ⚠️ **关键**：下载的触发器是「首遍槽位缺口」这个可度量事实，不是「我猜视频里有没有料」这个事前臆测。信号只用来在有缺口时判断下载性价比。

### 判断示例

| 帖子 | desc | 封面 | 首遍缺口 | 边际 | 决策 |
|:---|:---|:---|:---|:---|:---|
| PlanWeave（本次） | 484字+循环步骤+GitHub | 界面截图+流程图 | 无 | 低 | 🟢 跳过 |
| Hermes Studio | 完整更新日志 | 标题 | 无 | 低 | 🟢 跳过 |
| Scrapling | #Github #数据爬取 | — | — | — | 🔴 直接下（第一步已判稀疏） |
| 某教程帖 | "3步搞定，看视频" + 钩子 | 人物出镜 | 缺步骤 | 高 | 🔴 下载 |

无法预知视频内容，但可以通过三个间接信号做概率估计：

1. **封面图**：Vision 看到的是完整信息图/架构图？→ 视频大概率是逐条讲解，增量低
2. **desc 完整度**：核心结论、步骤、链接都写进正文了？→ 视频大概率是演示，增量低
3. **帖子类型**：工具介绍类帖子，作者通常正文写概念、视频放操作演示 → 增量低

**判定规则**：三个信号都指向增量低 → 跳过视频。任一信号不确定 → 下载。

### ⚠️ 必须显式输出判断结论

不管最终是否下载视频，**必须在分析过程中显式输出判断结论**，让用户看到你做了这个判断。格式：

> 「desc 判断：[密集/稀疏]（XXX字，[含/不含]具体工具名）。封面：XXX。增量估计：[低/不确定/高] → [不下载/下载]视频」

这一步不可跳过。即使判断结论是「不下载」，也必须输出。

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
    ↓ HTML 解析：
      ├── 优先：__SETUP_SERVER_STATE__ → LAUNCHER_SSR_STORE_PAGE_DATA.noteData（新版 SPA 页面）
      └── 回退：__INITIAL_STATE__ → note.noteDetailMap（旧版 / SSR 页面）
      均需修复 JS undefined→null
[标题 / 正文 / 图片URL / 视频URL / 互动数据]
    ↓
    ├── 图文帖 → 下载图片 → Vision 识图 → DeepSeek 总结
    └── 视频帖 → desc密度判定
                    ├── 稀疏 → 直接下载视频 → ASR+OCR → DeepSeek 总结
                    └── 密集 → 信号评估(边际期望) + 封面Vision → 按Schema填槽
                                ├── 槽位全满 → 不下载，直接出报告
                                └── 槽位有缺口 → 边际高则下载(ASR+OCR)，边际低则标注缺失
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

### 音频提取：必须用 `-map 0:a`，不能用 `-vn` 代替

`-vn` 只剥离视频轨，不保证选中音频轨——对某些编码（如 HE-AAC）可能产生静默输出（几 KB 的 WAV，实际音频数据丢失）。

```bash
# ❌ 错误：-vn 不保证音频轨选中
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
# → 可能产生 ~1KB 的无效 WAV

# ✅ 正确：显式映射音频流
ffmpeg -i video.mp4 -map 0:a -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
# → 正常大小 ≈ duration × 16000 × 2 bytes
```

> **验证**：正常 WAV 大小 = 时长(秒) × 16000 × 2（16kHz 16-bit mono）。27 秒约 860KB。若输出远小于此，说明音频轨未被正确选中。

### 音频分块
- faster-whisper 不支持 `start`/`duration` 参数
- 需用 ffmpeg `-f segment -segment_time 120` 物理切片，再逐段转录
- 转录脚本：`scripts/whisper_chunk.py <chunk.wav>`（本 skill 自带）

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

### ⚠️ `__INITIAL_STATE__` 的 noteDetailMap 包含多个帖子——必须按 noteId 精确匹配（2026.7.12 Harness综述实踩）

**小红书页面 `noteDetailMap` 可能包含多个帖子**（目标帖 + 推荐/关联帖），**不能取第一个条目**。必须先从页面 URL 中提取目标 `noteId`，再精确匹配：

```python
# ❌ 错误：取第一个条目 → 拿到的是随机推荐帖，不是用户分享的帖子
for nid, nd in note_map.items():
    note_data = nd.get('note', {})
    if note_data:
        break  # ← 可能是其他帖子！

# ✅ 正确：从URL提取noteId，精确匹配
note_id = re.search(r'/item/([a-f0-9]+)', url).group(1)
note_data = note_map.get(note_id, {}).get('note', {})
if not note_data:
    # fallback: 遍历搜索
    for nid, nd in note_map.items():
        if nd.get('note', {}).get('noteId') == note_id:
            note_data = nd.get('note', {})
            break
```

**症状**：第一次解析拿到 PlanWeave 帖子（noteId=6a460a47...），而用户分享的是 Harness 综述帖子（noteId=6a50bbbf...）。两者完全不同。第二次用精确匹配才正确获取。

### __SETUP_SERVER_STATE__ 新页面结构（2026.7.8 hermes-journey 帖子实踩）

**新版小红书 SPA 页面（~120KB HTML）将帖子数据放在 `__SETUP_SERVER_STATE__` 而非 `__INITIAL_STATE__`**。`__INITIAL_STATE__` 中 `noteDetailMap` 为空，但 `__SETUP_SERVER_STATE__` 的 `LAUNCHER_SSR_STORE_PAGE_DATA.noteData` 直接包含帖子对象（非 `noteDetailMap` 嵌套）。

**症状**：按原有流程解析 `__INITIAL_STATE__` → `noteDetailMap` 为空 → 误判为登录墙/数据缺失。实际数据在另一个 state 变量中。

**正确做法：两级回退**
```python
import re, json

# Level 1: 优先尝试 __SETUP_SERVER_STATE__（新版 SPA）
m = re.search(r'window\.__SETUP_SERVER_STATE__\s*=\s*', html)
if m:
    start = m.end()
    # ...花括号计数器提取 JSON...
    data = json.loads(json_str)
    page = data.get('LAUNCHER_SSR_STORE_PAGE_DATA', {})
    nd = page.get('noteData', {})  # 直接是帖子对象，含 title/desc/video/imageList 等
    if nd.get('noteId'):
        return nd  # ✅ 拿到数据，跳过 __INITIAL_STATE__

# Level 2: 回退 __INITIAL_STATE__ → noteDetailMap（旧版/SSR）
m = re.search(r'window\.__INITIAL_STATE__\s*=\s*', html)
# ...原有流程...
```

**关键差异**：
| | `__INITIAL_STATE__`（旧） | `__SETUP_SERVER_STATE__`（新） |
|:---|:---|:---|
| 帖子数据路径 | `data.note.noteDetailMap[note_id].note` | `data.LAUNCHER_SSR_STORE_PAGE_DATA.noteData` |
| 结构 | 嵌套 wrapper (`{note: {...}}`) | 直接帖子对象（`title`, `desc`, `video` 等顶级字段） |
| 典型 HTML 大小 | 800KB+ | ~120KB |
| 图片 URL 字段 | `infoList[].imageScene=WB_DFT` | 同，但 `infoList[].imageScene=H5_DTL/H5_PRV` |

> **注意**：`__SETUP_SERVER_STATE__` 中的图片 CDN URL 字段可能用 `H5_DTL`/`H5_PRV` 而非 `WB_DFT`/`WB_PRV`，提取时需同时尝试两种 scene 值。

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

### imageList 的 url 字段可能为空，真实 URL 在 urlPre/urlDefault/infoList（2026.7.3 PlanWeave 实踩）

某些帖子（如本次 PlanWeave 帖子 6a460a47...）的 `imageList[0].url` 为空字符串，但 `urlPre`、`urlDefault` 和 `infoList` 中有有效的图片 URL：

```python
img = image_list[0]
# url 字段 → 空字符串 ""  ← 不要用！
# urlPre    → "http://sns-webpic-qc.xhscdn.com/...!nd_prv_wgth_jpg_3"  ← 预览图
# urlDefault → "http://sns-webpic-qc.xhscdn.com/...!nd_dft_wgth_jpg_3" ← 默认图
# infoList  → [{"imageScene": "WB_PRV", "url": "..."}, {"imageScene": "WB_DFT", "url": "..."}]
```

**提取策略**：优先用 `infoList` 中 `imageScene="WB_DFT"` 的 URL，fallback 到 `urlDefault`，最后才试 `urlPre`。**不要直接用 `img['url']`**——它可能为空。

### 媒体 CDN URL 过期 → 重取页面刷新

`__INITIAL_STATE__` 或 `__SETUP_SERVER_STATE__` 中提取的图片/视频 CDN URL 带有时效性 `sign` 参数。如果下载返回 0 字节或 403：

1. **不要反复重试同一 URL**——签名已过期
2. **用完整 URL 重新请求页面**（见上一条）→ 解析 `__SETUP_SERVER_STATE__`（优先）或 `__INITIAL_STATE__`（回退）→ 获取新签名的媒体 URL
3. 立即下载（新签名也有时效，尽快完成）

### 音频提取：ffmpeg 必须加 `-map 0:a`（⚠️ HE-AAC 无声提取）

直接用 `ffmpeg -i video.mp4 -vn -acodec pcm_s16le ...` 提取音频时，对 HE-AAC 编码的音频流可能静默失败——生成的文件只有几百字节而非正常的 ~860KB（27s 视频）。**必须显式指定 `-map 0:a`** 选择音频流：

```bash
# ❌ 可能失败（HE-AAC 静默产生微小文件）
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# ✅ 正确：显式映射音频流
ffmpeg -i video.mp4 -map 0:a -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
```

**验证**：WAV 文件大小应约 = 时长(秒) × 16000 × 2 字节（16kHz 16-bit mono），如 27s → ~864KB。小于 1KB 说明提取失败。

### ffmpeg 路径（Windows）

Windows 上 ffmpeg 通常不在 PATH。通过 imageio-ffmpeg 获取：

```bash
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
# 典型输出：C:\Users\...\venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
```

在后续命令中使用完整路径：`"{ffmpeg_path}" -i "{video}" ...`

## ⚠️ 路由陷阱：Agent 经常忘记用这个 skill（L2 已记录）

**症状**：收到 xhslink.com 链接后，Agent 不走 skill 流水线，反而用 browser_navigate / curl 等通用工具试探。用户被迫提醒"调用我们的小红书理解skill做啊？你怎么忘了？"

**根因**：Agent 看到链接 → 本能反应是"抓取网页"而不是"检查有没有专用工具"。即使 skill 触发条件明确写了"用户消息包含 xhslink.com 且表达分析意图"，Agent 也不会主动检索。这跟论文 Q1（路由）的"检索+重排"问题一致——skill 在库里但 Agent 不把它当第一反应。

**对策**：此问题无完全解法（LLM agent 天然不会逐条比对 memory/skill）。lessons.md 已记录为 L2 规则，memory 也已硬化。最有效的防御是**用户主动提醒**。这不是 bug，是当前架构的已知局限。Agent 应当接受自己在这类情况下需要用户提醒。

## 博主全量帖子抓取（与单帖分析的区别）

> 📎 完整技术方案见 [`references/batch-user-scraping.md`](references/batch-user-scraping.md)（2026-07-05 Opus 分析）

本 skill 目前只做单帖分析。如果需要**抓取博主所有帖子**，核心差异：

| 维度 | 单帖（本 skill） | 博主全量（未实现） |
|:---|:---|:---|
| 入口 | 分享短链 | 博主主页 URL |
| 数据源 | `__INITIAL_STATE__` | 需走 Web API + 游标翻页 |
| 登录态 | 不需要 | **必须**（Cookie: `a1`/`web_session`） |
| 核心难点 | 内容提取 | **请求签名（x-s/x-t）** |

推荐混合方案：用 **MediaCrawler** 或 **ReaJason/xhs**（开源）做列表采集，再喂给本 skill 做深度分析。详见参考文件。

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

### 微信长消息分段（⚠️ 已废弃 — 标准已上提到 task-wrapup）

> ⚠️ **以下为历史版本，不再维护。** 微信分段交付标准以 `task-wrapup` skill 第 5 项为准。以下内容仅供参考，不得作为执行依据。
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
**收尾**：
1. 执行收尾自检 → 见 `task-wrapup` skill。包含：步骤完整性、自动审查(L1)、来源区分、产物存档、微信分段。
2. 任务完成后检查 `post-task-review` 触发条件，满足则生成复盘

## ✅ 收尾自检清单（所有干活类 skill 强制引用）

> 设计原则（2026.7.3 PlanWeave 复盘确立）：不靠人喊、不靠记忆、不靠对话窗口。以下步骤焊死在流程里，每个产出型 skill 的最后一步必须逐一执行。

### 1. L1 审查自动触发（不可跳过）

**不是「等用户说审」——是产出一完成就自己跑。**

```
1. 读取本次任务的 sprint-contract
2. 运行 qwen_review.py --contract <契约> --deliverable <交付物>
3. 读回裁决 JSON
4. 向用户呈报：总裁决 + 逐条结论/依据
5. PASS → 继续交付
6. CONDITIONAL ≥ 3 或 FAIL → 停下报告，由用户决定是否升级 Opus（不自触发）
```

> ⚠️ **架构局限（2026.7.2 验证，2026.7.3 重申）**：在 LLM agent 架构下，此步仍可能被跳过。最务实的防御是交付物末尾输出 `【交付完成，请回复"审"触发 L1 审查】`。详见 `l1-review` skill。

### 2. 来源可分辨（不每句标，但读者能分清）

**目标**：读者看完报告能分清「这是帖子说的」「这是 GitHub 上的」「这是 Agent 推断的」。

| 内容类型 | 标注方式 |
|:---|:---|
| 帖子本身信息（标题/作者/互动数据） | 不标，报告开头整体说明来源 |
| 外部数据源（GitHub README/API/第三方） | 报告中首次引用时说明，不用每行贴 URL |
| Agent 推断/建议 | 用 `（推断）` 后缀 |
| 无法核实的事实/数字 | 标注「未核实」，降级为参考 |

> **反面教材（2026.7.3）**：PlanWeave 报告未区分「帖子 desc 内容」「GitHub README 内容」「Agent 推断」，读者分不清哪些是事实哪些是推测。

### 3. 产物存档（下次找得到）

每次产出写进 `~/AppData/Local/hermes/output/` 统一目录：

```
~/AppData/Local/hermes/output/
└── YYYY-MM-DD_主题.md     # 完整分析报告
```

> 这是「追加不修改」原则：每次产出落一个文件，不回头改旧文件。Hermes memory 里可以存一个指针（不存全文），但文件本身是真相源。

### 4. 步骤完整性自检

交付前问自己三个问题：

| 检查点 | 本次是否通过 |
|:---|:---|
| 所有流程步骤都执行了吗？（有没有跳过判断节点？如视频下载决策） | |
| 微信分段发了吗？.md 文件发了 MEDIA 了吗？（长消息两条都做） | |
| 来源分得清吗？（读者能区分帖子内容/外部数据/推断） | |

> 三个问题任何一个答不上 → 不要交付，先补上。

## 🔗 横切约定

- **微信分段标准**：已上提到 `task-wrapup` skill 第 5 项维护。本 skill 的「输出与交付」章节为历史版本，以后以 task-wrapup 为准。

---

## ⚠️ 收尾（强制）

> 执行收尾自检 → 见 `task-wrapup` skill
