---
name: video-transcript-qa
description: "Use when 视频转写的数字/专有名词要能直接用。"
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [asr, transcription, whisper, video, qa, vision]
---

# 视频转写质量保证（质量层，不是管线）

> 本 skill 只管**转写准不准、关键量怎么核**。
> 下载/解析/分段的完整管线属于其他 skill：
> 小红书单帖 → `xiaohongshu-analysis`｜B 站全量 → `bilibili-understand`｜共用引擎 → `video-understand-core`。
> **三者都是用户自有 skill，不改它们；本 skill 只补“转录质量”这一层。**

适用：中文教程、菜谱、产品讲解、投资分析这类“视频里的话就是数据”的场景。
来源：2026-11-18 小红书「番茄肉丝烩饭」视频（6af6bff6…，2 分 13 秒）实踩。

---

## 一、`initial_prompt` 是免费的一档准确率

faster-whisper 支持 `initial_prompt`——**把本领域专有名词先告诉模型**，而不是让它从零猜。

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    wav,
    language="zh",
    vad_filter=True,
    initial_prompt="番茄肉丝烩饭，减脂餐，娃娃菜，香干，番茄膏，洋葱，猪肉丝，米饭，生抽，料酒，淀粉，橄榄油。",
)
```

**做法**：跑之前先扫一眼标题、封面 Vision、话题标签，把可能出现的名词列成一句逗号分隔的提示。
不要求写全，覆盖「食材/工具/步骤/专业术语」四类就够。

**实测效果**：tiny 裸跑把「番茄膏」听成「番茄高」、「娃娃菜」听成「花菜」；
换 `small` ＋ `initial_prompt` 后 28 段里专有名词基本全对。

**成本**：`small` CPU int8 约 5–10x 实时，2 分 13 秒音频 30–60 秒跑完，完全可接受。

---

## 二、⚠️ 数字一定会被听错——关键量必须回帧核字幕

实测最典型的一例：

```
字幕原文：「来适量的油，大概 6 克的样子」
ASR 输出：「来适量的油，大概六颗的样子」
```

**「六颗」和「6 克」差三个数量级。** ASR 对「克/颗/勺/两/分」这类量词几乎不可靠。

**规则：口播里出现的 `克数 / 毫升 / 时间 / 温度 / 火候档位 / 品牌型号`，一律抽关键帧用 Vision 读字幕原文。**
字幕是作者剪片时手打的，**通常比口播的机器转录更准**。

```bash
FF="$(python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")"
mkdir -p frames
for t in 9 11 44 56 78 88 96 118; do
  "$FF" -y -ss $t -i video.mp4 -frames:v 1 -q:v 2 "frames/f_${t}.jpg" -loglevel error
done
```

- **一次抽 8–12 帧**覆盖关键步骤即可，**不要逐秒抽**（Vision/OCR 成本高）
- 抽帧位置按 ASR 段落时间轴选：每个关键动作的**中段**，避开转场
- Vision 提问照抄这句：「画面里有没有字幕/贴纸文字？如果有，逐字读出」
  —— 比 OCR 稳，尤其字幕是艺术字/描边字时

---

## 三、抽帧顺手能拿到的额外信息（不重抽）

同一批帧一次拿多个信息：

- **份量/成品形态**（博主说「分成两份或三份吃」→ 看锅里和碗里的比例）
- **食材清单**（画面前景的原料比口播更全；本次从帧里看到锅里有娃娃菜，口播根本没提）
- **品牌/型号**（包装、调味瓶、工具铭牌）

---

## 四、交付时量要标来源

同一个数字，来源不同、置信度就不同，下游（营养核算、投资分析）拿到时必须是可判别的。

| 标注 | 含义 |
|:---|:---|
| `〔视频字幕原文〕` | 作者手打字幕，关键帧 Vision 逐字核过 → **最可信** |
| `〔口播转录〕` | 仅 ASR、未回帧核 → **数字类不可直接引用** |
| `〔推断〕` | 从画面/常识推的 |

✅ 写：下油 **6 g**（视频字幕原文「大概 6 克的样子」，已用关键帧核对）
❌ 写：下油约 6 g（ASR 转录）

---

## 五、与其它 skill 的分工

| 要做的事 | 去哪 |
|:---|:---|
| 小红书链接解析→下载→ASR/OCR→报告 | `xiaohongshu-analysis`（用户自有，勿改） |
| B 站全量视频理解 | `bilibili-understand`（用户自有，勿改） |
| 共用下载/ASR 引擎 | `video-understand-core`（用户自有，勿改） |
| **转写准不准、数字怎么核** | **本 skill** |
| 转出来的食材要去核算营养 | `health-assistant-delegation` |
