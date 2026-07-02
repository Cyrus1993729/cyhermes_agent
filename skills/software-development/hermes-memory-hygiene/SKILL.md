---
name: hermes-memory-hygiene
description: "【Memory 维护】当 memory 使用率超过 80% 或在大量写 skill/改配置后自动检查。审计、去重、合并压缩两个 memory 存储，防止容量耗尽。| 建议触发频率：每周或每次大规模 skill 变更后。"
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, memory, maintenance, cleanup, deduplication]
    related_skills: [hermes-agent, hermes-agent-skill-authoring]
---

# Hermes Memory Hygiene

## Overview

Hermes has two persistent memory stores that inject into every session:

- **User profile** (`target='user'`): Who the user is — identity, preferences, workflow style. Max **1,375 chars**. This fills up FAST when preferences get saved multiple times (e.g. "use Chinese" saved 4× over several sessions).
- **Personal notes** (`target='memory'`): Environment facts, tool quirks, project conventions. Max **2,200 chars**. Less prone to duplication but still needs pruning.

Both stores use substring matching for `replace`/`remove` operations via the `old_text` parameter. This has sharp edges (see Pitfalls).

The most common failure mode: the same preference gets saved every time the user corrects the agent, because the agent never checks whether an equivalent entry already exists. A 1,375-char profile can fill in 3-4 sessions of aggressive "remember this" saves.

## When to Use

- User asks about memory capacity or expresses concern about it filling up
- You suspect duplication (same preference stated 3+ ways across entries)
- You're about to `memory(action='add')` and should check for existing coverage first
- Periodic maintenance (every 5-10 sessions with heavy corrections)
- After a session where the user corrected you multiple times on the same class of thing

**Don't use for:** one-off task progress, session outcomes, PR numbers, or anything that will be stale in a week. Those go in `session_search`, not memory.

## Memory Store Basics

Memory files: `hermes/memories/MEMORY.md` + `hermes/memories/USER.md`，entries separated by standalone `§` lines. See `references/memory-storage-architecture.md` for complete layout + review system data boundary (review_log.jsonl, lessons.md, safety_invariants.md — all stored outside memory).

### User Profile (`target='user'`)

Pattern: short entries about identity and preferences. Typical entry shapes:
- Investment style, risk tolerance, time horizon
- Model/provider preference
- Output language and format preferences
- Communication style (concise, detailed, rough estimates OK, etc.)
- Workflow preferences (discuss then implement, Claude Code for design, etc.)

**Rule of thumb:** Each preference class should be ONE entry. If you have "always use Chinese" in 3 entries plus "output in Chinese" in a 4th, that's 4× the space for 1× the information.

### Personal Notes (`target='memory'`)

Pattern: environment facts, tool quirks, project paths. Typical entry shapes:
- CLI tool installation paths + proxy requirements
- API workarounds (rate limits, auth quirks)
- Project directory paths + key configuration
- Data source routing rules (which APIs need proxy, which need direct)

These are more varied so duplication is rarer, but entries can grow verbose. Trim unnecessary details.

## Deduplication Protocol

### Before Saving ANY New Memory

Always do this mental checklist before `memory(action='add')`:

1. **Scan existing entries** in the target store (shown in the MEMORY block at the top of every turn).
2. **If a similar entry exists**, prefer `replace` to merge the new information into the old entry, rather than `add` to create a sibling.
3. **Only `add` when** the information is genuinely new — no existing entry covers this facet.
4. **Compact phrasing.** User profile entries are consensus between you and the user; don't hedge with "the user said that..." or "it appears that..." — state facts declaratively.

### When You Spot Duplication (Audit Mode)

Protocol for cleaning already-bloated stores:

1. **Categorize entries** — group by what they're about (all "Chinese output" entries together, all "permission protocol" entries together, etc.).
2. **Pick the richest entry** in each group as the merge target.
3. **`replace` that entry** with a merged version containing all information from the group.
4. **`remove` the siblings** — use a unique substring from each (the first 8-10 characters that distinguish it).
5. **Verify** the result — entries count should shrink, usage% should drop.

## Cleanup Workflow (Step by Step)

Here's the concrete protocol used successfully in practice:

### Phase 1: Triage

1. Note the current `usage%` and `entry_count` for both stores (shown in the MEMORY block).
2. Scan entries and identify duplication clusters.
3. Plan merges: which entry absorbs which siblings.

### Phase 2: Merge (user profile)

For each cluster:
```
memory(action='replace', target='user', 
       old_text='<first 15-20 chars of target entry>',
       content='<merged content covering all siblings>')
```

### Phase 3: Remove duplicates

For each sibling:
```
memory(action='remove', target='user',
       old_text='<unique substring ~15 chars>')
```

**Critical:** old_text MUST be unique to that entry. If it matches multiple entries, the tool returns an error with candidate matches — pick a longer or different substring.

### Phase 4: Prune personal notes

Same protocol for `target='memory'`. Remove entries that are:
- Meaningless/placeholder (e.g. standalone `x`)
- Superseded by newer entries
- Too verbose for their value (trim with `replace` instead of full removal)

**Batch parallel operations.** When compressing 6+ entries, invoke multiple `replace` calls in a single tool-call block (up to 8 at once). Each call gets its own old_string/new_string pair. This completes a full audit pass in 2-3 turns instead of 8+. The tool processes them independently — a failure on one does not roll back the others. Only batch operations on different entries; never batch a `replace` and `remove` on the same entry in the same block (the remove would see the pre-replace version and fail the uniqueness check).

**Pointer-to-skill for operational detail.** When an entry is >200 chars and contains configuration recipes, debugging outcomes, or procedural checklists, prefer pointer-to-skill over pointer-to-file. Skills are executable — the agent loads them on demand. Files are passive. Good candidate: MoA configuration details (>500 chars of endpoint URLs, 401 root causes, correct/incorrect config formats) → compress to `MoA china:模型名+模型名+模型名。配置→moa-configuration skill。` The skill carries the full detail; memory only carries the decision (which models) and where to look.

**Pointer-to-file for static reference material.** When an entry is >100 chars and used infrequently (weeks between uses), and the knowledge is more reference than procedure, apply two-tier storage:
1. Write full details to `~/.hermes/references/<topic>.md`
2. Replace memory entry with a short pointer: `Topic → ~/.hermes/references/<topic>.md（一句话摘要）`

This typically saves 50-77% of the memory space. See `references/pointer-to-file-pattern.md` for the full technique, decision criteria, and real examples.

### Phase 5: Verify

Confirm new `usage%` and `entry_count` look healthy. User profile should be under 40%, personal notes under 60% in normal operation.

See `references/cleanup-example.md` for a real before/after: 83%→16% (user profile), 8→2 entries, with the exact merge and remove operations logged.
See `references/stale-tool-reference-example.md` for a real case where memory entries fell behind the skill library.
See `references/pointer-to-file-pattern.md` for the two-tier storage technique: keep a short pointer in memory, full details in a reference file.
See `references/skill-library-conventions.md` for the skill description format, dependency declarations, workflow recipes, and cross-cutting conventions established 2026-07-01.

## Common Pitfalls

1. **Single-character old_text can't uniquely match.** An entry containing just `x` cannot be removed with `old_text='x'` because every other entry containing the letter 'x' (export, proxy, exponential) also matches. There is no workaround for this — the entry is too short to isolate. Prevention: never save single-character or extremely short memory entries in the first place.

2. **Substring matching is case-insensitive and scans ALL entries.** `old_text='proxy'` matches "proxy", "PROXY", "HTTP_PROXY", and "Clash proxy 7897". Be specific enough to narrow to one entry. When unsure, use 15-25 character substrings.

3. **Accidentally removing the wrong entry.** Before confirming a `remove`, verify the old_text uniquely matches your intended target. When in doubt, use a longer substring. If you accidentally remove a useful entry, re-`add` it immediately.

4. **Using `add` when `replace` would merge.** Every `add` consumes capacity. If the information supplements an existing entry, use `replace` to merge them.

5. **Saving session-specific details to memory.** Memory is for durable facts that matter across sessions. Task progress, file counts, PR numbers, "Phase N done" — these belong nowhere (use `session_search` to recover later). A good test: "Will this fact still matter in 2 weeks?" If no, don't save it.

6. **Imperative phrasing in personal notes.** Write "Project uses pytest with xdist" not "Run tests with pytest -n 4". Imperatives get re-read as directives in later sessions and can cause repeated work or override the user's current intent.

7. **Not checking before saving.** The #1 cause of memory bloat. Scan existing entries before every `add`.

8. **Stale tool references — memory vs. skill drift.** When a skill evolves (e.g. pipeline v1.0 → v1.4, scripts move to skill directory), old memory entries may still reference the old paths or version numbers. The skill is authoritative — it's what actually runs. If memory says "use X at /old/path/v1.0" but a skill exists for X at v1.4, the memory is stale. Audit memory tool-reference entries against the skill library periodically, especially after skills are created or updated. When in doubt during a session, check the skill first — don't trust memory's tool path.

## Verification Checklist

- [ ] User profile `usage%` is under 40%
- [ ] Personal notes `usage%` is under 60%
- [ ] No duplicate preferences across entries (same fact stated multiple ways)
- [ ] All entries are declarative facts, not imperatives
- [ ] No session-specific artifacts (PR numbers, phase markers, file counts)
- [ ] No single-character or extremely short entries
- [ ] Before any future `memory(action='add')`, confirmed no existing entry covers the same information

## Automated Scanning (mem_gc.py)

`scripts/mem_gc.py` is a read-only memory scanner that flags four classes of
issues without modifying any files:

- **STALE** — entries with dates + volatile status words past threshold
- **VOLATILE** — entries with "待定/待充值/耗尽/TODO" etc., needing confirmation
- **SUPERSEDED** — content migrated to a skill or replaced by newer entries
- **DUP** — near-duplicate entry pairs (difflib similarity ≥ 0.62)

Usage: `python scripts/mem_gc.py [--days 45] [--out report.md] [--llm]`
The `--llm` flag uses qwen-bailian for semantic dedup judgment on DUP candidates.

Run before manual cleanup to prioritize which entries to merge/delete.

## See Also

- `scripts/mem_gc.py` — 自动化记忆时效扫描器，标记 STALE/VOLATILE/SUPERSEDED/DUP
- `references/skill-optimization-conventions.md` — **Skill 库优化三步法**（合并重复→统一描述→建立依赖）+ 工作流配方模板。增删 skill 时参照此文档。
