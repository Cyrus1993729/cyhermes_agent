# Opus 红队审契约 — 执行要点（2026-08-06 实测验证）

## 失败模式
`claude -p "$(cat prompt.txt)" --model opus --max-turns 3` → **"Error: Reached max turns (3)"，零输出**。
原因：审查类任务里 Opus 会自发进入 agentic 工具调用循环（想 WebFetch 仓库/读文件），把有限轮次烧光，结果被吞。

## 成功配方
```bash
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
claude -p "$(cat /tmp/opus_review_prompt.txt)" --model opus --max-turns 8 --tools "" --output-format text 2>&1 | tail -100
```
- `--tools ""`：禁掉全部工具，强制纯文本回答（关键）
- `--max-turns 8`：第二道保险（配合 --tools "" 其实 1-2 轮就够）
- 契约全文嵌入提示词：Opus print 模式沙箱**读不到本地文件**，给路径没用（同 claude-code skill 的 "FEED THE DOCUMENT" 教训）
- `tail -100` 截取尾部（输出长，头部是开场白）
- 先 smoke test：`timeout 90 claude -p "回复OK" --model opus --max-turns 1`，代理 404/200 均代表代理通

## 审查提示词结构（有效模板）
1. 角色：资深 DevOps/自托管专家，红队审查，任务是挑毛病不是背书
2. 用户背景：非技术、机器配置、常驻服务、代理环境、核心诉求（全自动/改配置方便/长期稳定）
3. 输出要求：结论 PASS/CONDITIONAL/FAIL；问题按【阻断级】/【建议级】分级，每条"问题+为什么+修改建议"；验收标准可判定性逐条复核表；最后一句最大风险
4. 给出重点审查方向（技术盲区、验收模糊、边界、执行顺序、非技术用户体验）但不限于

## 结果处置
- CONDITIONAL/FAIL → 逐条判断"有无解决方案"，全部有解才向用户打包呈报；用户非技术背景，结论要翻译成人话（如"静默失败=电脑重启后悄悄停摆没人知道"）
- 用户可能简化流程（不走 5 步全流程）→ 尊重，但 Opus 审结论仍值得呈报，因为它是免费的盲区扫描
