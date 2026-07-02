# Stale Tool Reference Example (2026-06-18)

## What happened

Memory had two B站-related entries:

| # | Memory entry | Reality |
|:--|:---|:---|
| #5 | BiliSum v1.19.1 at `C:\Users\Administrator\BiliSum\`, 127.0.0.1:3838 | Installed but **not the active pipeline**. It's a separate packaged web app. |
| #6 | B站视频理解(v1.0): `pipeline.py BV号 --platform bilibili` | **Stale version + wrong path**. Actual working version is v1.4 in `video-understand-core` skill's `scripts/` directory. |

The actual working pipeline: `video-understand-core` skill → `scripts/pipeline.py` or `scripts/quick_summary.py`. Version 1.4. Uses faster-whisper tiny+auto, RapidOCR, DeepSeek.

## Why it matters

When the user asked "which B站 pipeline do we use?", the answer wasn't in memory — it was in the skill library. Memory gave two conflicting/outdated answers. The skill was authoritative.

## Root cause

The pipeline evolved from a standalone script (v1.0) to a skill-packaged set of scripts (v1.4). The BiliSum web app was installed as an alternative but never became the primary tool. Memory was never updated to reflect these changes.

## Prevention

After creating or significantly updating a skill that replaces an older tool setup, review memory for stale references and update them. A quick search: `grep -i "skill_or_tool_name"` mentally against the MEMORY block.
