# GitHub 视频理解工具生态调研 (2026-06，更新 6/15)

用户要求全自动 B站/小红书视频理解（口播+画面，零人工参与），搜索了 GitHub 上相关项目。

## 架构决策 (2026-06-15)

**VLM 画面理解已弃用** — 详见 `references/vlm-vs-ocr-analysis.md`。对投资/数据型视频，VLM 本质上就是高级 OCR，无法做真正的图表分析。当前流水线：

```
yt-dlp → audio(faster-whisper) + frames(ffmpeg) → OCR → DeepSeek 整合
```

OCR 比 VLM 更准确更便宜，ASR+OCR 的文字整合由 DeepSeek 完成（其推理能力远超 VLM 的"看图说话"）。

## 核心需求
- B站/小红书视频 → AI 总结 + 时间轴分段 + 画面文字提取（OCR）
- 无需人工参与，全自动 pipeline
- 输出格式参考 B 站 AI 总结（时间轴分段 + 核心要点）

## B站视频理解工具（按 Star 排序）

| 项目 | ⭐ | 画面理解 | 状态 | 评价 |
|:---|:---|:---|:---|:---|
| [BibiGPT-v1](https://github.com/JimmyLv/BibiGPT-v1) | 6,113 | ❌ | 活跃 | 一键多平台AI总结，无VLM无OCR。 |
| [BiliSum](https://github.com/lycohana/BiliSum) | 329 | ✅ VLM | ❌ 已放弃 | Windows ffmpeg子进程bug，不可修复。 |
| [video-helper](https://github.com/LDJ-creat/video-helper) | 35 | ❌ | 活跃 | 思维导图+笔记。 |
| [video-summarizer](https://github.com/liang121/video-summarizer) | 34 | ❌ | 活跃 | Claude Code Skill，yt-dlp(1800+平台)+faster-whisper+LLM。下载+ASR部分可用。 |
| [openclaw-video-vision](https://github.com/maim010/openclaw-video-vision) | 19 | ✅ VLM | Agent Skill | OpenClaw插件，whisper+VLM。需适配Hermes。 |
| [bilibili-summary](https://github.com/jackwener/bilibili-summary) | 15 | ❌ | 活跃 | B站专用ASR+LLM。 |
| [bilibili-video-summary-agent](https://github.com/Cansiny0320/bilibili-video-summary-agent) | 7 | ❌ | 活跃 | CLI工具，字幕/Whisper+LLM。 |
| [vivid](https://github.com/tiderzheng/vivid) | 4 | ❌ | 新项目 | 字幕+ASR+AI摘要。 |
| [bili-summary](https://github.com/gkd2323c/bili-summary) | 0 | ❌ | 新项目 | Whisper.cpp(Vulkan)+弹幕+评论+JSON输出。弹幕/评论部分可复用。 |
| [bilibili-summary (jayhchen)](https://github.com/jayhchen/bilibili-summary) | 1 | ❌ | Agent Skill | Universal AI agent skill for B站 transcription。 |
| [colommar/bilibiliAISubtitles](https://github.com/colommar/bilibiliAISubtitles) | 1 | ❌ | 新项目 | 调用B站官方AI字幕/总结API。 |

**关键发现：没有任何第三方工具在「下载+ASR+画面内容提取」三项俱全且稳定可用。** BiliSum 最接近但已废弃。官方的 AI 总结 (B站 conclusion API) 需要登录（返回 -403），不具可行性。

## 小红书下载生态

| 项目 | ⭐ | 特点 |
|:---|:---|:---|
| **yt-dlp 原生** | — | 内置 `XiaoHongShu` extractor ✅ 确认可用 `yt-dlp --list-extractors \| grep XiaoHongShu` |
| [video-downloader (lulu-ls)](https://github.com/lulu-ls/video-downloader) | 39 | 多平台（抖音/B站/快手/小红书）Python下载器 |
| [xhs_downloads](https://github.com/golordmanji-stack/xhs_downloads) | 13 | 小红书专用，图文+视频+高清原图 |
| [video-downloader-skill (wxhou)](https://github.com/wxhou/video-downloader-skill) | 3 | Claude Code Skill，支持抖音/Twitter/B站/YouTube/小红书 |

**小红书视频理解：无现成工具。** yt-dlp 解决了下载，但 ASR + OCR + 总结必须自建。小红书的特殊挑战：视频内容大量以内嵌文字呈现（口播少），OCR 是关键环节。

## B站/小红书官方 AI 总结（不可用）

| 平台 | 端点 | 结果 | 
|:---|:---|:---|
| B站 | `x/web-interface/view/conclusion/get` | `-403 访问权限不足` — 需登录 |
| 小红书 | 问一问 AI | 重定向到登录页 `error_code=300017` |

即使登入后使用 cookie，风控风险高（B站 detail 接口返回 `-352`）。**不建议走这条路。**

## 推荐方案（2026-06-15 更新）

**唯一可行方案：自建 Pipeline。** 

```
yt-dlp (B站/小红书) → faster-whisper ASR + ffmpeg 帧 → OCR (RapidOCR) → DeepSeek 整合总结
```

成本 ¥0.01-0.02/视频。ASR 转录 + OCR 抽文字 + LLM 推理 覆盖了投资/AI类视频的全部信息需求。详见 `references/ai-video-pipeline.md`。

**为什么不用 VLM：** 详见 `references/vlm-vs-ocr-analysis.md`。核心原因：VLM 对数据图表 = 高级 OCR，不会做真正的量化分析，且成本是 OCR 的 5-10 倍。
