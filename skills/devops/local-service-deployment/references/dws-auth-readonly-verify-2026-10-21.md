# 第三方 CLI 授权后的只读验收（dws / Dayflow client，2026-10-21 实测）

触发：用户扫码/设备授权完成，说「显示授权成功，你试试」。**别只看 `authenticated: true` 就报成功——要真读一次日历和邮件，把「可读」证明出来。**

---

## 一、dws（钉钉官方 CLI）验收序列

```bash
DWS=C:/<root>/tools/dws/dws.exe

$DWS auth status      # 布尔 + 到期时间；不打印 token
$DWS doctor           # 五项体检
$DWS calendar +book-list      # 日历本列表
$DWS calendar +agenda         # 今天日程（不传时间默认今天）
$DWS mail +recent-mail        # 最近邮件
$DWS mail +unread-mail        # 未读
```

`auth status` 回执字段（拿来做回执，不含凭据）：
```json
{"success":true,"authenticated":true,"token_valid":true,"refresh_token_valid":true,
 "expires_at":"...","refresh_expires_at":"...","corp_name":"...","user_name":"..."}
```

`doctor` 五项 = 登录状态 / 钥匙串 / runtime context / 网络连通性 / 版本更新。**授权成功后应为 `4 pass · 1 warn · 0 fail`**（剩的那条 warn 通常是「有新版本」）。

### 坑

- 🔴 **`doctor` 第一次跑报 `Runtime context unavailable` 不是装坏**：紧接着的第二次就 `✅ Runtime context ready`——首跑在预热运行时。**别据此重装或去翻 runtime payload。**
- **`count: 0` 要结合 `ok: true` 判读**：`calendar +agenda` 返回 `{"ok":true,"data":{"count":0,"events":[]}}` = 今天真的没日程，不是读失败。反之 `ok:false` 才是故障。
- **版本锁定别顺手升级**：`doctor` 提示 `有新版本 (当前 v1.0.63, 最新 v1.0.65)`，若协调端指定固定版本就**不跑 `dws upgrade`**，并把这条 warn 如实报到回执里。
- **`+` 前缀是内置快捷命令**（`+agenda`/`+book-list`/`+recent-mail`/`+unread-mail`），与 `calendar event list` 这类原生命令并列存在；快捷命令已经做过投影和自动解析，优先用它们。

### 脱敏口径（对外/对 A2A peer 回执时）

只报：**可读布尔 + 数量**（日历本 N 个 / 今日 N 条 / 最近 N 封 / 未读 N 封 / doctor X pass）。
**不报**：邮箱地址、组织 ID、userId、token、邮件主题全文（除非用户本人要看）。

---

## 二、Dayflow `client items` 的返回形状

🔴 **`client items` 返回的是裸 JSON 数组**，不是 `{"items": [...]}`：

```python
# 会炸：AttributeError: 'list' object has no attribute 'get'
items = d.get('items', [])

# 正确
items = d if isinstance(d, list) else d.get('items', [])
```

对照：

| 命令 | 返回 |
|---|---|
| `client items` | **裸数组** `[ {item…}, … ]` |
| `client state` | 对象 `{items, goals, reviews, drafts, settings, sync, availability, revision}` |

查某一天：拉全量后本地按 `date == 'YYYY-MM-DD'` 过滤，并**排除 `status:'cancelled'`**（取消项仍在数组里，不排会虚报）。

今天日期一律取 `date '+%Y-%m-%d'`（北京时间），不要用会话上下文里的日期推断。
