# Multi-Round Opus Design Refinement Pattern

When the user wants Opus to design something, a single "here's everything, give me the answer" prompt often produces a generic result. The multi-round pattern iteratively tightens the design by feeding each round's output + new constraints into the next.

## Pattern (3 rounds typical)

```
Round 1: Opus analyzes external input + existing scheme → "what to incorporate?"
         (Opus gets: XHS post + our current scheme → returns priority-ranked integration points)
    ↓ user reviews, confirms direction
Round 2: Opus merges Round 1 results with original scheme → "unified plan"
         (Opus gets: Round 1 output + original scheme → returns merged plan)
    ↓ user approves plan
Round 3: Opus designs implementation for specific environment → "how to land it here"
         (Opus gets: merged plan + actual config/env details → returns phased implementation)
```

## Prompt Construction: File Concatenation for Long Prompts

Opus design prompts are often 8-10KB and multi-part. Build them with file concatenation:

```bash
# Build the prompt from pieces
write_file("C:/tmp/prompt_header.md", "# Context\n...")
write_file("C:/tmp/prompt_body.md", "# Full post content\n...")
# ... in terminal:
cat "C:/tmp/prompt_header.md" "C:/tmp/prompt_body.md" > "C:/tmp/full_prompt.md"
echo "" >> "C:/tmp/full_prompt.md"
echo "## 你的任务" >> "C:/tmp/full_prompt.md"
echo "..." >> "C:/tmp/full_prompt.md"
```

## Delivery: Background + Process Log

Long Opus calls (2-5 min) use background mode:

```bash
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
PROMPT=$(cat "C:/tmp/full_prompt.md")
timeout 300 claude -p "$PROMPT" --model opus --max-turns 10
# → terminal(background=true, notify_on_complete=true, timeout=360)
```

**⚠️ Truncated output**: The completion notification truncates long Opus output. Retrieve the full output:

```python
process(action="log", session_id="proc_<id>", limit=500)
```

## Windows Path Quirks

- `write_file("/tmp/foo.md")` resolves to `C:\tmp\foo.md` (outside workspace) → OK for temp prompts
- MSYS `cat /tmp/foo.md` fails → use `cat "C:/tmp/foo.md"` (forward slashes OK)
- `claude -p "$(cat file)"` works on git-bash for prompts up to ~10KB
- `$(cat ...)` avoids MSYS path translation that would break with `/foo` params

## Smoke Test Always

Every Opus call starts with:
```bash
timeout 60 claude -p "OK" --model opus --max-turns 1
```
Failure → abort, don't burn credits on a broken path.
