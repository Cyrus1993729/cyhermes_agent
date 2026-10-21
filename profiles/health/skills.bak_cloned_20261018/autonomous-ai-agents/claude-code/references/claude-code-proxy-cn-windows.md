# Claude Code Proxy Debugging (China / Windows)

## Session: Gold Analyzer Review — June 2026

### Problem
`claude auth login` failed repeatedly:
- Without proxy: HTTP 403 from `platform.claude.com`
- With wrong proxy port (7890): ECONNREFUSED
- The CLI does NOT inherit Windows system proxy settings

### Diagnosis Steps
```bash
# 1. Check if Claude CLI exists
which claude || where claude
npm list -g @anthropic-ai/claude-code

# 2. Try auth — observe error type
claude auth login        # 403 = firewall block, ECONNREFUSED = wrong proxy/port

# 3. Test proxy connectivity
curl -x http://127.0.0.1:7897 https://claude.com -o /dev/null -w "%{http_code}"

# 4. Identify proxy port
# Ask user what proxy software and port. Common: Clash Verge=7897, Clash=7890, v2ray=10809
```

### Solution
```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"
claude auth login   # → "Login successful."
```

### Verification
```bash
claude auth status --text
# Expected: Login method: Claude Pro account, Organization/Email shown, Proxy: http://127.0.0.1:7897
```

### Post-Login: Running Code Reviews
```bash
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

# Print mode (non-interactive) — preferred for one-shot reviews
claude -p "Review this project for bugs" --allowedTools "Read" --max-turns 10

# For larger codebases: increase turns
claude -p "Review all files" --allowedTools "Read" --max-turns 15

# JSON structured output
claude -p "Find bugs" --allowedTools "Read" --max-turns 10 --output-format json
```

### Pitfall: Tool call corruption
When using Claude Code from Hermes terminal tool on Windows, large prompts with JSON-like configs in the prompt body can get corrupted. Keep prompts focused. If output shows "tool call arguments were corrupted", reduce prompt complexity.
