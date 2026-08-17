# 产品名/工具名确认终局两招(2026-08-15 小红书第241集实踩)

场景:从视频/帖子识别被提到的工具名,ASR 音译 + web 搜索都 0 命中时,用以下两招收敛。

## 背景

第241集"这2个Skill让AI开发效率提升10倍"提到两个 Skill:
- ASR 音译为 "Advise Project Approach"、"Nurrow Archive"
- web 搜索直接搜 0 命中(名字拼错导致)

## 招一:视频结尾总结帧必查

教程/工具帖结尾常有一屏总结页列出全部工具名。

```bash
# 抽结尾前 30 秒的帧(每秒1帧),逐帧 Vision
ffmpeg -ss <duration-30> -to <duration> -i video.mp4 -vf fps=1 -q:v 3 end_%03d.jpg
```

第241集 241 秒视频,end_005 帧同时出现 `advise-project-approach` 和 `neuro-archive` 两个名字——一条帧解决全部。

## 招二:GitHub API repo 搜索(name 变体)是最终收敛路径

对候选名做变体,逐个搜索:

```bash
curl -s "https://api.github.com/search/repositories?q=<变体>+in:name" | python -c "import json,sys; [print(i['full_name'], i['stargazers_count'], i.get('description','')) for i in json.load(sys.stdin).get('items',[])[:10]]"
```

变体策略:去连字符(neuroarchive)、换大小写(NeuroArxiv)、换词混排(narrow/neuro/arxiv)、拆词。
- 第241集:neuro-archive / narrow-archive 都 404 → `neuroarxiv` 命中 `UditAkhourii/neuroarxiv`(337⭐,"A skill to kill from-scratch coding — Claude checks real arXiv prior art before it designs a new architecture"),描述与视频功能完全吻合 ✓

## 辅助:作者 repo 全列表排除归属错误

`curl -s "https://api.github.com/users/<作者>/repos?per_page=30"` 一次看全该作者所有仓库,判断目标工具是否属于该作者(第241集 AaravKashyap12 只有 1 个 skill 仓库,据此判断第二个 skill 属另一作者)。

## 判定链总结(与 hermes-studio-eval.md 的"Hermes Studio"案例一致)

**视频帧内 UI 文本 > 结尾总结帧 > GitHub API repo 搜索(变体) > web 搜索 > ASR > 封面 OCR**
封面是艺术字/缩略图,OCR 最不可信;ASR 对英文专有名词音译失真。
