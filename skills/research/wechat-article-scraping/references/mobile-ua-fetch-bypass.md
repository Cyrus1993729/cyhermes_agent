# 移动端 UA 降级：桌面 UA 被跳登录页时的通用解法

> 适用：任何「桌面 UA 拿到的是登录墙/空壳页，但页面本身其实公开」的站点。
> 首次定型于 2026-11-05 小红书 `/discovery/item/` 页。

## 一、先认症状：空壳页长得像「改版了」

用桌面 UA 请求一个分享链接：

- HTTP **302** → `Location: https://<host>/login?redirectPath=...`
- 跟随后拿到的 HTML 只有 **37KB**（正常完整页 165KB）
- `__INITIAL_STATE__` **存在且 JSON 能解析**，但 `note.noteDetailMap` 是 `{}`
- 全页 `noteDetailMap` 出现次数 = 0

**误判风险**：很容易当成「页面结构又改版了」或「数据接口变了」，然后去改解析器、加 cookie、上浏览器——**全部白费**。

## 二、解法：只换 User-Agent，不加 cookie、不走代理

```bash
UA_M='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'

curl -s -D - -o page.html -A "$UA_M" "<分享链接或带 xsec_token 的完整 URL>"
```

实测结果（小红书长图文帖）：

| | 桌面 UA | iPhone UA |
|---|---|---|
| HTTP | 302 → `/login` | **200** |
| HTML 大小 | 37 KB | **165 KB** |
| `__SETUP_SERVER_STATE__` | 无 | **有** |
| 帖子数据 | `noteDetailMap` 空 | `LAUNCHER_SSR_STORE_PAGE_DATA.noteData` 含 title/desc/imageList/interactInfo |

**关键的判定顺序（省时间）**：

```
302 到 /login  ──┐
HTML < 50 KB   ──┼─→ 立刻换 iPhone UA 重试（一次就成）
全页搜不到目标数据键 ──┘

只有换 UA 也失败，才去试 cookie / 浏览器 / 代理。
```

## 三、配套：批量下载静态资源必须用 python，不要用 bash 循环

拿到 24 个图片 URL 写进 `urls.txt` 后，这个写法**一行不报错但一个文件都不生成**：

```bash
while IFS= read -r u; do curl -s -A "$UA" "$u" -o "img_$(printf %02d $i).jpg"; i=$((i+1)); done < urls.txt
# → stat 空、目录里只剩 urls.txt；但同一个 URL 单独 curl -o t.jpg 却正常
```

**不要在循环上花时间调试，直接换 python**：

```python
import urllib.request
ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148'
for i, u in enumerate([l.strip() for l in open('urls.txt') if l.strip()]):
    req = urllib.request.Request(u, headers={'User-Agent': ua, 'Referer': 'https://www.xiaohongshu.com/'})
    data = urllib.request.urlopen(req, timeout=30).read()
    open('img_%02d.jpg' % i, 'wb').write(data)
    print('img_%02d.jpg' % i, len(data))     # ← 必须打字节数
```

**要点**：
1. CDN（如 `sns-webpic-qc.xhscdn.com`）**必须带 UA**，裸 curl 会被拒。
2. 带 `Referer` 更稳。
3. **每个文件落地后 print 字节数**——正常 100–450 KB，**0 字节即失败**，不要等全部下完才发现。
4. 下载完 `ls -la` 数一遍文件数是否等于 URL 数。

## 四、验证清单

- [ ] 响应是 200 不是 302
- [ ] HTML 大小 > 100 KB（或至少明显大于空壳）
- [ ] 目标数据键存在且非空
- [ ] 资源文件数 == URL 数，且每个 > 0 字节

## 五、什么情况这套不管用

- 站点对**所有** UA 都要求登录（真登录墙）→ 回到 cookie / 浏览器路线。
- 页面是纯 JS 渲染、HTML 里本来就没有数据 → 换 UA 无用，走 API 或浏览器。
- 只对移动端 UA 返回简化版（阉割了部分字段）→ 两个 UA 的字段结构要分别解析，不能复用同一个路径。

## 六、别把它当成万灵药

换 UA 能解决的是「**站点主动区分端**」这一类，不是「**站点禁止抓取**」这一类。
如果是付费墙、WAF 挑战、验证码，换 UA 无效——去找搜索引擎缓存、存档站或官方 API。
