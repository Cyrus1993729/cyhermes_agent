# Claude Code Auth Diagnosis Protocol

Full diagnosis path developed 2026-06-29 when `claude -p` suddenly returned 403 after working for 11 straight days.

## Symptom
```
$ claude -p "hello" --model opus
Failed to authenticate. API Error: 403 Request not allowed
```

Even `claude config list` and `claude status` return 403.

## Step-by-Step Diagnosis

### Step 1: Verify it's not a one-off
```bash
claude -p "OK" --model opus --max-turns 1 2>&1
claude status 2>&1
claude config list 2>&1
```
If ALL commands return 403, it's not a transient error — auth is broken.

### Step 2: Check auth config
```bash
python -c "
import json, os
with open(os.path.expanduser('~/.claude.json')) as f:
    data = json.load(f)
print('billingType:', data.get('oauthAccount',{}).get('billingType'))
print('orgType:', data.get('oauthAccount',{}).get('organizationType'))
print('claudeCodeFirstTokenDate:', data.get('claudeCodeFirstTokenDate'))
print('passesEligibilityCache:', json.dumps(data.get('passesEligibilityCache',{}), indent=2))
"
```

Key fields to check:
- `claudeCodeFirstTokenDate: null` → CLI has NEVER successfully obtained a token (even if it previously worked — the token may be stored elsewhere)
- `passesEligibilityCache` with `"forbidden"` → Organization explicitly blocked from API access
- `billingType: google_play_subscription` → Google Play billing may not include CLI API access
- `organizationRateLimitTier: default_claude_ai` → Consumer tier, not API tier

### Step 3: Check for env var credentials
```bash
echo "CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN:+SET}"
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+SET}"
```

Even if set, these may not work (Google Play subs don't grant API access).

### Step 4: Test direct Anthropic API
```bash
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-opus-4-20250514","max_tokens":100,"messages":[{"role":"user","content":"OK"}]}'
```

If this also returns 403, the subscription simply doesn't include API access at all.

### Step 5: Check Windows Credential Manager
```bash
cmdkey /list 2>&1 | grep -i "claude\|anthropic"
```
No entries = tokens stored elsewhere (likely in memory/browser session, not OS keychain).

### Step 6: Test alternative paths
```bash
# Nous Research OAuth (Hermes built-in)
hermes chat -q "OK" --model anthropic/claude-opus-4.8 --provider nous -Q
```
If this returns "account balance too low" → OAuth works but needs credits at portal.nousresearch.com.

### Step 7: Check session history for prior working invocations
```bash
# In Hermes: use session_search to find prior successful Claude Code runs
# Look for sessions where claude -p or claude --model opus was called
# and returned actual output (not 403 or max turns)
```

## Common Root Causes

| Cause | Symptoms | Fix |
|-------|----------|-----|
| **Google Play sub ≠ API access** | Worked before, suddenly 403. `passesEligibilityCache: forbidden` | Run `claude login` to refresh OAuth token |
| **OAuth token expired** | Worked for days, suddenly 403. No config changes. | Run `claude login` |
| **Anthropic backend policy change** | 403 appears without any local changes. `passesEligibilityCache` updated recently. | May need to wait or contact Anthropic support |
| **Proxy not set** | `claude auth login` hangs or ECONNREFUSED | `export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="..."` |

## Historical Pattern

As of 2026-06-29, confirmed via session logs: Claude Code CLI worked continuously from June 16 through June 27 (11 days), then suddenly broke with 403 on June 29. No auth refresh was ever needed during those 11 days. This suggests the 403 is NOT a routine token expiry but likely a backend policy change or OAuth session invalidation.

## Recovery Attempts

1. Try `claude login` to refresh OAuth
2. Try `claude auth login --console` for manual code-paste flow
3. If all OAuth paths fail and `billingType: google_play_subscription`, consider that Google Play subs may have lost CLI API access entirely
