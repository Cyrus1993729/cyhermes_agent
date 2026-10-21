# 微信 iLink Bot 重新绑定实战（2026-10-18）

> 场景：用户很久没用微信 → iLink 的 bot 会话服务端超时 → 微信通道全挂。
> 触发语：“帮我连一下这个微信的 bot”。全程约 40 分钟，大量时间花在二维码时效上。

## 1. 症状与诊断（先做这步，别急着扫码）

**症状**：`errors.log` 里每 10 分钟一条（历史累计 1200+ 条）：

```
ERROR gateway.platforms.weixin: [Weixin] Session expired; pausing for 10 minutes
ERROR cron.scheduler: Job 'xxx': delivery error: Weixin send failed: iLink sendmessage error: ret=None errcode=-14 errmsg=session timeout
```

**这不是配置错**：`.env` 里 `WEIXIN_ACCOUNT_ID/TOKEN/BASE_URL` 都在、格式也对。是**服务端把 bot 会话判超时了**（长期不发消息会被回收）。用户主观感受“我好久没用微信了”正是线索。

### 🔴 诊断时的假阳性陷阱（本会话踩到，浪费一轮）

iLink 的 POST 接口**必须带齐全三个东西**，漏一个就返回和“会话过期”**一模一样**的 `errcode:-14 session timeout`：

| 项 | 值 |
|:--|:--|
| header `AuthorizationType` | `ilink_bot_token` |
| header `X-WECHAT-UIN` | 随机数字串（`str(random.randint(10**8,10**9))`） |
| body `base_info` | `{"channel_version": CHANNEL_VERSION}`（本机 CHANNEL_VERSION=`2.2.0`） |
| header `iLink-App-Id` / `iLink-App-ClientVersion` | `bot` / `(2<<16)|(2<<8)|0` |
| header `Authorization` | `Bearer <token>` |

**教训**：验证 token 有效性时，**必须照抄 `_headers()` + `_api_post()` 的完整格式**；否则会把“我请求写错了”误判成“token 也挂了”，得出“重扫码也没用”的错误结论。
正确格式下的成功响应长这样：
```json
{"msgs":[],"sync_buf":"CAAY7rDI75Q0","get_updates_buf":"CgkIABjusMjvlDQ..."}
```

## 2. 二维码接口与 90 秒生死线

```
GET  https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3
  → {"qrcode":"<32位hex>", "qrcode_img_content":"https://liteapp.weixin.qq.com/q/XXXX?qrcode=<hex>&bot_type=3", "ret":0}
GET  https://ilinkai.weixin.qq.com/ilink/bot/get_qrcode_status?qrcode=<hex>
  → {"ret":0,"status":"wait"|"scaned"|"scaned_but_redirect"|"expired"}
  → 成功时额外带 ilink_bot_id / bot_token / baseurl / ilink_user_id
```
这两个是 **GET**，只需要 `iLink-App-Id` + `iLink-App-ClientVersion` 两个头，不要 token。

### 🔴 核心约束：二维码只有约 90 秒寿命

三张码实测存活 **121s / 92s / 92s**。用户“看到消息→掏手机→扫码→在微信里点确认”根本来不及，第一次串行尝试就卡在这里（日志实锤）：
```
15:26:42 第 3 张码生成
15:28:12 状态: scaned     ← 用户扫上了
15:28:14 状态: expired    ← 2 秒后失效，确认没赶上
```

**结论：不要走“我生成→我发→用户扫”的人工接力，必须让脚本自己循环补发。**

## 3. 可用方案：自动发码 + 自动补发 + 直接推 Telegram

脚本（本机 `C:\Users\Administrator\AppData\Local\Temp\weixin_bind_loop.py`）结构：

```
for cycle in 1..12:
    token,url = GET get_bot_qrcode
    落盘 token（也编码在 PNG 里，可用 cv2.QRCodeDetector 反解）
    自检 GET get_qrcode_status  ← 🔴 必须先自检，见下方“URL 拼接坑”
    生成 PNG -> 用 `hermes send --to telegram "...MEDIA:<png>"` 直接推给用户
    轮询 status 最长 130s：
        scaned  -> 立刻再推一条“⚠️ 立刻在微信点确认！”
        expired -> continue（补发下一张）
        拿到 ilink_bot_id+bot_token -> 写结果文件，退出
```

要点：
- **推送用 `hermes send`，不要靠主 agent 转发**——它无 LLM 延迟，`--to telegram`，消息里写 `MEDIA:<png>` 即附图；已配好的平台无需 gateway 在跑。
- **检测到 `scaned` 立刻催确认**——最容易漏的一步就是“扫了但没在微信里点确认”，状态会一直卡在 `scaned`。
- 每轮控制在 12 次以内，并在首条消息里写明轮数，避免无限刷屏。
- 依赖：`uv venv` 建临时环境 + `uv pip install "qrcode[pil]"`（本机系统 python 无 qrcode，PIL 有）。

### 🔴 URL 拼接坑（害用户白扫一次）

第一版把 base_url 拼了两遍（`{BASE}/{BASE}/ilink/bot/get_qrcode_status`）→ 轮询**全是 HTTP 404**，用户扫码结果完全没接住。
**修法**：`api_get(endpoint, base=None)` 只接收相对 endpoint， pełen URL 由函数拼；重定向用 `base` 参数传递。
**加保险**：发码**之前**先自检一次状态接口，URL 不通就立刻中止并通知用户，绝不发出“扫了也接不住”的码。

### 扫码结果丢失后的补救

如果轮询断了但码已经发出去，**PNG 里就编码着完整 URL**（含 qrcode token），可反解回来继续查：
```python
import cv2
data,_,_ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(png_path))
# data = https://liteapp.weixin.qq.com/q/XXXX?qrcode=<token>&bot_type=3
```
（本机无 decoder，用 `uv pip install opencv-python-headless` 装到临时 venv 即可。）

## 4. 绑定成功后写什么

1. **`.env` 三行**（纯文本替换，先 `cp` 备份）：`WEIXIN_ACCOUNT_ID` / `WEIXIN_TOKEN` / `WEIXIN_BASE_URL`
2. **账号文件** `weixin/accounts/<account_id>.json`：`{"token","base_url","user_id","saved_at"}`
3. **核对 home channel**：新绑定的 `ilink_user_id` 必须等于 `.env` 的 `WEIXIN_HOME_CHANNEL`，否则 cron 通知会路由错。本次两者一致（`o9cq805...@im.wechat`）。

## 5. 🔴 必须重启 gateway（适配器把 token 缓存在实例里）

`WeixinAdapter.__init__` 里 `self._token = ... _wx_secret("WEIXIN_TOKEN")` —— **只在启动时读一次**，改 `.env` 不会热重载（这点和 cron 的 .env 重载机制不同，别搞混）。
所以绑定完，运行中的 gateway 里微信通道依然是死的。

**重启方式**（按安全性排序）：
1. ✅ 让用户在 Telegram 发一句 `/restart` —— gateway 内置斜杠命令（`gateway/run.py` 的命令注册表 `"restart": self._handle_restart_command`），优雅重启，不会把服务搞挂
2. ⚠️ 杀 PID + `schtasks /run /tn Hermes_Gateway` —— 全自动但会断约 30s；**注意 `hermes gateway restart/stop` 在 gateway 进程内会被安全防护 BLOCKED**

## 6. 验证（重启前就能做，很有用）

重启前就可以用**新进程**验证绑定是否真的成功——因为新进程会重新读 `.env`：
```bash
hermes send --to weixin "微信通道测试" --json
# 期望 {"success": true, "platform": "weixin", "chat_id": "...@im.wechat", ...}
```
这条**通了 = 绑定确实成功**，剩下的纯粹是“让 gateway 用上它”的运维问题，和绑定本身无关。

## 7. 时间线参考（本次）

| 时刻 | 事件 |
|:--|:--|
| 15:0x | 发现 1200+ 条 Session expired，确认真因是 iLink 会话超时 |
| 15:1x | 第一版 watcher：拉码→人工转发→码过期（121s/92s/92s） |
| 15:22 | v2 循环（自动推 Telegram）；第 3 张扫到但差 2s 没确认 |
| 15:31 | v3 循环（12 轮 + scaned 催确认） |
| **15:32:23** | **status=confirmed，绑定成功** |
| 15:33 | 写完 .env + 账号文件，`hermes send --to weixin` 端到端验证通过 |

## 8. 复用时直接抄的最小步骤

1. 确认症状：`errors.log` 出现 `errcode=-14 session timeout` / `Session expired; pausing`
2. `uv venv` + `uv pip install "qrcode[pil]"`
3. 跑自动补发循环（记得**发码前自检状态接口**）
4. 用户扫**最新**那张，扫完**立刻在微信点确认**
5. 拿 `ilink_bot_id`/`bot_token` → 写 `.env` + 账号文件
6. `hermes send --to weixin` 验证
7. 让用户 `/restart` 让 gateway 生效
