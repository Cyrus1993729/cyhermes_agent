# iLink Bot API Behavior Notes

Captured from live testing of the WeChat iLink Bot API during gateway setup.

## Endpoints

Base URL: `https://ilinkai.weixin.qq.com`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `ilink/bot/get_bot_qrcode?bot_type=3` | GET | Fetch QR code for login |
| `ilink/bot/get_qrcode_status?qrcode=<hex>` | GET | Poll QR scan status |
| `ilink/bot/getupdates` | POST | Long-poll for messages |
| `ilink/bot/sendmessage` | POST | Send text message |
| `ilink/bot/sendtyping` | POST | Send typing indicator |
| `ilink/bot/getconfig` | POST | Get config including typing tickets |
| `ilink/bot/getuploadurl` | POST | Get CDN upload URL for media |

## QR Code Behavior

- 🔴 **CORRECTION (2026-10-18, live re-test): QR codes live ~90–120 s, NOT 4–5 s.**
  Three consecutive codes measured **121 s / 92 s / 92 s**. The "4–5 seconds" figure
  previously recorded here was wrong, and it led straight to the false conclusion that
  the QR flow can never be automated and the user must run `hermes gateway setup`
  themselves. Working approach: `gateway-setup` SKILL.md → "QR Login Flow";
  full worked case: `hermes-wechat-delivery` → `references/ilink-rebind-2026-10.md`.
- ⚠️ ~90 s is **still** too short for a human relay. The user must scan AND confirm
  inside the window, so a self-refreshing loop that pushes each new code to Telegram is
  required — and the push must bypass the LLM (`hermes send --to telegram` with a
  `MEDIA:<png>` line), never be relayed by the main agent turn.
- The `qr_login()` function auto-refreshes up to 3 times on expiry
- When status reaches `scaned`, immediately push a second message telling the user to
  **tap confirm in WeChat** — that is the step that actually gets missed; the status
  sits at `scaned` until the code expires.
- After 3 expirations, the function returns `None`
- The QR URL is embedded in a `liteapp.weixin.qq.com` URL that opens inside WeChat
- A plain `https://` URL is also returned — this can be rendered as ASCII art via the `qrcode` package
- QR poll statuses: `wait` → `scaned` → `confirmed`, or `expired`
- On `scaned_but_redirect`, the `redirect_host` field provides a new base URL

## Credential Storage

After successful QR login:
- Credentials saved to `~/.hermes/weixin/accounts/<account_id>.json`
- Config needs `account_id` and `token` in `platforms.weixin`
- Env vars: `WEIXIN_ACCOUNT_ID`, `WEIXIN_TOKEN`, `WEIXIN_BASE_URL`

## Context Token Persistence

- Per-peer context tokens stored in `~/.hermes/weixin/accounts/<account_id>.context-tokens.json`
- Restored on startup for reply continuity across gateway restarts

## Sync Buffer

- Long-poll cursor saved to `~/.hermes/weixin/accounts/<account_id>.sync.json`
- Prevents message loss across gateway restarts

## Typing Indicators

- Typing tickets fetched via `getconfig` API, cached for 10 minutes per user
- `send_typing` with TYPING_START (1) / TYPING_STOP (2) status codes
- Gateway automatically triggers typing while agent processes a message

## Rate Limiting / Retry

- 2-second retry on transient errors (first 2 failures)
- 30-second backoff after 3 consecutive failures
- Session expiry (`errcode=-14`) pauses for 10 minutes
- `errcode=-2` with `errmsg="unknown error"` is also a stale-session signal
- Token lock prevents multiple gateway instances using the same token

## Encryption

- Media files use AES-128-ECB with per-file random keys
- Requires `cryptography` Python package
- CDN base URL: `https://novac2c.cdn.weixin.qq.com/c2c`
