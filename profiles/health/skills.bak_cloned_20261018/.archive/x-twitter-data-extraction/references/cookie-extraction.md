# 从浏览器提取 X/Twitter 认证 Cookie

## Chrome / Edge（中文 UI）

1. 用你的 X bot 账号登录 https://x.com
2. F12 打开开发者工具
3. 点击「应用」（Application）标签
4. 左侧：存储（Storage）→ Cookies → `https://x.com`
5. 在右侧列表中找到并复制：

| Cookie 名 | 说明 | 格式 |
|-----------|------|------|
| `auth_token` | 主认证 token | 32 位十六进制，如 `abc123def456...` |
| `ct0` | CSRF 防护 token | 长十六进制字符串 |

## Chrome / Edge（英文 UI）

1. Login to x.com with bot account
2. F12 → Application → Storage → Cookies → `https://x.com`
3. Copy `auth_token` and `ct0`

## 保存方式

保存到本地配置文件（不要明文发到聊天）：
```
AUTH_TOKEN="你的auth_token值"
CT0_TOKEN="你的ct0值"
```

## 失效处理

- auth_token 通常数月有效
- 改密码、异地登录、手动登出会使旧 token 失效
- 失效时报错通常含 "This request requires a matching csrf cookie and header"
- 重新按上述步骤提取即可

## 注意事项

- `x-csrf-token` 请求头必须和 cookie 里的 `ct0` 值完全一致
- 不同设备的 token 不同，不能混用
- 建议专门注册一个 bot 账号用于数据采集，不要用主号
