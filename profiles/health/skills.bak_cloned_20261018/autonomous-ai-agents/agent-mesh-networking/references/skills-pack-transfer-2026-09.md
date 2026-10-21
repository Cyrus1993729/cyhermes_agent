# 技能包批量分享 runbook（HTTP zip，2026-09-02 牛来→妈妈 11 skill 实测）

场景：把本机沉淀的多个 skill（+ 依赖 scripts）批量装到对端 Hermes agent。文本类配置（memory/用户画像）见 `share-to-peer-2026-09.md`；**数百 KB 的 skill 包用 HTTP 传输**。

## 步骤 0：数据驱动筛选（用户标准：常用的才分享，不用的不分享）

从会话库统计每个 skill 的真实调用次数（skill_view 出现频率），不凭印象：

```python
import sqlite3, json, collections
con = sqlite3.connect(r'C:/Users/<你>/AppData/Local/hermes/state.db')
rows = con.execute("SELECT tool_calls FROM messages WHERE tool_calls IS NOT NULL").fetchall()
hits = collections.Counter()
for (tc,) in rows:
    if not tc: continue
    try: data = json.loads(tc) if isinstance(tc, str) else tc
    except Exception: continue
    if isinstance(data, dict): data = [data]
    for call in data:
        f = call.get('function', {}) if isinstance(call, dict) else {}
        if f.get('name') == 'skill_view':
            try: a = json.loads(f.get('arguments','[]'))
            except Exception: a = {}
            hits[a.get('name','?')] += 1
for n,c in hits.most_common(30): print(c, n)
```

- 高频+通用 → ✅ 分享；本机实例绑定（trendradar、gold-investment-analysis cron）→ ❌；低频/0 调用 → ❌
- 分享前对候选 pack 做**敏感扫描**：`sk-…`、`Bearer …`、`AIza…`、`ghp_…`、`AKIA…`、PRIVATE KEY——0 命中才算干净

## 步骤 1：打包（zip 顶层 = skills/ + scripts/）

```python
import os, zipfile
hermes = os.path.expanduser("~/AppData/Local/hermes")
skills_root, scripts_dir = hermes+"/skills", hermes+"/scripts"
share = [("分类", "skill名"), ...]   # 相对 skills_root 的目录

dep_scripts = ["qwen_review.py","workflow_check.py","mem_gc.py","review_trend.py","whisper_chunk.py", ...]
zip_path = hermes + "/skills_share/skills_pack.zip"
with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
    for cat,name in share:
        d = os.path.join(skills_root,cat,name)
        if not os.path.isdir(d): d = os.path.join(skills_root,name)
        for root,dirs,fs in os.walk(d):
            dirs[:] = [x for x in dirs if x!="__pycache__"]
            for f in fs:
                if f.endswith((".pyc",".bak")): continue
                z.write(os.path.join(root,f), "skills/"+os.path.relpath(os.path.join(root,f),skills_root))
    for s in dep_scripts:
        p = os.path.join(scripts_dir,s)
        if os.path.exists(p): z.write(p, "scripts/"+s)
```

依赖脚本发现法：grep skills 目录内所有 .md 里 `scripts[\\/]([a-z_0-9]+\.py)` 的引用，缺的补进 dep_scripts（已在 skill 自带 scripts/ 下的不用）。

## 步骤 2：HTTP 服务 + 防火墙

- 起服务（background=true，静默 daemon）：`python -m http.server 8765 --bind 0.0.0.0`（在 skills_share 目录）
- 探活：`curl -s --noproxy '*' http://127.0.0.1:8765/skills_pack.zip` → 200
- 防火墙（UAC 提权姿势同 A2A 9900，见 SKILL.md）：bat 先 `netsh advfirewall firewall delete rule name="<名>"` 再 add TCP localport=8765，跑 `powershell -Command "Start-Process -FilePath '<bat>' -Verb RunAs -Wait"`，回读日志确认

## 步骤 3：A2A 指令（message/send，模板见 share-to-peer-2026-09.md）

指令三大步 + 注意事项 + 回复要求：

1. **下载**：`curl -s --noproxy '*' -o C:/Users/<对端用户名>/AppData/Local/hermes/skills_pack.zip http://<本机LAN-IP>:8765/skills_pack.zip`，然后 `ls -la` 确认大小非 0（否则贴回 curl 报错，勿继续）
2. **解压**：`python -c "import zipfile,os; base='C:/Users/<对端用户名>/AppData/Local/hermes'; zipfile.ZipFile(base+'/skills_pack.zip').extractall(base); print('extracted')"`（zip 顶层 skills/ scripts/ 自动合并）→ 再 ls skills/ 确认分类目录
3. **删 zip**：`rm .../skills_pack.zip`
4. 注意事项：技能内 C:\\Users\\Administrator\... 路径与 127.0.0.1:7897 端口均为示例，按对端实际 %LOCALAPPDATA% 和代理端口调整
5. 回复要求：zip 大小、解压后分类目录列表、zip 是否已删；curl 报错贴原文

## 坑（2026-09-02 实测，两次才成功）

1. ⚠️ **`%LOCALAPPDATA%` 在 MSYS bash 不展开**——第一次指令用 %VAR% 语法，对端 curl 下载到字面量 `%LOCALAPPDATA%/...` 文件，`ls` 找不到 zip、以为发错机器。**必须写对端绝对路径或 $VAR**。这是本类任务最大坑。
2. **对端用户名≠本机用户名**：本机 Administrator，妈妈机是 `C:/Users/1`。不要假设；从对端报错（「没找到」「路径错」）里读取它的真实 home 再重发。
3. **A2A 300s 超时 ≠ 失败**：对端执行中 HTTP 连接超时，任务实际在跑；用轻量查询消息（「简短回复：zip 在不在/解压完成没」）确认状态，**别重发指令**（重发会重复下载/重复解压）。
4. 验证要 `skills_list` 列名（能列出即加载成功），不只查目录存在——目录在而 skill 未注册的情况可能存在。
5. 收尾：删临时 token 文件与 .py 脚本（明文凭证/脚本不留盘）；HTTP 服务与防火墙规则留到用户确认分享结束后再撤。

## 通用项目目录传输（非 skill 包，2026-09-02 牛来→妈妈 实测 ✅）

同一 HTTP zip 通道可传**任意项目目录**（serenity_search/、gold_analyzer/ 等），zip 顶层直接放原目录名，对端解压到 home 即用——无需 skills/ 布局。

### 凭据铁律（本会话核心约定）

- **凭据文件不进包**：`token.txt`、`.env`（API key）等一律排除，沿用 9/2 约定「A2A 不传凭据，对端用户手动拷贝」。
- zip 内写一个 `凭据文件手动拷贝说明.txt`，列出被排除文件的**对端路径 + 格式**（如 `C:/Users/1/serenity_config/token.txt` 单行 X auth token；`.env` 为 `FRED_API_KEY=xxxx`）。
- 打包后用 `assert` 验证凭据不在 namelist：`assert "gold_analyzer/.env" not in names and "serenity_config/token.txt" not in names`。

### Python zipfile 反斜杠坑（首轮误打包实踩）

Windows 下 `os.path.relpath()` 返回反斜杠路径（如 `gold_analyzer\.env`），`rel.endswith("/.env")` 匹配不到 → 凭据**被误打进 zip**。修复：先归一化再匹配：`rel = rel.replace("\\", "/")`，排除条件写 `rel.endswith("token.txt")` / `"gold_analyzer/.env" in rel`。写完任何排除逻辑都要断言验证。

### 复用既有 HTTP 服务（不必重启）

- 上次分享的 `python -m http.server 8765` 可能还在跑：`netstat -ano | grep 8765` 确认 LISTENING 后直接复用端口，新 zip 丢进同一 skills_share 目录即可，防火墙已放行无需重开。
- **探活勿用 `curl -o /dev/null`**（MSYS bash 下原生 curl 不认 /dev/null，报 exit 23）——用 `curl -sI` HEAD 验证：返回 200 + `Content-Length` 与本地 zip 字节数一致即链路通（`curl -sI --noproxy '*' http://127.0.0.1:8765/<zip>`）。
