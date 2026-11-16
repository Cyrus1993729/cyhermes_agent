---
name: codex-cli
description: 经 codex exec 调 GPT-5.6 做审查/方案/看图处理图片时使用(用户指定"让GPT-5.6处理X"=走codex非API)。含Windows调用姿势、-i图片输入、sandbox档位、JSON提取。
version: 1.0.0
category: autonomous-ai-agents
tags: [codex, cli, gpt-5.6, review, windows]
---

# Codex CLI 调用（GPT-5.6 非交互）

## 触发
- 需要用 GPT-5.6（Codex 背后模型）做审查/独立方案/双审对比（对应 claude-code skill 的定位）
- 用户说"走 Codex / GPT 审查"或脚本需要调 codex
- 维护调用 codex 的脚本（如 daily_report_review.py）
- ⚠️ **2026-09-01 起为本机深度审查/分析/sign-off 的默认执行通道**（原 Opus/claude-code-workflow 因账户冻结停用）。深度任务统一用 `-c 'model="gpt-5.6-sol"'` 指定 GPT-5.6 Sol（Plus 配额模型，实测可用）；普通任务用默认模型即可
- 🔥 **2026-10-17 起新增更强模型 `gpt-6-astra`**（需 codex-cli ≥0.163.0，本机已升级）：用于**批判性审查/归因复盘**类任务，实测会主动抓你的数据错误并逐条给【事实】/【判断】标注。调用姿势与 sol 相同：`-c 'model="gpt-6-astra"'`。用户说"问gpt6astra"= 走这个模型

## 环境事实
- 安装：`~/.local/bin/codex` 是 **bash 脚本**；同目录 `codex.cmd` 是 Windows 包装器（内部 `powershell Get-ChildItem $env:LOCALAPPDATA\OpenAI\Codex\bin\*\codex.exe | Sort LastWriteTime | Select -First 1` 定位最新 codex.exe）
- 版本实测：**codex-cli 0.163.0**（2026-10-17 由 0.146.0-alpha.9.2 手工升级；见下"手工升级"节）
- 可选模型（`~/.codex/models_cache.json` 的 `models[].slug`，**2026-11-05 实测全量**）：`gpt-6.1-sol`、`gpt-6.1-terra`、`gpt-6-astra`、`gpt-6-sol`、`gpt-6-luna`、`gpt-5.6-sol`（config 默认）、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-reserve`、`codex-auto-review`
- 🔥 **2026-11-05 起 `gpt-6.1-sol` 可用（当前最强 sol 线）**：用户说「gpt6.1sol high」「用 6.1 sol 跑」= 走这个。**模型名 + 推理档位是两个独立 `-c`**：
  ```bash
  codex.cmd exec --skip-git-repo-check --sandbox read-only \
    -c 'model="gpt-6.1-sol"' -c 'model_reasoning_effort="high"'
  ```
  实测（2026-11-05，系统评估类长分析）：high 档 ~4 分钟 / 68K tokens / exit 0。用户只给模型名没给档位时，深度分析默认加 `high`。
- ⚠️ **模型 slug 会变**：用户报的模型名先核对 `models_cache.json` 里是否存在，别照着旧记录硬调；不存在就如实说「本机没有这个 slug，现有是 …」让他选，不要静默降级到别的型号。
- 必须走代理（OpenAI 被墙）：`HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:10808`（10808 = v2rayN 主线路；7897/Clash 已退休作废，别再写进脚本）

## 手工升级 Codex CLI（2026-10-17 实测；`codex update` 在本机不可用）
🔴 `codex update` 会报 `Error: Could not detect the Codex installation method. Please update manually` —— 本机安装方式它认不出来，**别浪费时间试自动升级**。

本机安装布局（关键）：`%LOCALAPPDATA%\OpenAI\Codex\bin\<16位哈希>\`，每个哈希目录是一堆平铺的 exe；`codex.cmd` 靠 **LastWriteTime 最新** 的 `codex.exe` 决定用哪个版本（所以升级=放一个 mtime 更新的新目录，旧目录留着就是天然回滚点）。

升级步骤（实测跑通）：
1. 取新版二进制（**不动现有安装**，下到临时目录）：
   ```bash
   cd "$LOCALAPPDATA/Temp" && npm install --no-save @openai/codex@<版本>
   # 二进制落在 node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/
   #   bin/codex.exe, bin/codex-code-mode-host.exe,
   #   codex-path/rg.exe, codex-resources/{codex-command-runner,codex-windows-sandbox-setup}.exe, codex-resources/voice/
   ```
   （也可先 `npx -y @openai/codex@<版本> --version` 快速验版本；npx 会装到 `$LOCALAPPDATA/Temp/node_modules`）
2. 把上述 exe **平铺**拷进新目录 `%LOCALAPPDATA%\OpenAI\Codex\bin\<新16位hex>\`（用 `shutil.copy2` 保留 mtime，保证比旧目录新）
3. 验证三件事，**缺一不可**：
   - `cmd.exe /c "C:\Users\Administrator\.local\bin\codex.cmd" --version` → 新版本号
   - 新老模型各一次冒烟：`printf '只输出 JSON: {"ok": true}' | <codex.cmd> exec --skip-git-repo-check --sandbox read-only [-c 'model="gpt-6-astra"']`
   - **跑真实下游管线**（本机是 `hermes/scripts/daily_report_review.py`）：`sys.path.insert` 后直接 `import daily_report_review as d; d.call_gpt('<假草稿>','')`，断言返回 dict 有 `findings` 键。冒烟通过 ≠ 管线通过，必须实测这一条
4. 回滚：删掉新建的哈希目录即可（旧版目录原封不动）

坑：
- `rg.exe` 新旧版本大小完全一致（4,218,880 bytes），可复用，但一并拷进新目录更保险
- 升级前后都别让 codex 进程在跑（改动 exe 时会被占用）

## 调用姿势（Windows subprocess，实测定型）
```python
env = dict(os.environ)
env["HTTP_PROXY"] = "http://127.0.0.1:10808"
env["HTTPS_PROXY"] = "http://127.0.0.1:10808"
prompt_file.write_text(prompt, encoding="utf-8")   # 长 prompt 走 stdin
r = subprocess.run(
    ["cmd.exe", "/c", r"C:\Users\Administrator\.local\bin\codex.cmd",
     "exec", "--skip-git-repo-check", "--sandbox", "read-only"],
    stdin=open(prompt_file, encoding="utf-8"),
    capture_output=True, text=True, timeout=600, env=env,
    cwd=r"D:\Workspace\Projects\TrendRadar")   # 任意已存在目录
```
🔴 关键坑（全部实测）：
1. **subprocess 直接调 `codex` → WinError 2**：bash 的 PATH（~/.local/bin）不在 Windows PATH，且无扩展名 bash 脚本 CreateProcess 不认。必须 `cmd.exe /c <绝对路径>/codex.cmd`
2. **必须 `--skip-git-repo-check`**：不在 git 仓库内运行会报 "Not inside a trusted directory and --skip-git-repo-check was not specified"
3. **长 prompt 不要作位置参数**：cmd.exe 命令行上限 8191 字符；prompt 写临时文件 + stdin 重定向（codex exec 无位置参数时从 stdin 读）
4. `--sandbox read-only`：审查类任务只读，够用且安全
5. 启动可能有无害 ERROR 日志（`codex_models_manager: failed to refresh available models: timeout`）不影响结果

## 🔴 评估「我这套系统 / 这个工具值不值得换」类任务（2026-11-05 定型）

用户发来一个开源项目/工具，问「对我们有什么用」时，走这条：

1. **先把事实喂满**：项目 README 原文 + 作者自述 + 已知限制 + **用户自己的系统现状**（不是他自己猜的现状，是你查到的）。用户画像写在 prompt 里，包括他的**行为约束**（拒绝持续手动记录、不接受复杂架构、要零操作、成本敏感）——只写需求不写约束，它给的方案他一定会否决。
2. **六要素之外再加两条**：⓪ 明写「**你可以否定提问方已有的判断**」并把我方初步结论列出来给它打；⑦ 明写「**用大白话，禁止堆术语，能用生活类比就用类比**」——用户点名要通俗解释时，这一条不写它就交学术腔。
3. **它会反过来纠正你**：本次它抓出我两处「只看任务名没看实现就下的判断」。凡是 prompt 里描述用户现有系统的地方，**先自己查证再写进去**，否则被它当众纠正。
4. **交付结构固定三块**：①它说对的（含它反驳我的地方，附我的核实结果）②它说错/说不准的（标出来）③它对用户的实际结论。**不要把它的话原样转述**——它纠正的是我，转述前必须先回查本机事实，答错了要当场认。
5. 🔴 **它的定量结论必须回本机原始日志逐项核验再转述**（2026-11-13 实测，gpt-6.1-sol 审「健康助理上下文治理」）：
   - **它对的地方**：推翻了我「变慢 = 每轮重放 26.8 万 tokens」的诊断，指出「缓存读取量 ≠ 重新计算量」；
     并抓出我漏统计了助手消息的 `tool_calls`（写文件参数）——实测那一项 376K 字符，**比 content 总量还大**。
   - **它错的两类（都会误导决策）**：
     - **拿累计平均值当现状**：它用 `cache_read_tokens ÷ api_call_count` 算出「每次 prompt 27.1 万」，
       但那是 968 次调用的历史平均；日志里当前末态是 **34.8 万**、峰值 49.8 万。
     - **用错权重**：它花整节算「剪枝破坏缓存要 1176 次调用才回本」，
       而按本机计价实测 8 天总花费才 **1.75 美元**——成本根本不是约束，延迟才是。
   - **正确姿势**：拿 `agent.log` 的 `API call #N: in= out= latency= cache=` 原始行做**双桶对照**，
     而不是拿它的推算当结论。凡是它给的「平均值 / 累计值 / 回本周期」，先问一句「这是现状还是历史均值」。
5. 长分析一律 **background + notify**，别用前台；提取按「最后一个 codex 标记 → tokens used」，跑完先看有没有 `usage limit`。

## 看图 / 写文件执行类任务（2026-09-08 实测：隔玻璃反光去除）
- 用户说"让 GPT-5.6 处理(图片/任何任务)"→ **一律走 codex exec,不是 API 调用**(用户明示纠正:「不是用api调用gpt5.6sol,是用之前调用codex的方式」)
- `-i, --image <FILE>...` 把图片附给 GPT-5.6(它能看图;可重复 -i 附多张)。原图先拷成干净文件名放工作目录(用户图在 hermes cache/images/img_*.jpg)
- 要 codex **自己写脚本+运行**(如图像处理)→ `--sandbox danger-full-access`,配 `-C <工作目录>` + prompt 限定"别碰工作目录外文件";纯审查仍用 read-only
- ⚠️ **前台 timeout 先于 codex 完成触发**(实测 420s 被杀,但产物已落地):超时后先查产物文件(mtime/是否存在)再判定,勿直接认定失败;长任务用 background+notify
- 交付前自验(不信 codex 自报):自己重跑脚本看 stdout、核对输出尺寸、做 before/after 对比图(cv2.vconcat+putText 标签)+ vision_analyze 目检,再交付 MEDIA: 路径
- 完整配方(调用骨架/prompt 要素/验证/反光去除技法/坑): [`references/codex-image-task-recipe.md`](references/codex-image-task-recipe.md)

## 长文本分析类任务(2026-09-08 实测:瑞幸vs爱回收选址前景)
- 覆盖面广/要出长报告的"分析类"(非图片、非审查 findings)→ 用 background + notify 跑,避免前台 timeout:**`"$CODEX" exec ... < prompt.txt > codex_out.txt 2>&1` + background=true notify=true**,完成后从 codex_out.txt 清洗提取
- 提取姿势同"输出格式"节:ANSI 清洗 → 取 `\ncodex` 之后、`tokens used\n<N>` 之前的正文;codex_out 会重复整段分析两次(尾部),取第一个 `tokens used` 前为止,再 `body[body.find('# ') :]` 去起手杂质
- 🔴 **正文起点要锚「最后一个」codex 标记（2026-10-08 实测）**：分析类 stdout 里会混进 `web search: ...` 工具痕迹，且出现**多个** `codex\n` 标记（本次报告前有 1 块工具痕迹 + 2 个标记）→ 用 `body.rfind('# <报告标题>')` 锚定，或从**最后一个** `codex` 标记切，再截到 `tokens used`。取第一个标记会把工具痕迹当成交付内容输出给用户。
- 💰 **投资/决策类分析的 prompt 必须写全六要素**：①持仓（数量+均价）②约束（产品形态/能否做空/操作频率）③实时数据快照（标日期与来源）④我方量化系统读数 ⑤定价/分析框架 ⑥明确几问几答的交付格式。只给行情不给持仓，它只能回通用建议。脚本形态：`-c 'model="gpt-5.6-sol"'` 作为 args 列表项直接传参正常（2026-10-08 实测：长分析 201s / exit 0）。
- 🔑 **GPT-5.6-Sol 会主动纠正你喂的"二手来源数据"**:本会话它独立抓出我搜到的 3 处过时/错误数据(瑞幸证券已转场外交易、京东协议2026-03已续至2030年底、瑞幸Q2同店进一步-5.3%)。→ 给它的"候选数据"按草稿对待,别当定稿;分析 prompt 里附上来源 URL,它能在正文首段主动列出数据校正。这比我自己交叉验证更省力且更准
- 🔴 **用户质疑你的分析 → 立刻拿 gpt-6-astra 对打（2026-10-18 定型）**：用户说"XX 有点牵强吧"时，**不要辩护也不要马上认错**——把「你的原始论点 + 用户的反驳原话 + 你查到的硬数据（标为待核实）」一起喂给 `-c 'model="gpt-6-astra"'`，要求它：①逐个论点打分并指认哪些牵强 ②给出更准确的替代框架 ③指出你的认知盲区。
  - prompt 里必须明写"**你可以否定提问方**"，否则模型会和稀泥
  - 数据按**草稿**提交并附来源 URL；本次 Astra 抓出 5 处（博通 160 亿是 AI 半导体收入指引而非总营收、"7月跌22.30%"是高点回撤被误读成整月跌幅、涨价≠利润、成交额/开户数不是净流入、券商与学者原话属修辞证据而非事实证据）
  - 它也会**纠正用户的推理**（本次："A股涨得比美股多所以不是跟涨"不成立，因为口径不同——纳指 16.05% 是 5 个月、科创50 64.25% 是 6 个月）。交付时如实分成「用户说对的」与「用户说错的」两块
  - background+notify 跑（high reasoning 实测约 4-6 分钟 / 89K tokens）
  - 🔴 **它纠"时间线"时先回去看用户原话**：本次它纠的是我 prompt 里的表述（"从6月起持续调整"），而用户实际说的是"6月之后"——用户没错，别把对 prompt 的纠正原样转述给用户
- 完整配方(分析 prompt 结构/background 骨架/校正行为/交付): [`references/codex-analysis-recipe.md`](references/codex-analysis-recipe.md)
- Codex 账号封号风险审计(官方CLI唯一使用面确认/红线/工具评估): [`references/codex-account-safety-2026-09.md`](references/codex-account-safety-2026-09.md)

## 🔴 配额撞限：判别、红线、以及「不要自动换模型顶替」（2026-10-19 实测）

**症状**：header 之后直接报

```
ERROR: You've hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro),
visit https://chatgpt.com/settings/usage to purchase more credits
or try again at 12:39 PM.
```

**判别三件事**：
1. **配额按账号算，不按模型**——实测 `gpt-6-astra` / `gpt-5.6-sol` / `gpt-5.6-luna`
   返回**一模一样**的错误。所以“换个模型试试”是无效动作，别浪费轮次。
   报错里的 `try again at HH:MM` 就是恢复时刻。
2. **exit code = 1**，且 stdout 里**没有** `codex` 正文标记、没有 `tokens used`。
3. 最快的判别法：`printf '只输出 JSON: {"ok": true}' | codex exec ...` 冒烟——秒回同一错误。

🔴 **不要拿别的模型（Opus/Claude Code、网关上的 kimi/qwen/deepseek）偷偷顶替。**
外部审查通道撞限是**用户的决策点**，不是你的降级点：他要的是“这个模型的意见”，
换一家出来的不是同一件商品。**正确做法 = 如实告知撞限 + 恢复时刻 + 问他等还是换**，
由他拍板。（同源偏好：fallback 是最后手段，见 `hermes-china-providers`。）

## 🔴 账号存活判别：封号 / 撞限 / 凭证失效 三态分清（2026-11-07 实测）

用户问「听说今天很多人 ChatGPT 账号被封，我这个被封了吗」时走这条。

**① 零成本探针（不耗配额、秒回）**——用 auth.json 里的 access_token 打账号接口：

```python
d = json.load(open(os.path.expanduser("~/.codex/auth.json"), encoding="utf-8"))
tok, acct = d["tokens"]["access_token"], d["tokens"]["account_id"]
# curl -s -w '\n[HTTP %{http_code}]' -H "Authorization: Bearer <tok>" \
#      -H "chatgpt-account-id: <acct>" -H "User-Agent: Mozilla/5.0" \
#      https://chatgpt.com/backend-api/me        （env 里必须带 10808 代理）
```

- `[HTTP 200]` + `{"object":"user","id":"user-...","email":...,"name":...}` → **账号活着**
- 401/403 → token 过期或账号失效；此时再做一次真实调用（下面 ③）才能区分「需刷新」与「真封」

**② 账号身份/邮箱/套餐从 id_token 解**（不联网、不打印 token 本身）：

```python
p = d["tokens"]["id_token"].split(".")[1]; p += "=" * (-len(p) % 4)
j = json.loads(base64.urlsafe_b64decode(p))      # email / name / sub
j["https://api.openai.com/auth"]                 # chatgpt_plan_type / chatgpt_account_id
```

本机实测（2026-11-07）：email=`yucui3516@gmail.com`，`sub` 前缀 `google-oauth2|`（= Google OAuth 直接登录，不是邮箱密码注册），plan=`plus`。
⚠️ `chatgpt_subscription_active_until` 会停在旧日期（实测停在 2026-08-23 但账号照常可用），**别据此判断订阅过期/账号异常**。

**③ 三态判别表**：

- `exit 0` + 有 `codex` 正文标记 + `tokens used` → 正常
- `You've hit your usage limit` → 撞限（按账号算，换模型无效，见上一节）
- 401 / `deactivated` / 有报错但无正文标记 → 封号或凭证失效

**④ 验证方式按他的说法来（本次被中途打断纠正）**：他说「你直接问他一个问题，看看能不能回答」时，就真的跑一次问答（例：问 2026 美国中期选举进展），**把他的原话贴给他**——这才是他要的验证。技术探针(skill 里的 ①②)可以跑也可以顺带提一句当旁证，但**不要并列成「两种方法」汇报**：他会打断说「不要用两种方法了」。他要的是直观、自己看得懂的验证，不是我的探测矩阵。

**相关**：ChatGPT 对话/数据有几套存放位置、官方导出怎么走、本机 Codex 会话体量 → [`references/chatgpt-data-backup-paths.md`](references/chatgpt-data-backup-paths.md)

## 🔴 正文提取的失败守卫（2026-10-19 实踩）

正文提取用「最后一个 `codex` 标记 → `tokens used`」这套锚点，**在失败运行上会静默出错**：
配额撞限/报错时根本没有 `codex` 标记，`m` 为空 → 回退成 `body = raw` →
**整个 header + prompt 回显被当成“回答”存进产物文件**，长度看着还挺像回事（本次 4769 字符），
很容易当成功交付给用户。

**必须加两道守卫（缺一不可）**：

```python
if "usage limit" in raw or "hit your usage" in raw:
    print("QUOTA_BLOCKED"); sys.exit(2)          # ① 先判失败，别进提取逻辑
m = list(re.finditer(r"(?:^|\n)codex\n", raw))  # ② 正则要兼容“行首无前缀”
body = raw[m[-1].end():] if m else ""
if not m:                                        # ③ 没标记就砍 header，而不是全留
    i = raw.find("\n--------\n")
    j = raw.find("\n--------\n", i + 1) if i != -1 else -1
    body = raw[j + 10:] if j != -1 else ""
```

另外：正文起点一律取**「最后一个」**标记（分析类 stdout 里会混进 `web search:` 工具痕迹 + 多个标记）。

## 输出格式与 JSON 提取
- stdout 含回显结构：`user\n<prompt>\ncodex\n<json>\ntokens used\n<N>\n<json>`——**JSON 出现两次**
- 也可能是 ```json 围栏包裹
- 🔴 **嵌套陷阱**：JSON 可能是外层 `{"findings":[...]}` 含内层 `{"severity":...}` 对象——取"最后一个合法块"会取到内层（无 findings 键）→ 静默丢 findings
- ✅ 提取姿势：解析所有平衡 `{}` 块 → 优先选含 `findings` 键的块，否则取最长。带单元断言：嵌套/单层/围栏三种形态
- 🔴 **stdout 含 ANSI 控制字符 → read_file 判 binary 无法直读（2026-08-31 实踩）**：subprocess capture 的 stdout 里有 `\x1b[...m` 转义序列（及杂散控制字符），`read_file` 会报 "Binary file - cannot display as text"。**用 python 清洗后再存/读**：`re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)` + `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)`；正文在 `codex\n` 标记之后、`tokens used\n<N>` 之前（清洗后 `re.sub(r'\ntokens used\n[\d,]+$', '', body)` 去掉尾部）

## 审查用法（GPT-5.6 作审查者的模式）
- 审查 prompt 结构：RUBRIC（检查项+严重度分级）→ 【待审内容】→ 【候选数据/来源】（有则给，审查者做跨数据比对）
- findings 输出：`{"findings": [{"severity": "hard|soft", "category", "location", "issue", "fix"}]}`
- 审查者 prompt 强制"不确定即标 hard"→ 能纠正生成模型的知识偏差（8/11 实测 GPT 独立抓出"DeepSeek是字节旗下"归属错误 + 跨候选数据的时间/表述不一致）
- 单次调用成本/耗时：实测 1-4 分钟（token 消耗 ~3K-17K）
- 完整审查管线实例：见 trendradar-operations `references/daily-report-review-2026-08.md`（daily_report_review.py）

## 验证
- 连通性冒烟：`printf '只输出 JSON: {"ok": true}' | codex exec --skip-git-repo-check --sandbox read-only`（bash 里）→ 输出含 `{"ok":true}` + `tokens used`
- 脚本化调用后必须断言提取到的 JSON 结构（findings 键存在），不能只看 exit 0

## 交付验证（Codex 改完本机 hermes 代码后,三步确认"修复已生效"）
1. **修复是否已进 HEAD**:`git ls-tree HEAD <文件>` 有输出 = 已提交。⚠️ 本机仓库是 shallow clone → `git log` 可能只有 1 行且 `git merge-base --is-ancestor` 返回 false,别据此误判"修复不在"
2. **运行中的 gateway 是否已加载新代码**:进程 wmic CreationDate > 文件 mtime → 是(2026-09-04 样例:gateway 06:51:46 启动,修复文件 06:50:29 落盘 → 已加载)
3. **无 pytest 时直接函数级实测**(比读代码更有说服力):`venv/Scripts/python.exe -c "import sys; sys.path.insert(0, r'<repo绝对路径>'); from <模块> import <函数>; print(<函数>(...))"` — 验证 provider 识别/header 生成等核心逻辑

## 迁移与恢复
- **Opus → GPT-5.6 Sol 迁移全景**（2026-09-01：改动逐文件清单、回滚备份、解冻恢复路径、"双审→单审"用户裁决）：[`references/opus-to-gpt56-sol-migration-2026-09.md`](references/opus-to-gpt56-sol-migration-2026-09.md)
