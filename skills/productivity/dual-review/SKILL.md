---
name: dual-review
description: "新5步流程审查层——Codex+Opus双引擎并行全量审查+千问盲审，替代原千问L1+Opus L2"
version: 1.0.0
tags: [review, dual-engine, codex, opus, qwen, arbitration]
---

# 双引擎审查（新5步流程第④步）

## 触发条件

用户说"走新5步流程"时启用。与旧5步流程（l1-review + task-wrapup）互不干扰。

旧流程文件：`workflow_*.md`
新流程文件：`workflow_v2_*.md`

## 完整编排流程（Agent 执行 SOP）

### Step 1: 并行启动双审

```bash
# Codex 正向验证（不需 pty，不需 PTY）
HTTPS_PROXY=http://127.0.0.1:7897 codex exec --sandbox danger-full-access "$(cat ~/.hermes/skills/productivity/dual-review/references/codex-forward.md)

交付物：<path>
契约：<path>" 2>&1 | tee ~/.hermes/reviews/<task_id>/codex-r0.json

# Opus 反向证伪
HTTPS_PROXY=http://127.0.0.1:7897 claude -p --model opus --max-turns 5 "$(cat ~/.hermes/skills/productivity/dual-review/references/opus-adversarial.md)

交付物：<path>
契约：<path>" < /dev/null 2>&1 | tee ~/.hermes/reviews/<task_id>/opus-r0.json
```

两个并行跑（background=true），都设置 notify_on_complete=true。

### Step 2: 接地校验

```bash
python workflow_check.py --mode dual --step ground \
  --codex ~/.hermes/reviews/<task_id>/codex-r0.json \
  --opus ~/.hermes/reviews/<task_id>/opus-r0.json \
  --deliverable <deliverable_path>
```

### Step 3: 归并 → 分歧路由

根据接地结果：
- CORROBORATED（双方一致）→ 合并，D5随机抽1条千问复核
- INDEPENDENT（单方发现）→ 交叉质证
- CONFLICT（一方说有、一方说无）→ 分歧路由

分歧路由判据：
1. 再给一轮证据能解决？（事实类）
2. 需要用户偏好？（价值类）
3. 不确定？→ fail-safe：默认价值类上抛

### Step 4: 事实类收敛

- 4a 交叉质证：单方发现喂给另一模型确认/证伪
- 4b 定点验证：分歧压缩到一条可判定主张
- 4c 补证据：自动生成测试/fuzzing（限时5分钟）
- 4d 千问盲审：证据持平时决胜

### Step 5: 修复循环（≤2轮，全程自动，无人干预）

**核心规则**：发现问题 → 自动修复 → 自动提交复审。修复和复审之间没有任何人工确认环节。用户只在最终交付或触发上抛时才看到结果。

每轮：
1. 合并 Codex 和 Opus 的 findings → 去重 → 按严重度排序
2. Agent 自动修复所有 high/critical finding
3. 自动提交 R1/R2 复审（Codex + Opus 重新并行审查）
4. 震荡检测（停滞+回环）

```bash
python workflow_check.py --mode dual --step oscillation \
  --history-dir ~/.hermes/reviews/<task_id>/ \
  --codex ~/.hermes/reviews/<task_id>/merged-r1.json \
  --round 2
```

### Step 6: 通过验证

```bash
python workflow_check.py --mode dual --step verify \
  --codex ~/.hermes/reviews/<task_id>/final-decision.json
```

状态码：
- 0 = PASS
- 10 = PASS_WITH_NOTES
- 20 = REPAIR_REQUIRED
- 30 = USER_DECISION_REQUIRED
- 40 = REVIEW_INVALID
- 50 = ARTIFACT_VERSION_MISMATCH

### Step 7: 价值类上抛

翻译成选择题卡（A/B/C + 推荐默认值），去重批量呈现。

### Step 8: 追踪文件打勾

```bash
python workflow_check.py --mode dual --step wrap --step "④审查"
```

## 组件

- `references/codex-forward.md` — Codex 正向验证 prompt
- `references/opus-adversarial.md` — Opus 反向证伪 prompt
- `references/cross-exam.md` — 交叉质证 prompt
- `references/qwen-blind.md` — 千问盲审 prompt
- `references/grounding.md` — 接地校验规则
- `references/severity.md` — 严重度定义+通过门禁

## Pitfalls（实战沉淀, 2026-08-01）

### Opus 沙箱隔离 → 审查 prompt 必须内联交付物全文
Opus（Claude Code CLI）在默认工作目录下无法读取桌面或 hermes 目录的文件。审查时必须把交付物和契约的**全文内联到 prompt 中**，而不是给文件路径。Codex（--sandbox danger-full-access）可以读外部文件，但为了一致性也建议内联。

### 双审交叉验证价值确认
首次实战中，Opus R1 判 PASS，Codex R1 仍发现 3 条 high。单靠一个审查者会漏。双审交叉验证有效。

### Opus 擅长发现逻辑断裂，Codex 擅长发现数据精度问题
Opus 独有洞察：通胀回落+非农弱却断言加息 → 核心逻辑矛盾（D2论证）
Codex 独有洞察：PE口径混用、CPI≠PCE目标 → 数据精度问题（D3数据逻辑）

新流程默认以影子模式运行（审查但不阻断流程）。
- 静默影子（2-4周）→ 软门禁 → 正式闸
- 毕业门槛：Critical误报<1%、High精确率≥80%、接地率≥95%、结构化输出≥99%、召回≥70%、≥100任务

## 与旧流程的关系

- **old**: `l1-review` skill + `task-wrapup` skill → `workflow_*.md`
- **new**: `dual-review` skill + `workflow_check.py --mode dual` → `workflow_v2_*.md`
- 互不干扰，通过追踪文件名区分
