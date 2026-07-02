# Xiaohongshu (小红书) Content Access Limitations

## Anti-Crawling Measures

Xiaohongshu has strong anti-crawling protections that make programmatic note access very difficult:

1. **SSR without note data**: The web page returns 200 with `__INITIAL_STATE__`, but `noteDetailMap` is empty/contains `null` keys — note content is NOT server-rendered.

2. **Client-side API requires signatures**: Actual note data is loaded via `edith.xiaohongshu.com` APIs that require `X-S` and `X-T` headers generated from valid authenticated cookies.

3. **Error 300031**: Accessing `/explore/{noteId}` without proper cookies redirects to 404 with `error_code=300031` and message "当前笔记暂时无法浏览".

4. **API endpoints return 404 without signatures**:
   - `edith.xiaohongshu.com/api/sns/web/v1/feed?source_note_id={id}` → 404
   - `edith.xiaohongshu.com/api/sns/web/v2/note/{id}` → 404

## What You CAN Do

- **Search via DuckDuckGo lite**: `lite.duckduckgo.com` can find Xiaohongshu-linked discussions on third-party platforms
- **Bing search**: Works through proxy but may not index Xiaohongshu content well
- **Direct user sharing**: If the user has the note link, ask them to describe/screenshot the content

## What Does NOT Work

- Google search (blocked in China, proxy returns empty)
- Baidu search (blocks programmatic access)
- Direct note page scraping (noteDetailMap empty)
- Note detail API without X-S/X-T signatures
- Using homepage cookies alone (signatures are required, not just cookies)

## Fallback

When Xiaohongshu content is needed:
1. Ask user for a text summary or screenshot
2. Search DuckDuckGo for third-party reposts/discussions
3. Check Bilibili, Zhihu, Toutiao for discussions referencing the note
