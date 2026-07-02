# getmsg API 响应结构

## 请求

```
GET https://mp.weixin.qq.com/mp/profile_ext
  ?action=getmsg
  &__biz=Mzg3ODcwNTI4NA==
  &f=json
  &offset=0
  &count=10
  &is_ok=1
```

## 成功响应

```json
{
  "ret": 0,
  "errmsg": "ok",
  "can_msg_continue": 10,
  "general_msg_list": "[
    {
      \"comm_msg_info\": {
        \"id\": 2247497049,
        \"type\": 49,
        \"datetime\": 1782431380,
        \"fakeid\": \"...\",
        \"status\": 2,
        \"content\": \"\"
      },
      \"app_msg_ext_info\": {
        \"title\": \"文章标题\",
        \"digest\": \"文章摘要\",
        \"content\": \"\",
        \"fileid\": 100000001,
        \"content_url\": \"https://mp.weixin.qq.com/s/xxxxx\",
        \"source_url\": \"\",
        \"cover\": \"https://mmbiz.qpic.cn/...\",
        \"subtype\": 9,
        \"is_multi\": 0,
        \"multi_app_msg_item_list\": []
      }
    }
  ]",
  "next_offset": 10,
  "video_msg_list": [],
  "app_msg_list": []
}
```

## 字段说明

| 字段 | 含义 |
|------|------|
| `ret` | 0=成功，非0=失败 |
| `can_msg_continue` | 下次请求的 offset 值，0=没有更多 |
| `general_msg_list` | JSON 字符串，需再次 parse |
| `comm_msg_info.datetime` | Unix 时间戳 |
| `comm_msg_info.type` | 消息类型，49=图文消息 |
| `app_msg_ext_info.title` | 文章标题 |
| `app_msg_ext_info.content_url` | 文章链接 |
| `app_msg_ext_info.digest` | 文章摘要 |
| `app_msg_ext_info.cover` | 封面图 URL |
| `app_msg_ext_info.is_multi` | 是否多图文（1=一次推送多条） |
| `multi_app_msg_item_list` | 多图文的子文章列表，结构同上 |

## 错误响应

```json
// 未登录
{"base_resp":{"ret":-3,"errmsg":"no session","cookie_count":0},"ret":-3,"errmsg":"no session"}

// 参数错误
{"base_resp":{"ret":-2,"errmsg":"invalid args"},"ret":-2,"errmsg":"invalid args"}

// 频率限制
{"base_resp":{"ret":-1,"errmsg":"system error"},"ret":-1,"errmsg":"system error"}
```

## 分页逻辑

```python
offset = 0
while True:
    response = fetch(f"{API}?action=getmsg&__biz={BIZ}&f=json&offset={offset}&count=10")
    data = json.loads(response)
    
    if data['ret'] != 0:
        break
    
    msg_list = json.loads(data['general_msg_list'])
    if isinstance(msg_list, dict):
        msg_list = msg_list.get('list', [])
    
    for msg in msg_list:
        # 处理正文 (app_msg_ext_info)
        # 处理多图文 (multi_app_msg_item_list)
        pass
    
    if data.get('can_msg_continue', 0) == 0:
        break
    
    offset = data['can_msg_continue']
```

## article 页面变量提取

加载任意一篇文章后，可从页面 JS 变量提取：

```python
article_vars = await page.evaluate("""
    () => {
        return {
            biz: typeof biz !== 'undefined' ? biz : null,
            sn: typeof sn !== 'undefined' ? sn : null,
            mid: typeof mid !== 'undefined' ? mid : null,
            idx: typeof idx !== 'undefined' ? idx : null,
            appmsgid: typeof appmsgid !== 'undefined' ? appmsgid : null,
            msg_title: typeof msg_title !== 'undefined' ? msg_title : null,
            nickname: typeof nickname !== 'undefined' ? nickname : null,
            create_time: typeof ct !== 'undefined' ? ct : (typeof create_time !== 'undefined' ? create_time : null),
        };
    }
""")
```

| 变量 | 含义 | 示例 |
|------|------|------|
| `biz` | 公众号唯一 ID（Base64） | `Mzg3ODcwNTI4NA==` |
| `sn` | 文章签名 | `b6a9020d99...` |
| `mid` | 消息 ID | `2247497049` |
| `idx` | 文章在推送中的位置 | `1` |
| `msg_title` | 文章标题 | `【亚马逊开发篇】...` |
| `nickname` | 公众号名称 | `一味君` |
| `create_time` | 发布时间 (Unix) | `1782431380` |
