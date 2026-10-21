# Claude Opus 4.8 架构评审 (2026-06-15)

## 评审背景

用户需要为 B站 和 小红书 建立视频理解 skill，主要分析投资/AI领域内容。
环境: Windows 10, MSYS/git-bash, 无 GPU, Clash 代理 7897, Python 3.11, DeepSeek API。

## 已确认的技术路线

- 下载: yt-dlp (B站可用 bilibili-api-python 免登, 小红书 yt-dlp 当前不可用)
- 转录: faster-whisper int8 + VAD
- 画面文字: OCR (RapidOCR 首选, EasyOCR 备选)
- 整合: DeepSeek 结构化总结
- 不用 VLM 做画面理解

## Q1: faster-whisper 是否值得替换 openai-whisper

**结论: 值得。配置 compute_type="int8"，开 VAD。**

- Windows 安装: 纯 wheel, `pip install faster-whisper`, 依赖 ctranslate2 + onnxruntime, 零编译
- 实际加速: 2-4x (不是广告的 4-5x), int8 量化
- 中文精度: 几乎无劣化 (模型权重相同)
- **关键优势**: 内建 Silero VAD 跳过静音/BGM → 减少幻觉字幕。投资视频常有背景音乐，openai-whisper 在静音段爱"幻觉"出不存在的内容
- 注意: 首次运行从 HuggingFace 下模型, 需代理或 `HF_ENDPOINT=https://hf-mirror.com`

## Q2: OCR 引擎选择

**结论: RapidOCR (rapidocr-onnxruntime) 首选, EasyOCR 备选, 不用 PaddleOCR。**

- PaddleOCR: Windows 安装脆弱 (paddlepaddle + paddleocr 版本错配历史), 不适用
- RapidOCR: PaddleOCR 的 PP-OCR 模型打包成 ONNX, 纯 wheel, 精度 ≈ PaddleOCR, CPU 快
- EasyOCR: 有 Windows temp.zip Defender 锁的已知坑 (已有绕过方案), 精度对大号文字够用
- **比选引擎更重要的**: 帧去重 (phash) — 不做的话逐帧 OCR 又慢又噪

## Q3: B站弹幕+评论

**结论: 评论轻量加入 (高赞前 10-15 条, 独立标注来源), 弹幕不入流水线。**

- 高赞评论常有数据纠错、补充来源 — 值得加
- **必须**单独成块标记为"观众补充（未经核实）", 绝不能和口播混在一起
- 弹幕对投资内容基本是噪声, 最多用来检测"弹幕密度暴增 = 观众认为的关键时刻"

## Q4: 小红书笔记正文

**结论: 接受为已知限制, yt-dlp 元数据兜底 + 支持用户粘贴。**

- 先试 `yt-dlp --dump-json` 看 title/description 是否自带正文 (可能零成本解决)
- 免登抓取正文不可靠 (web端有签名/风控)
- 缺失影响低到中等 — 小红书视频干货在画面+口播里
- 支持用户可选粘贴正文 (对非程序员零成本, 100% 准确)

## Q5: Skill 架构

**结论: 两个门面 skill (bilibili-understand + xiaohongshu-understand) + 一个共享内核模块。**

- 两个 skill: 触发词不同、平台前置步骤不同 (B站走免登, 小红书走 yt-dlp)
- 内核层: 一个共享 Python 模块, `platform=bilibili|xhs` 参数区分, 用绝对路径引用
- 不用 symlink (Windows 权限坑), 不复制粘贴 (代码漂移)

## 整体架构风险

| 优先级 | 风险 |
|:--|:---|
| 🔴 | 帧去重缺失 — 最大遗漏, ffmpeg 抽帧 + pHash 去重 |
| 🔴 | 代理未统一 — 三处代理一处直连, 非程序员卡死点 |
| 🟠 | B站字幕别当主路径 — ASR 主路, 字幕优化 |
| 🟠 | 长视频撑爆上下文 — 超 30 分钟需 map-reduce |
| 🟠 | OCR 数字误读风险 — 标注为低置信, 与口播交叉验证 |
| 🟡 | yt-dlp extractor 易碎 — B站优先 bilibili-api-python |
| 🟡 | 下载策略 — 一次下载完整视频, 本地同时抽音频和帧 |

## 落地顺序建议

① 帧去重 → ② 代理封装 → ③ 换 faster-whisper → ④ OCR 选型 → ⑤ 中间产物缓存
