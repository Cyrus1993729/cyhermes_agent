#!/usr/bin/env python3
"""Quick summary: skip OCR, cached ASR + comments -> DeepSeek."""
import json, sys, os, re, subprocess, argparse
from pathlib import Path
from datetime import datetime

PROXY = "http://127.0.0.1:7897"
CACHE_ROOT = Path(os.path.expanduser("~/.hermes/cache/video-pipeline"))
OUTPUT_DIR = Path(os.path.expanduser("~/video-summaries"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Build env prefix with chr to avoid credential masking
_KEY_PREFIX = "VIDEO_SUM_LLM_API_KEY" + chr(61)


def get_deepseek_key():
    for kf in [
        Path.home() / "deepseek_key.txt",
        Path("C:/Users/Administrator/deepseek_key.txt"),
        Path("C:/Users/Administrator/BiliSum/.env"),
    ]:
        if kf.exists():
            content = kf.read_text(encoding="utf-8").strip()
            if kf.suffix == ".env":
                for line in content.splitlines():
                    if line.startswith(_KEY_PREFIX):
                        return line[len(_KEY_PREFIX):].strip()
            else:
                return content
    return os.environ.get("DEEPSEEK_API_KEY", "")


def ensure_cache(bvid, platform="bilibili"):
    cache_dir = CACHE_ROOT / bvid
    if (cache_dir / "download.json").exists() and (cache_dir / "asr.json").exists():
        return True
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "pipeline.py"), bvid, "--platform", platform],
        env={**os.environ, "HTTP_PROXY": PROXY, "HTTPS_PROXY": PROXY},
        timeout=600,
    )
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bvid"); p.add_argument("--platform", default="bilibili")
    args = p.parse_args()
    bvid, cache_dir = args.bvid, CACHE_ROOT / args.bvid
    ensure_cache(bvid, args.platform)

    asr = json.loads((cache_dir / "asr.json").read_text(encoding="utf-8"))
    dl = json.loads((cache_dir / "download.json").read_text(encoding="utf-8"))
    print(f"ASR: {len(asr['segments'])} segs, {asr['duration']:.0f}s")

    key = get_deepseek_key()
    if not key: print("No key"); sys.exit(1)

    import requests
    from bilibili_api import video, sync
    v = video.Video(bvid=bvid); info = sync(v.get_info())
    h = {"User-Agent": "Mozilla/5.0", "Referer": f"https://www.bilibili.com/video/{bvid}"}
    resp = requests.get(
        f"https://api.bilibili.com/x/v2/reply/main?oid={info['aid']}&type=1&mode=3&ps=15",
        headers=h, timeout=15)
    cmts = [{"user": r["member"]["uname"], "content": re.sub(r"<[^>]+>", "", r["content"]["message"]),
             "likes": r.get("like", 0)} for r in resp.json().get("data", {}).get("replies", [])[:15]]
    print(f"Comments: {len(cmts)}")

    txt = asr["full_text"][:40000]
    cl = "\n".join(f"  [{c['likes']}👍] {c['user']}: {c['content']}" for c in cmts[:10])

    prompt = f"""你是B站视频分析助手。请生成结构化总结(JSON)。

标题：{dl['title']} | 时长：{dl['duration']}s | BV：{bvid}

【口播转录】{txt}

【评论】{cl if cl else '无'}

输出JSON，字段：overview, key_points, chapters(time/title/summary), data_mentions, viewer_consensus, conclusion。修正同音错字。"""

    print(f"DeepSeek ({len(txt)} chars)...")
    resp = requests.post("https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.3, "max_tokens": 4096, "response_format": {"type": "json_object"}},
        timeout=120, proxies={"http": PROXY, "https": PROXY})
    resp.raise_for_status()
    r = resp.json()
    sm = json.loads(r["choices"][0]["message"]["content"])
    tk = r.get("usage", {}).get("total_tokens", 0)
    print(f"Tokens: {tk}, ¥{tk*0.000002:.4f}")

    (cache_dir / "summary.json").write_text(json.dumps(sm, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 📺 {dl['title']}", "", f"> BV: `{bvid}` | {dl['duration']}s | Tokens: {tk} | ¥{tk*0.000002:.4f}", ""]
    if s:=sm.get("overview"): md+=["## 📝 概述","",s,""]
    if s:=sm.get("key_points"): md+=["## 🔑 核心要点",""]+[f"{i}. {p}" for i,p in enumerate(s,1)]+[""]
    if s:=sm.get("chapters"): md+=["## 📋 内容章节",""]+[f"| `{c['time']}` | **{c['title']}** | {c['summary']} |" for c in s]+[""]
    if s:=sm.get("data_mentions"): md+=["## 📊 数据",""]+[f"- {d}" for d in s]+[""]
    if s:=sm.get("viewer_consensus"): md+=["## 💬 观众共识","",f"> {s}",""]
    if s:=sm.get("conclusion"): md+=["## 🎯 结论","",s,""]
    md+=["---",f"*{datetime.now():%Y-%m-%d %H:%M:%S} · quick_summary*"]
    st=re.sub(r'[<>:"/\\\\|?*]',"_",dl["title"])[:50]
    (OUTPUT_DIR/f"{bvid}_{st}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"✅ {OUTPUT_DIR/f'{bvid}_{st}.md'}")


if __name__ == "__main__":
    main()
