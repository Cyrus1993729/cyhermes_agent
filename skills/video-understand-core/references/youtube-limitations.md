# YouTube Video Access — Limitations & Workarounds

Last verified: 2026-07-09

## Current Posture

As of mid-2026, YouTube enforces strict bot detection on ALL unauthenticated API access:

| Method | Result |
|--------|--------|
| yt-dlp (no cookies) | `LOGIN_REQUIRED` / "Sign in to confirm you're not a bot" |
| yt-dlp (`--cookies-from-browser chrome`) | DPAPI decryption failure (Windows) |
| yt-dlp (`--cookies-from-browser edge`) | Cookie DB copy failure |
| yt-dlp (`--extractor-args "youtube:player_client=android"`) | Same LOGIN_REQUIRED |
| pytube | HTTP 400 / bot detection |
| InnerTube API (ANDROID client) | `playabilityStatus: LOGIN_REQUIRED` |
| InnerTube API (MWEB client) | `playabilityStatus: LOGIN_REQUIRED` |
| InnerTube API (WEB client) | `playabilityStatus: LOGIN_REQUIRED` |
| youtube-transcript-api | IP blocked — `RequestBlocked` |
| Invidious API (`inv.nadeko.net`, `invidious.fdn.fr`, etc.) | Endpoint disabled or empty response |
| Piped API (`pipedapi.kavin.rocks`) | Empty response |
| yewtu.be API | Empty response |
| cobalt.tools v7 API | Shut down Nov 2024 |
| YouTube embed page (`/embed/VIDEO_ID`) | Returns 200 HTML but no stream URLs, no captions data |

## What DOES Work (Without Auth)

### YouTube oembed API — metadata only

```
curl -x http://127.0.0.1:7897 \
  "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=VIDEO_ID&format=json"
```

Returns: `title`, `author_name`, `author_url`, `thumbnail_url`, `type`

**Use case**: Quick metadata extraction when full video access is blocked. Useful for:
- Getting video title/author to decide whether it's worth the auth effort
- Filing/sorting videos by metadata
- Fallback when all download methods fail

**Does NOT return**: duration, description, captions, stream URLs, view count

### youtube-nocookie oembed — same as above

```
curl -x http://127.0.0.1:7897 \
  "https://www.youtube-nocookie.com/oembed?url=https://www.youtube.com/watch?v=VIDEO_ID&format=json"
```

Identical output shape, sometimes more reliable.

## What's Needed for Full Access

YouTube now requires **authentication** for basically everything — even reading public video metadata.

Options (in order of viability):

1. **Cookies file** — Export from a logged-in browser, pass with `yt-dlp --cookies cookies.txt`
   - Firefox: `yt-dlp --cookies-from-browser firefox` (most reliable on Windows)
   - Manual export: browser extension → `cookies.txt` → `yt-dlp --cookies cookies.txt`
   
2. **OAuth token** — `yt-dlp --oauth2-client-id ... --oauth2-client-secret ...`
   - Requires registering a YouTube API application
   - More complex setup but more durable

3. **User manually downloads** — User downloads audio/video and provides file path

## Fallback Strategy

When YouTube auth is unavailable:

1. **Try oembed** → get title + author (works through proxy)
2. **Check if title is descriptive enough** — some Chinese finance channels put the full conclusion in the title
3. **Search for the report/topic separately** — if the video is about a public report (UBS, Goldman, etc.), search for the original report
4. **Ask user** — present options: provide cookies, manually download, or accept title-based analysis

## Key Insight

Chinese finance YouTube channels (like 老厉害) often put their **full thesis/conclusion in the video title** as a hook. When full video access is blocked, the title alone can provide substantial analytical value — treat it as a structured summary rather than dismissing it.
