# 跨机分享配置 runbook（2026-09-02 牛来→妈妈 实测）

## 场景

把本机沉淀的 skill / memory / 用户规范分享给对端 Hermes agent。本会话分享内容：用户画像 5 条（target=user）+ 通用铁律 6 条（target=memory），63.6s 往返完成，双方确认落盘。

## 前置探测

1. 对端 Agent Card 确认身份与可达：`curl --noproxy '*' http://<对端IP>:9900/.well-known/agent-card.json` 返回 JSON，`name` 字段 = 权威身份（中文名完全可用）。
2. 本机 token 取法（**从 config.yaml 读，绝不硬编码**）：

```python
import yaml
c = yaml.safe_load(open('config.yaml', encoding='utf-8'))
open('a2a_token_tmp.txt','w').write(c['a2a_agents']['<对端名>']['auth']['token'])
```

3. ⚠️ /tmp 坑：MSYS 下原生 python 不认 `/tmp`（FileNotFoundError）——临时文件放 `$LOCALAPPDATA/hermes/` 下，用完 `rm -f`。

## 投递脚本模板（message/send 直连）

```python
# -*- coding: utf-8 -*-
import json, time, urllib.request

token = open("a2a_token_tmp.txt").read().strip()
base = "http://<对端IP>:9900"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "A2A-Version": "1.0"}

instruction = """<对端名>，以下是主人正式配置，请写入你的持久存储：
== 第一部分：写入 USER profile（memory 工具，target=user），内容如下 ==
……（5 条）
== 第二部分：写入 MEMORY（target=memory），内容如下 ==
……（6 条）
执行要求：
1. 先用 memory 工具查看当前 USER/MEMORY 现状，避免重复覆盖；
2. 每条内容保持完整，可合并精简但不丢关键信息；
3. 完成后简短回复：写了几条、存到哪个 target、当前字符数。不要复述全部内容。"""

body = json.dumps({"jsonrpc": "2.0", "id": int(time.time()*1000), "method": "message/send",
    "params": {"message": {"role": "user", "parts": [{"text": instruction}],
    "metadata": {"taskId": f"share-{int(time.time())}"}}}}).encode("utf-8")

req = urllib.request.Request(base + "/", data=body, method="POST", headers=headers)
with urllib.request.urlopen(req, timeout=300) as r:
    resp = json.loads(r.read().decode("utf-8"))
st = resp["result"]["status"]
parts = st.get("message", {}).get("parts", [])
print("state:", st.get("state"))
print("reply:", parts[0]["text"][:1000] if parts else "")
```

## 分享内容分类检查表（分享前逐项过）

| 类别 | ✅ 直传 | ⚠️ 参数化/改造 | ❌ 不分享 |
|---|---|---|---|
| 方法论/流程 skill（sprint-contract、task-wrapup、decision-gate、docx/xlsx/pdf 等） | 通用直接传 | — | — |
| 含本机路径的 skill | — | 删 C:/Users、D:\Workspace、API key 目录引用 | 实例绑定太深的（trendradar、gold-investment-analysis cron 系统） |
| 含凭据的 skill | — | 删私有仓库名、token；grep 探测：`sk-…` `Bearer …` `token*=*"…"` | 无法脱敏的原样传 |
| 依赖对端环境的 skill（claude-code/codex CLI、l1-review 网关） | — | 仅当对端装了对应 CLI | 环境不存在就别传 |
| 网络经验 | 与出口 IP 相关的事实（X 走代理/Google CAPTCHA/Bing 直连） | 端口改成「以本机实际监听为准」+自查命令 | 本机参数值（127.0.0.1:7897） |
| 用户画像 | 个人背景+行为规范（⚠️规范类比背景更关键，防行为割裂） | 修剪 provider/验证管线条目（留 skill 环节） | 一次性决策记录、私有仓库名 |

## 验证

- 对端回复必须含：条数 + target + 当前字符数（如「USER 5 条，834/1375；MEMORY 6 条新增，1559/2200，原 4 条环境条目未动」）——数字对得上才算落盘。
- 回复时间 60s+ 属正常（对端是完整 agent 要思考+写 memory），别当超时放弃。
- 投递后立即清理临时 token 文件（明文凭证不留盘）。

## 会话内 a2a 工具 vs 底层 JSON-RPC

- 会话内工具（a2a_call/a2a_list/a2a_discover 等 🧩）由插件注册，**门控条件下才加载**（a2a_agents 有配置 OR A2A_PORT 环境变量 OR platforms.a2a.enabled）。
- 实测 tool_search/tool_describe 可能返回「not currently available」——此时**不要卡住，直接走 JSON-RPC 直连**（上面的脚本），message/send 等效 a2a_call。
