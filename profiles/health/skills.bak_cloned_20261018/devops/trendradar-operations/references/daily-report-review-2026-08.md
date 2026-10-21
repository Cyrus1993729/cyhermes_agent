# 日报投递前自动审查机制（2026-08-11 上线）

## 背景与触发
8/11 五类日报出现"DeepSeek是字节旗下大模型团队"事实错误（qwen3.7-max 生成，B站热搜仅标题，prompt 逼模型补背景 → 幻觉）。用户拍板：
- cron 主模型切回 deepseek-v4-flash（qwen 仅 DeepSeek 拥堵且短期无法恢复时应急）
- **所有日报发出前必须过一轮审核**，但**不走完整 5 步流程**（日报高频，契约/闸门/复盘过重）
- 审查模型最终定调（2026-08-11 晚）：**只保留 GPT-5.6（走 Codex CLI），qwen 暂不参与**——脚本 `--model gpt|qwen|both` 参数控制，默认 gpt，想恢复双模型传 `--model both`（qwen 调用代码保留不删）

## 三层质检设计
```
生成草稿 → L0 硬规则（本地正则，零成本）→ L1 模型审查（默认 gpt=GPT-5.6 via Codex CLI）
→ 自动修复（≤1 轮）→ 投递
审查服务异常 → 降级只跑 L0，照发 + 日报末尾标注"⚠️ 今日未经模型审查（审查服务异常）"
```
- **L0**（daily_report_review.py l0_check）：禁止词（值得关注/持续观察/建议跟进/综上所述/详见原文/原文未说明）、喊单词（加仓/减仓/抄底/梭哈/清仓/止盈/止损→soft 标记交模型判）、链接缺失（<1 个即 hard）、"背景："行全部标记待核实、模块完整性
- **L1（当前单模型 GPT-5.6）**：Codex CLI 调用（见下）。未调用的模型在输出标记 `skipped: true`，findings 不计入合并
- **L2 用户兜底**：日报保留来源标注；"背景："内容要么删除要么明示"未核实"——用户 10 秒可校验

## 双模型互补原理（为什么留 --model both 开关）
- **审查必须异源**：同源审查（qwen 审 qwen 生成物）会放行同样的知识偏差——8/11 前 qwen 生成错误、若 qwen 审也会放行（语料里"DeepSeek=字节"是共现噪声）。
- 8/11 双模型实测：qwen 和 GPT **双双独立**抓出"DeepSeek是字节旗下"，GPT 还额外抓到"英伟达循环融资表述与候选不符""宇树尚未上市却说上市首日"——跨候选数据比对成果
- 意外收获：审查 prompt 强制"不确定即标 hard"时，qwen 能纠正自己的生成偏差（生成时被共现噪声带偏，审查时被推到怀疑模式给出正确判断）
- 用户定调单 GPT 后：qwen 暂退；`--model both` 保留双模型互补能力，未来可一键恢复

## 审查 RUBRIC 要点（REVIEW_RUBRIC，脚本内嵌）
1. 事实性（最高优先）：公司/人物/机构归属错误、数字与候选数据一致性、"背景："行置信度、明显编造 → hard
2. 合规性：喊单/禁止词/格式违规 → hard
3. 相关性/去重、投资视角逻辑 → soft
每条 finding：`{severity: hard|soft, category, location, issue, fix}`；输出 `{"findings": [...]}`

## Codex CLI 调用姿势（Windows subprocess，实测定型）
```python
env = dict(os.environ); env["HTTP_PROXY"] = "http://127.0.0.1:7897"; env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
prompt_file.write_text(prompt, encoding="utf-8")   # 长 prompt 走 stdin，避免命令行长度限制
r = subprocess.run(
    ["cmd.exe", "/c", r"C:\Users\Administrator\.local\bin\codex.cmd",
     "exec", "--skip-git-repo-check", "--sandbox", "read-only"],
    stdin=open(prompt_file, encoding="utf-8"),
    capture_output=True, text=True, timeout=600, env=env,
    cwd=r"D:\Workspace\Projects\TrendRadar")
```
关键点：
- `codex` 在 ~/.local/bin 是 **bash 脚本** + 同目录 `codex.cmd` 是 Windows 包装器（内部找 `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`）——**Python subprocess 直接调 `codex` 会 WinError 2**（bash PATH 的 ~/.local/bin 不在 Windows PATH），必须经 `cmd.exe /c codex.cmd`
- 必须 `--skip-git-repo-check`（否则报 "Not inside a trusted directory"）+ `--sandbox read-only`（审查只读）
- 必须走 7897 代理（OpenAI 被墙）
- prompt 作为**位置参数**有长度风险（cmd.exe 命令行 8191 上限）→ 写临时文件 + stdin 重定向
- 输出杂音：stdout 含 `user/<prompt>/codex/<json>/tokens used/N/<json>` 回显结构，JSON 出现两次

## extract_json 陷阱（实测踩坑修复）
- codex 输出可能是 ```json 围栏、纯文本、或嵌套 JSON（外层 `{"findings":[...]}` 内含内层 `{"severity":...}` 对象）
- ❌ 原实现取"最后一个合法块"→ 取到内层对象（无 findings 键）→ 静默丢 findings
- ✅ 修复：解析所有平衡 `{}` 块 → **优先选含 `findings` 键的块，否则取最长**（内层对象无 findings 键，外层有）
- 此缺陷靠验证脚本的"嵌套提取"单元断言抓出——审查脚本必须带这个断言

## cron prompt 集成（两个日报的第 4.5 步）
1. write_file 草稿落盘 `output/_draft_five.txt`（或 `_draft_cb.txt`）
2. 跑审查脚本，完整读 stdout JSON
3. verdict=PASS → 直接进入下一步；hard findings → 逐条修复（≤1 轮不重审，时间约束）：归属/数字/时间错误→删条或改写；背景行不确定→删背景行保留标题+链接；喊单/禁止词→改写
4. 审查失败 → 降级照发 + 末尾标注"⚠️ 今日未经模型审查"
- 跨境日报第 1 步同步改为 `prepare_candidates.py --crossborder-only > output/candidates_cb.json`（候选落盘供审查比对）

## 验证方法（可复用）
- 回归样本：`~/AppData/Local/hermes/scripts/fixtures/draft_five_20260811_test.txt`（含已知错误"DeepSeek是字节旗下"的日报草稿）
- 验证脚本（Temp，hermes-verify- 前缀）：py_compile + L0 单元断言（禁止词/喊单词/背景行/链接阈值边界）+ extract_json 三种形态（嵌套/单层/围栏）+ merge 去重 + **端到端真实双模型调用**（断言 verdict=FIX、qwen/gpt ok、双模型 findings_count>0、抓到 DeepSeek 归属错误）
- 输出格式：`{l0, qwen:{ok,findings_count}, gpt:{ok,findings_count}, findings[], verdict, hard_count}`——findings_count 字段必须存在（曾把各模型 findings 从输出过滤掉导致无法验证双模型都有产出）

## 教训
1. 生成端规则 > 事后审查：先堵"凭记忆补背景"源头（Pitfall 18），审查是第二道闸
2. 换模型是有副作用的变更：防"慢"引入"知识偏差"——模型替换后首轮输出必须盯事实性断言
3. 高频产物审查要轻：固定规则 + ≤1 轮修复 + 失败降级，不阻塞投递
4. 审查器 prompt 强制"不确定即标 hard"能纠正生成模型的共现混淆
