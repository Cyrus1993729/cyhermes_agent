# X Auth Token 提取指南（中文 Chrome）

## 场景
当 serenity-search 报 CSRF 错误或 token 过期时，用户需要重新从浏览器复制 `auth_token` 和 `ct0`。

## 步骤

### 1. 打开开发者工具
三选一：
- 右键网页任意位置 → 「检查」
- Chrome 右上角 `⋮` → 更多工具 → 开发者工具
- `Ctrl + Shift + I`

### 2. 找到 Application 面板
如果顶部标签栏没看到「应用」：
- 点最右边的 `>>` 展开更多标签
- 找到「应用」（英文版是 Application）

### 3. 定位 Cookies
左侧树形菜单：
```
应用 → 存储 → Cookies → https://x.com
```

### 4. 复制两个值
在右侧 Cookie 表格中找：
- `auth_token` — 双击 Value 列复制
- `ct0` — 双击 Value 列复制

### 5. 粘贴到配置文件
打开 `C:\Users\Administrator\serenity_config\token.txt`
替换对应的值，保留引号。

## 注意事项
- Token 不同设备登录会变化
- 重新登录会产生新 token
- 别人登录同账号可能使旧 token 失效
- 自然过期通常数月
