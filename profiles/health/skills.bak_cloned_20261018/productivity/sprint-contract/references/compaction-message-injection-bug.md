# Compaction Message Injection Bug

## Discovery Date
2026-07-03

## Symptom
Agent misinterprets historical user instructions as current tasks because compaction summary text gets merged into the user's latest message.

## Root Cause
`agent/context_compressor.py` lines 2596-2616: `_merge_summary_into_tail` path.

When the head (pre-compression section) ends with an `assistant` message and tail (post-compression section) starts with a `user` message (the user's latest input), the role-alternation logic deadlocks:
- `summary_role = "user"` avoids head's assistant → collides with tail's user
- Flip to `assistant` → collides with head's assistant
- → Falls back to `_merge_summary_into_tail = True`

This prepends the LLM-generated compaction summary (which contains verbatim historical user instructions) into the first tail message — the user's CURRENT message.

Agent receives one combined message:
```
[COMPACTION SUMMARY with verbatim historical instructions...]
--- END OF CONTEXT SUMMARY ---

[User's actual current message]
```

The `_SUMMARY_END_MARKER` is not strong enough to prevent the agent from acting on the verbatim instructions in the summary.

## Detection
- Gateway log shows `inbound message: msg='<user's real message>'` — confirm actual message content
- Session hygiene compaction fires at the same second (correlated in logs)
- Agent's first message received contains unexpected historical content

## Fix Options
| Option | Approach | Risk |
|:---|:---|:---|
| A | Merge into tail[1] instead of tail[0] when tail[0] is user message; fallback to standalone system-role message | Changes role alternation logic |
| B | Stronger separation marker when merging into tail | Band-aid, doesn't fix root cause |
| C | Use `role="system"` for summary in deadlock case (independent of user/assistant alternation) | Some providers may not support mid-conversation system messages |

## Code Location
- `agent/context_compressor.py` lines 2596-2648 (role selection + merge logic)
- `agent/context_compressor.py` lines 43-68 (SUMMARY_PREFIX — the instruction text telling agent to ignore summary)
