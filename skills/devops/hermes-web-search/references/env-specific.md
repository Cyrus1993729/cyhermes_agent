# 本项目实际网络测试结果

测试日期：2026-07-14
代理地址：127.0.0.1:7897

## 搜索引擎可达性实测

```
Bing直连:        302 1.17s  ✅
Google代理:      302 2.69s  ✅ (有CAPTCHA风险)
DuckDuckGo代理:  200 2.90s  ✅
DDG Lite代理:    202 1.29s  ✅ (最干净的HTML)
Bing代理:        已测试     ✅
Baidu直连:       未测试     (中文可用)
Startpage代理:   已测试     ✅ (偏慢)
Google直连:      超时       ❌
DuckDuckGo直连:  未测试     (大概率超时)
Startpage直连:   空返回     ❌
```

## Tavily 配置信息

- **API key 位置**：`C:\Users\Administrator\Desktop\各类api key\Tavily API key.txt`
- **Key 前缀**：`tvly-dev-`
- **安装版本**：tavily-python 0.7.26
- **Python 环境**：`AppData\Local\hermes\hermes-agent\venv` (Python 3.11.15)
- **包管理器**：uv（pip 不在 PATH）
- **直连测试**：`api.tavily.com` 直连可达，无需代理

## Hermes 配置命令

```bash
# 查看当前后端
hermes config get web.search_backend
hermes config get web.backend

# 设置 Tavily
hermes config set web.search_backend tavily
hermes config set web.backend tavily

# 清空（禁用搜索）
hermes config set web.search_backend ''
hermes config set web.backend ''
```

## Bing 直连后备方案命令模板

```bash
curl -sL --max-time 10 --noproxy '*' \
  "https://www.bing.com/search?q=<URL_ENCODED_QUERY>" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  | sed 's/<[^>]*>//g' | grep -iE "<KEYWORD>" | head -50
```

## 注意事项

1. 本项目使用 git-bash (MSYS)，不是 PowerShell
2. `.env` 和 `config.yaml` 受 Hermes 保护，不能直接用文件工具读写
3. `.env` 用 terminal + python 脚本读写
4. `config.yaml` 用 `hermes config set/get` 操作
5. 配置变更后必须 `hermes gateway restart` 才能生效
