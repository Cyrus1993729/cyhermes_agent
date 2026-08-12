---
name: codex-cli
description: 经 codex exec 调 GPT-5.6 做审查/方案时使用。含 Windows 调用姿势与 JSON 提取。
version: 1.0.0
category: autonomous-ai-agents
tags: [codex, cli, gpt-5.6, review, windows]
---

# Codex CLI 调用（GPT-5.6 非交互）

## 触发
- 需要用 GPT-5.6（Codex 背后模型）做审查/独立方案/双审对比（对应 claude-code skill 的定位）
- 用户说"走 Codex / GPT 审查"或脚本需要调 codex
- 维护调用 codex 的脚本（如 daily_report_review.py）

## 环境事实
- 安装：`~/.local/bin/codex` 是 **bash 脚本**；同目录 `codex.cmd` 是 Windows 包装器（内部 `powershell Get-ChildItem $env:LOCALAPPDATA\OpenAI\Codex\bin\*\codex.exe | Sort LastWriteTime | Select -First 1` 定位最新 codex.exe）
- 版本实测：codex-cli 0.146.0-alpha（2026-08）
- 必须走代理 7897（OpenAI 被墙）：`HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:7897`

## 调用姿势（Windows subprocess，实测定型）
```python
env = dict(os.environ)
env["HTTP_PROXY"] = "http://127.0.0.1:7897"
env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
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

## 输出格式与 JSON 提取
- stdout 含回显结构：`user\n<prompt>\ncodex\n<json>\ntokens used\n<N>\n<json>`——**JSON 出现两次**
- 也可能是 ```json 围栏包裹
- 🔴 **嵌套陷阱**：JSON 可能是外层 `{"findings":[...]}` 含内层 `{"severity":...}` 对象——取"最后一个合法块"会取到内层（无 findings 键）→ 静默丢 findings
- ✅ 提取姿势：解析所有平衡 `{}` 块 → 优先选含 `findings` 键的块，否则取最长。带单元断言：嵌套/单层/围栏三种形态

## 审查用法（GPT-5.6 作审查者的模式）
- 审查 prompt 结构：RUBRIC（检查项+严重度分级）→ 【待审内容】→ 【候选数据/来源】（有则给，审查者做跨数据比对）
- findings 输出：`{"findings": [{"severity": "hard|soft", "category", "location", "issue", "fix"}]}`
- 审查者 prompt 强制"不确定即标 hard"→ 能纠正生成模型的知识偏差（8/11 实测 GPT 独立抓出"DeepSeek是字节旗下"归属错误 + 跨候选数据的时间/表述不一致）
- 单次调用成本/耗时：实测 1-4 分钟（token 消耗 ~3K-17K）
- 完整审查管线实例：见 trendradar-operations `references/daily-report-review-2026-08.md`（daily_report_review.py）

## 验证
- 连通性冒烟：`printf '只输出 JSON: {"ok": true}' | codex exec --skip-git-repo-check --sandbox read-only`（bash 里）→ 输出含 `{"ok":true}` + `tokens used`
- 脚本化调用后必须断言提取到的 JSON 结构（findings 键存在），不能只看 exit 0
