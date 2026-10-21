# 备份推送失败的双重根因：代理配错 + GitHub 密钥扫描拦截

> 2026-10-21 牛来端实战。备份 cron 连挂 5 天（`last_status: error`, `failure_streak: 5`），
> 报错停在 `Failed to connect to github.com port 443 via 127.0.0.1`。
> 修好代理后才发现真正的拦路虎是第二个：GitHub push protection。

## 症状与误判陷阱

cron 里看到的错误：

```
BACKUP FAILED: git push error
fatal: unable to access 'https://github.com/<owner>/<repo>.git/':
Failed to connect to github.com port 443 via 127.0.0.1 after 10011 ms
```

这个报错**只说明代理连不上**，会让人以为「修好代理就完事」。
实际上代理修好后 push 仍然失败，只是错误换了一套说辞。**两个故障串联时，第二个被第一个挡住了。**

## 根因一：git 代理指向一个没在监听的端口

现场：

```
git config --global --get-regexp proxy
# http.proxy  http://127.0.0.1:7897     ← Clash 默认端口，本机根本没装/没开
# https.proxy http://127.0.0.1:7897

netstat -ano | grep 7897        # 无输出 = 没有监听
netstat -ano | grep LISTENING | grep -E ":1080[0-9]|:789[0-9]"
# TCP 127.0.0.1:10808  LISTENING   ← 真正在跑的代理（v2rayN）
```

**教训：报错里的 `127.0.0.1` 不带端口号，别信它是「代理不通」，先查那个端口到底有没有监听。**
从 7897（Clash 惯例）换到别的客户端后，git 全局配置不会自动跟着改。

修复：

```bash
git config --global http.proxy  http://127.0.0.1:<真实端口>
git config --global https.proxy http://127.0.0.1:<真实端口>
git -C <repo> ls-remote --heads origin    # 不推数据，只用它验连通+认证
git -C <repo> ls-remote --heads origin 2>&1 | head -1   # 出 commit 行即通
```

对照验证（排除「是线路问题还是端口问题」）：

```bash
curl -sS -o /dev/null -w "code=%{http_code}\n" --noproxy '*' --max-time 12 https://github.com   # 直连：超时
curl -sS -o /dev/null -w "code=%{http_code}\n" -x http://127.0.0.1:10808 https://github.com     # 走代理：200
```

## 根因二：GitHub push protection（密钥扫描）拦截整个推送

代理修好后的新报错：

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: Push cannot contain secrets
remote:  —— DeepSeek API Key ——
remote:    locations:
remote:      - commit: <sha>
remote:        path: profiles/health/.env:3
remote: To push, remove secret from commit(s) or follow this URL to allow the secret.
remote:         https://github.com/<owner>/<repo>/security/secret-scanning/unblock-secret/...
 ! [remote rejected] main -> main (push declined due to repository rule violations)
```

关键点：**它拦的是「推送里包含的历史提交」，不是「当前工作区文件」。**
所以光把文件从工作区删掉 / 加进 .gitignore 都没用——那个 commit 还在待推的提交链里，照样拦。

### 诊断三连

```bash
# 1) 哪些敏感文件还在被 git 跟踪
git -C <repo> ls-files | grep -iE '\.env|auth\.json|token|secret|api[_-]?key|credential|\.pem$'

# 2) 这些文件出现在哪些提交里
git -C <repo> log --oneline --all -- profiles/health/.env

# 3) 泄露提交是否已经推到远程（决定要不要轮换密钥）
git -C <repo> merge-base --is-ancestor <sha> origin/main \
  && echo "已在远程=真实泄露，必须轮换 key" \
  || echo "只在本地，未泄露"

# 4) 某个文件在远程里到底有没有秘密（不打印值，只数命中）
git -C <repo> show origin/main:config.yaml | grep -c "sk-"
```

### 修复：reset --soft 重建单个干净提交（比重写历史安全得多）

待推的是若干条机器生成的 `auto backup` 提交时，**不值得为了干净历史去跑**
`git filter-branch` / `filter-repo`（慢、易错、Windows 上更坑）。直接把本地回退到
远程最新点，用当前文件树重新提交一次：

```bash
# 0) 先留后路
cd ~/AppData/Local/hermes
git branch backup-before-fix $(git rev-parse HEAD)

# 1) HEAD 回到远程最新，index 与工作区都不动（--soft）
git reset --soft origin/main

# 2) 把凭证文件从索引里摘掉（工作区文件保留，Hermes 照常能用）
git rm --cached profiles/health/.env profiles/health/auth.json

# 3) 按新 .gitignore 重新索引
git add -A

# 4) 提交前自检：暂存区里不许再有凭证类文件（应为空）
git diff --cached --name-only | grep -iE '\.env|auth\.json|\.pem$|\.key$|connection\.json'

# 5) 提交并推送
git commit -m "auto backup"
git push origin main
```

本次实测输出：`c8ad9a7..d449b63  main -> main`，`git ls-remote` 回读一致。

> 代价：丢失若干条 `auto backup` 中间提交。机器自动提交没有审阅价值，值得。
> 如果待推提交里有**需要保留的真实开发历史**，改用 filter-repo，别机械套这段。

### 别用 GitHub 给的 unblock 链接放行

报错里那个 `unblock-secret` URL 能一键放行。**不要点**——那等于主动把密钥永久写进仓库历史。
正确顺序永远是：把密钥从提交里拿掉 → 需要时轮换密钥。

## 比拦截更糟的情况：悄悄进仓库的密钥

本次最大发现不是被拦的那个，而是**没被拦的那个**：

```
git -C <repo> show origin/main:config.yaml | grep -c "sk-"   # → 3
grep -c "sk-" ~/AppData/Local/hermes/config.yaml             # → 1
```

`config.yaml` 在白名单里被放行，里面 `api_key:` 是明文真钥匙（OpenCode Go 的 `oc_sk_...`、
DeepSeek 的 `sk-...`）。**它们已经在远程仓库的历史提交里存在很久了**，GitHub 也没拦——
原因是被拦的那把 key 格式被识别得更严格，不代表 config.yaml 安全。

**结论：`config.yaml` 进备份 = 密钥进备份。** 白名单放行 config.yaml 时，必须同时处理里面的 api_key。

两条路，二选一：

1. **备份前脱敏**（推荐，保留配置结构）：commit 前把 `api_key:\s*\S+` 的值替换成 `"***"` 写进
   索引/副本，原文件不动。注意 `git add` 之后、`git commit` 之前替换，且不能改工作区里的真文件，
   否则 Hermes 立刻连不上模型。
2. **config.yaml 不进备份**：从白名单删掉 `!config.yaml`，另外维护一份脱敏的
   `config.example.yaml` 给人看结构。

**密钥一旦确认到了远程，纯清理历史不够——必须轮换密钥。** 轮换之后历史里的旧值自动失效，
历史是否干净就不再重要了。这件事只能用户本人在对应平台操作，Agent 不要代做。

## 预防清单（白名单 .gitignore 的正确结尾）

白名单策略的漏洞在于：`!profiles/**` 会把 `profiles/health/.env` 一起放行。
**放行规则之后，必须补一段凭证排除**（gitignore 后写的规则优先）：

```gitignore
# === 凭证类绝不入库（放在所有放行规则之后，优先级最高）===
.env
.env.*
**/.env
**/.env.*
**/auth.json
**/*.pem
**/*.key
**/hermes-cloud-connection.json
**/.local/
profiles/**/.env
profiles/**/auth.json
```

自检（建议加进备份脚本的提交前钩子）：

```bash
git diff --cached --name-only | grep -iE '\.env|auth\.json|\.pem$|\.key$' && \
  echo "!!! 拒绝提交：暂存区含凭证文件" && exit 1
```

## 附：本次一并纠正的一个错误认知

旧版 `hermes-backup` 写着「`no_agent` cron 的 script 路径相对于 `~/.hermes/scripts/`，
不是 `~/AppData/Local/hermes/scripts/`」。**错的。**
`cronjob_manage` 的 `script` 相对路径解析到 `~/AppData/Local/hermes/scripts/`，
且**支持子目录**：本次用 `script: dayflow/df_morning.py` 直接跑通，无需复制到别处。
