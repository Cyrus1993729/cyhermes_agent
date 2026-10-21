# OpenCode API key 过期 + .env 热重载（2026-10-18 实锤）

## 症状（用户视角）

「OpenCode 一直在报错」「测试一下是否可以对话」——用户连续几条消息都在确认服务是否活着。
**用户明确说「我的 OpenCode 账号肯定是没有欠费的」——他是对的，你如果先猜余额会浪费一两轮。**

## 错误链原文（每次请求连刷三条）

```
# 第 1 条 · 主链路 opencode-go / deepseek-v4.1-flash
HTTP 401 {'error':{'type':'authentication_error','code':'api_key_expired',
'message':'This API key has expired. Create a new API key in OpenCode Console 
and replace it in your client or secret store. Signing in again will not renew this key.'}}

# 第 2 条 · 兜底1 fallback_providers[0] → deepseek 官方 / deepseek-flash
HTTP 402 Insufficient Balance (request_id: 78a4705c-...)

# 第 3 条 · 兜底2 fallback_model → opencode-go-anthropic / qwen3.7-max
HTTP 401 ... api_key_expired          ← 同一个 key、同一个网关，必然一起挂

→ agent.conversation_loop: Non-retryable client error → 任务失败
```

对应 cron 记录：`Job 'TrendRadar五类日报' failed: RuntimeError: HTTP 401: This API key has expired...`，`last_status: error`。

## 判别：401 还是 402，一次 curl 说清

| 返回 | 含义 |
|:--|:--|
| `401 api_key_expired` | **key 本身过期**，只能去 Console 新建（重新登录不续期） |
| `401 authentication_error` 其它 code | key 用错平台/格式 |
| `402 Insufficient Balance` | 账号余额不足（DeepSeek 官方侧常见） |
| `400 MissingSessionID` | 缺 `x-opencode-session` 头 |
| `403` | 缺 `User-Agent: curl/8.0.0`（Cloudflare） |

复现命令（两个都打，两个都 401 才算实锤）：

```python
import subprocess, json
H = ['-H','Authorization: Bearer '+KEY, '-H','User-Agent: curl/8.0.0',
     '-H','x-opencode-session: hermes-diag-1']
# 1) 目录
curl -s -o - -w '\n__HTTP__%{http_code}' --max-time 40 -x http://127.0.0.1:10808 \
     {H} https://opencode.ai/zen/go/v1/models
# 2) 真实 chat
#    POST /zen/go/v1/chat/completions
#    {"model":"deepseek-v4.1-flash","messages":[{"role":"user","content":"回复OK"}],"max_tokens":10}
```

## 🔴 核心结论：换 .env 里的 key **不需要重启 gateway**

这一条推翻了旧做法（杀 PID + schtasks /run），是本会话最有价值的发现。

**源码依据** `cron/scheduler.py` → `run_job()`（约 :5865-5876，no_agent 分支）与 :6233-6251（agent 分支）：

```python
# Re-read .env and config.yaml fresh every run so provider/key
# changes take effect without a gateway restart.
from hermes_cli.env_loader import load_hermes_dotenv, reset_secret_source_cache
reset_secret_source_cache()
load_hermes_dotenv(hermes_home=_get_hermes_home())
```

`load_dotenv(override=True)` 会覆盖**整个进程**的 `os.environ`。所以：

- **任何一次 cron tick（含每 30 分钟的 no_agent 看门狗脚本）都会自动把新 key 加载进 gateway 进程**
- 想立刻生效：`cronjob(action="run", job_id=<任意 job>)` 手动触发一次即可

### 三层生效时机（别混）

| 改什么 | 生效方式 |
|:--|:--|
| `config.yaml`（含 custom_providers 内联 api_key） | mtime 缓存热加载（`hermes_cli/config.py:3883`），新会话即生效 |
| `.env`（如 `OPENCODE_GO_API_KEY`） | **下一次 cron tick 自动重载**，或手动 run 一个 job |
| provider/base_url 结构性变更、新装依赖 | 仍需重启 gateway |

### 验证脚本（改完之后必跑）

```python
import psutil, datetime
new = open(r'C:\Users\Administrator\Desktop\各类api key\opencode key新.txt', encoding='utf-8').read().strip()
for p in psutil.process_iter(['pid','name','cmdline']):
    cl = ' '.join(p.info['cmdline'] or [])
    if 'hermes_cli.main' not in cl: continue
    v = p.environ().get('OPENCODE_GO_API_KEY')
    st = '新KEY ✓' if v == new else ('旧KEY ✗' if v else '未设置')
    print(p.info['pid'], st, cl[cl.find('hermes_cli.main'):][:45])
```

实际观察：`gateway run` 进程（PID 9852）在一次手动 cron run 后立刻变成「新KEY ✓」；
`serve` 进程（PID 4044，desktop spawn 的第二个调度器）仍是旧 key，但它下一次 tick 也会自愈——**这不影响结论，只是记忆里「双调度器残留」现象的又一例证**。

## 换 key 的完整操作（只需 2 处）

```python
# 1. 备份
shutil.copy2('.env', f'.env.bak_{ts}'); shutil.copy2('config.yaml', f'config.yaml.bak_{ts}')
# 2. 纯文本替换旧 key → 新 key（不要 YAML round-trip，会毁注释/格式）
#    .env           : OPENCODE_GO_API_KEY            (1 处)
#    config.yaml    : opencode-go-anthropic 内联 api_key (2 处)
# 3. 校验
yaml.safe_load(open('config.yaml'))          # 必须仍是 dict
for f in ('.env','config.yaml'): assert old not in open(f).read()
```

### 🔴 换 key 必须改 **3 个来源**（本文件早前版本错误地写"其余脚本读环境变量自动跟随"——已纠正）

脚本取 key 分三类，**只改 `.env` 会让 8 个脚本里 5 个继续用旧 key**：

| 来源 | 谁在用 | 换 key 时 |
|:--|:--|:--|
| `.env` 的 `OPENCODE_GO_API_KEY` | Hermes 主链路（`opencode-go` provider 的内置 `env_vars`） | 必改 |
| `config.yaml` 的 `opencode-go-anthropic` **内联** `api_key` | Hermes 第 2 层兜底 + 3 个脚本（正则抓 `api_key:\s*(\S+)`） | 必改（2 处） |
| **桌面 key 文件**（硬编码路径，**不读环境变量**） | `api_healthcheck.py` / `api_probe.py` / `model-subscription-evaluation/scripts/model_probe.py` / `video-understand-core/scripts/{pipeline,quick_summary}.py` | 必改 |

硬编码路径共 5 处，全部指向同一文件：
`C:\Users\Administrator\Desktop\各类api key\opencode go api key.txt`

```bash
grep -rln "各类api key" --include=*.py scripts/ skills/   # 换 key 后跑一遍确认无遗漏
```

**踩过的坑**：用户把新 key 存成了**新文件**（`opencode key新.txt`）而旧文件留着，结果 `.env` 换完、主链路转绿，但健康检查脚本每 30 分钟**假报一次 401**（读的是旧文件）。→ 换 key 时**务必确认脚本读的那个文件也换了**，否则会误判"key 还没生效"。最省事的修法是把新 key **写进脚本共用的那个文件**（备份旧的即可），一个都不用改脚本。

### 端到端验证（别只看 curl 通）

```bash
timeout 220 hermes -z "只回复这五个字：新key已生效" < /dev/null
```
然后查 state.db：

```sql
SELECT session_id, model, billing_provider, billing_base_url, datetime(first_seen,'unixepoch','localtime')
FROM session_model_usage ORDER BY rowid DESC LIMIT 3;
```
本次实测得到 `('20261018_142404_b29898','deepseek-v4.1-flash','opencode-go','https://opencode.ai/zen/go/v1',...)` = 真的走了主链路，不是兜底。

## 附带事实

- **key 生命周期约 62 天**：旧 key 2026-08-16 存入，最后一次成功 10/17 20:41（跨境日报），10/18 08:00 已 401。**失效发生在夜里 → 早报静默失败**，建议加「每周一次 key 探针」cron（打 `/models`，非 200 即告警）。
- **key 格式 2026-10 变更**：旧 `sk-` 开头 67 位 → 新 `oc_sk_` 开头 51 位。别用长度/前缀去校验新旧。
- 🔴 **换 key 后当前会话仍粘在 fallback 上**（`agent._fallback_activated` sticky）→ 要 `/reset` 开新会话才回到主链路。本次当前会话被锁在 DeepSeek 官方（余额仅 ¥9.99）。
- 🔴 **兜底链结构性缺陷再确认**：`fallback_model` 第 2 层 `opencode-go-anthropic` 与主链路**同 key 同网关** → key 过期/网关挂的场景零保护。这类故障下唯一有效的是 `fallback_providers[0]`（DeepSeek 官方，独立 key）。
- DeepSeek 官方余额查询端点：`GET https://api.deepseek.com/user/balance`（返回 `is_available` + `balance_infos`）。本次 ¥9.99 仍可用——**`Insufficient Balance` 不是余额为 0 的必要条件**，余额极低时会间歇性 402，别据此判定账号没钱。
- 旧 key 文件（`Desktop/各类api key/opencode go api key.txt`）留着会成陷阱，按用户既有习惯改名 `... 已过期.txt`。
