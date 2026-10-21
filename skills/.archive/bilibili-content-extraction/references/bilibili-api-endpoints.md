# B站 API 端点参考

## 搜索 API

### 用户搜索
```
GET https://api.bilibili.com/x/web-interface/search/type
  ?search_type=bili_user
  &keyword=<URL编码的关键词>
  &page=1

Response (200):
{
  "code": 0,
  "data": {
    "numResults": 2,        // 总结果数
    "numPages": 1,           // 总页数
    "result": [{
      "type": "bili_user",
      "mid": 403082144,      // UID ← 最重要的字段
      "uname": "JASON刘雨鑫",
      "usign": "简介文本",
      "fans": 699341,
      "videos": 1303,        // 视频总数
      "level": 6,
      "official_verify": {
        "type": 127,
        "desc": ""
      },
      "res": [{              // 最近的几个视频
        "aid": 116674179237064,
        "bvid": "BV1MtVZ67Ey8",
        "title": "视频标题",
        "play": "89485",
        "pubdate": 1780912800  // Unix时间戳
      }]
    }]
  }
}
```

### 视频搜索（推荐用于按UP主+地点搜索）
```
GET https://api.bilibili.com/x/web-interface/search/type
  ?search_type=video
  &keyword=<UP主名+地点>
  &page=1

每页最多20条。循环page=1,2,3直到结果<20或numPages耗尽。

Response:
{
  "code": 0,
  "data": {
    "page": 1,
    "pagesize": 20,
    "numResults": 1000,
    "numPages": 50,
    "result": [{
      "type": "video",
      "aid": 1500241247,
      "bvid": "BV1RU421Z7XQ",
      "title": "视频标题",
      "author": "JASON刘雨鑫",
      "mid": 403082144,       // UP主UID
      "tag": "大连,探店,东北",  // 逗号分隔
      "description": "-",      // 通常为空或"-"
      "play": 250821,
      "video_review": 152,     // 弹幕数
      "favorites": 1694,
      "review": 224,           // 评论数
      "pubdate": 1706705692,
      "duration": "3:41"
    }]
  }
}
```

### 全类型搜索（可用于确认视频总量）
```
GET https://api.bilibili.com/x/web-interface/search/all/v2
  ?keyword=<关键词>

Response:
{
  "code": 0,
  "data": {
    "pageinfo": {
      "video": {"numResults": 1000, "pages": 50},
      "article": {"numResults": 41, "pages": 3},
      "bili_user": {"numResults": 0, "pages": 0}
    }
  }
}
```
注意：all/v2 返回的分页信息可能不准确，实际可获取的视频数少于numResults。

---

## 视频详情 API

### 基础详情 + 相关推荐
```
GET https://api.bilibili.com/x/web-interface/view/detail
  ?bvid=<BVID>

Response:
{
  "code": 0,
  "data": {
    "View": {
      "aid": 115292256669538,   // ← 需要用于评论API
      "bvid": "BV1uEn2zJEta",
      "title": "今天来大连的长山岛吃海鲜，看看3个人要花多少",
      "desc": "",                // 通常为空
      "duration": 260,           // 秒
      "pubdate": 1759230000,     // Unix时间戳
      "owner": {"mid": 403082144, "name": "JASON刘雨鑫"},
      "stat": {
        "view": 246244,
        "danmaku": 437,
        "reply": 584,
        "favorite": 572,
        "share": 424,
        "coin": 342
      },
      "tname": "",               // 分区名（可能为空）
      "tid": 212,                // 分区ID
      "cid": 0,                  // 用于字幕API
      "subtitle": {"allow_submit": false, "list": []},
      "pages": [{"cid": 0, "page": 1, "part": "默认"}]
    },
    "Related": [{                // 相关推荐
      "aid": ...,
      "bvid": "...",
      "title": "...",
      ...
    }]
  }
}
```

### 简单详情（不含相关推荐，更轻量）
```
GET https://api.bilibili.com/x/web-interface/view
  ?bvid=<BVID>

Response: 直接包含 View 对象（同上），无 Related 字段。
```

---

## 评论 API

```
GET https://api.bilibili.com/x/v2/reply/main
  ?oid=<aid>           // 从 view API 获取的 aid
  &type=1              // 1=视频, 12=专栏
  &mode=3              // 3=热度排序, 2=时间排序
  &ps=20               // 每页条数

Response:
{
  "code": 0,
  "data": {
    "replies": [{
      "rpid": ...,               // 评论ID
      "mid": ...,                // 评论者UID
      "content": {
        "message": "评论文本<em class=\"keyword\">高亮</em>..."  // 含HTML标签
      },
      "like": 562,               // 点赞数
      "rcount": 82,              // 回复数
      "ctime": 1759233600,
      "replies": [...]           // 楼中楼（可能为空）
    }]
  }
}
```

**评论解析要点：**
- `message` 包含 `<em class="keyword">` 等HTML标签，用 `re.sub(r'<[^>]+>', '', msg)` 清理
- 过滤条件：`like >= 20` 或 `rcount >= 3` 通常能得到有价值的信息
- 寻找自称"本地人"的评论 — 他们通常提供最准确的价格/店名信息
- 高赞评论（>100赞）比低赞评论更可靠

---

## 空间 API（易触发风控）

### 空间视频搜索
```
GET https://api.bilibili.com/x/space/wbi/arc/search
  ?mid=<UID>
  &keyword=<搜索词>
  &order=pubdate
  &ps=30
  &pn=1

⚠️ 此端点频繁返回 412 / "风控校验失败"。
备选方案：使用搜索API (search/type) 代替，通过 author 字段过滤。
```

---

## 其他端点（成功率低）

### AI视频总结
```
GET https://api.bilibili.com/x/web-interface/view/conclusion
  ?bvid=<BVID>

返回 model_result.summary 字段（多数视频返回空）。
```

### 字幕
```
GET https://api.bilibili.com/x/player/v2
  ?bvid=<BVID>
  &cid=<cid>

data.subtitle.subtitles[].subtitle_url → 下载JSON字幕。
多数短视频（2-5分钟）无字幕数据。
```

---

## 速率限制经验

| 操作 | 安全间隔 |
|------|---------|
| 同一端点连续请求 | ≥1.5秒 |
| 切换不同端点 | ≥1秒 |
| 遇到412后重试 | 等待5秒，换端点 |
| 搜索API (search/type) | 最稳定，可连续请求 |
| 空间API (space/wbi) | 最不稳定，容易触发风控 |
| 评论API (reply/main) | 中等稳定 |

建议在循环中每N次请求后插入 `time.sleep(1.5)`。
