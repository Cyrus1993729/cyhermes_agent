# B站 API Response Examples

Verified working endpoints and their response shapes.

## 1. Search UP主

**Request:**
```
GET /x/web-interface/search/type?search_type=bili_user&keyword=刘雨鑫JASON
```

**Response (key fields):**
```json
{
  "code": 0,
  "data": {
    "result": [{
      "type": "bili_user",
      "mid": 403082144,
      "uname": "JASON刘雨鑫",
      "usign": "主业美食旅游节目《XFUN吃货俱乐部》...",
      "fans": 699341,
      "videos": 1303,
      "level": 6,
      "res": [{ "bvid": "...", "title": "...", "play": "89485" }]
    }]
  }
}
```

## 2. Search videos (most reliable)

**Request:**
```
GET /x/web-interface/search/type?search_type=video&keyword=刘雨鑫+大连&page=1
```

Returns up to 20 results per page. Key fields: `bvid`, `aid`, `title`, `author`, `mid`, `tag`, `play`, `pubdate`, `description`, `duration`.

## 3. Video detail

**Request:**
```
GET /x/web-interface/view/detail?bvid=BV1nCHwz7Eda
```

The `data.View.ugc_season` field reveals the series/playlist the video belongs to. Useful for finding related content from the same UP主 in the same region.

## 4. Comments (hot-sorted)

**Request:**
```
GET /x/v2/reply/main?oid={aid}&type=1&mode=3&ps=20
```

`oid` = `aid` from view API. `mode=3` = hot-sort.

Response key fields per reply: `rpid`, `like`, `rcount` (sub-reply count), `content.message` (HTML, strip tags).

## 5. Sub-replies (楼中楼)

**Request:**
```
GET /x/v2/reply/reply?oid={aid}&type=1&root={rpid}&ps=10
```

This is the **most valuable endpoint** for extracting details. Sub-replies often contain:
- Store names that viewers recognized
- Exact addresses from locals
- Price comparisons from locals
- Insider tips ("go to X market instead", "this place is a chain", etc.)

## 6. Episode/series info

**Request:**
```
GET /x/space/wbi/season/list?season_id={id}&pn=1&ps=30
```

⚠️ This endpoint frequently returns 412. The `season_id` comes from `ugc_season.id` in the view/detail response.

## Real session example: Dalian restaurant research

**Target**: JASON刘雨鑫 (UID 403082144), Dalian food videos

**Results**: 5 candidate videos → 4 confirmed Dalian, 1 excluded (actually Yanbian)

**Key extraction pattern**: 
1. Search API found videos by title keyword "大连"
2. View API confirmed video metadata (all desc empty, no subtitles)
3. Comment API found high-level sentiment (price complaints, "良心" praise)
4. Sub-reply API found **crucial location clues**:
   - "美丽园" → confirmed by 5+ sub-replies
   - "照片顶上有个东麓小区" → pinpointed饺子馆 neighborhood
   - "应该是渔人码头那边" → located the烧烤 stall
   - "马栏子菜市场" → identified the market
5. OSM Nominatim geocoded 渔人码头 (中山区虎滩路), 马栏广场 (沙河口区), 长山岛 (长海县)

**What couldn't be extracted**: Exact store names visible only in video frames. Marked as 🔍 in output.
