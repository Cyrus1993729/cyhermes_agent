# Case Study: 一味君 (yiweijun) Scraping Session

## Account Info
- **Name**: 一味君
- **Biz**: `Mzg3ODcwNTI4NA==` (base64 encoded)
- **Content**: Amazon cross-border e-commerce (选品、站外推广、社群运营)
- **Verified from**: article at `https://mp.weixin.qq.com/s/pMdbeMoqX43AX6k4RNK-bw`

## Extraction Method
- `var biz = "Mzg3ODcwNTI4NA=="` in page source (variable is `biz`, not `__biz`)

## Sogou Results Breakdown
| Page | Total Links | Genuine 一味君 | Noise | Notes |
|------|:----------:|:-------------:|:-----:|-------|
| 1 | 9 | 9 | 0 | All clean |
| 2 | 10 | 8 | 2 | Noise: 补阳还五汤, 大鱼海棠(diff account) |
| 3 | 7 | 1 | 6 | Only 蝙蝠侠影评 is genuine |
| 4 | 8 | 0 | 8 | All noise — Chinese medicine, tea, etc. |
| 5-10 | 39 | 1 | 38 | One Amazon article (选品篇) buried in noise |

**Total genuine yield: 18-19 articles from Sogou**

## Content Extraction
- 15 articles successfully extracted as Markdown
- 3 more with different biz (possibly same author's old account): 大鱼海棠, 蝙蝠侠影评, 双子杀手
- Content directory: `C:\Users\Administrator\yiweijun_kb\articles\`
- Output: individual `.md` files with date prefix

## Key Learnings from This Session

### getmsg API Limitation Discovered
The getmsg API at `mp.weixin.qq.com/mp/profile_ext` **only works for the account owner**. Even after the user logged into mp.weixin.qq.com and had a valid session, calling getmsg for another account's biz returned `ret=-3, errmsg=no session`. This is NOT a cookie/authentication issue — it's a permission check on the server side.

### Chrome Crash During Deep Pagination
Chrome on page 4 of Sogou results crashes with OOM. Workaround: launch fresh browser instance per page. This uses more startup time but avoids the crash.

### Sogou Redirect Token Timing
Tokens expire in ~60 seconds. The combined search+redirect approach (follow links immediately after discovering them on the same page) is the only reliable method.

### Content URL Format
Sogou redirects resolve to `mp.weixin.qq.com/s?src=11&timestamp=...&signature=...` URLs (not the standard `__biz=&mid=&idx=&sn=` format). These signature URLs are valid but don't contain biz in the URL params — must extract from page source.
