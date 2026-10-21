# Opus 辅助代码审查与修 Bug 工作流

> 2026-07-03 实战验证：诊断 Hermes 微信消息投递限流根因 → Opus 红队审查 → 出代码 diff → 应用修复。

## 适用场景

- 定位了一个复杂 bug，写好分析文档，想让 Opus 做红队审查
- 需要 Opus 对技术方案给出代码级别的修正意见

## 完整流程（六步，不可跳过）

### 🔴 Pitfall：跳过 sprint-contract 或 L1 审查（2026-07-03 踩坑）

**症状**：Opus 审完出 diff → Agent 直接 `patch` 改代码 → 用户问"千问审了吗？契约写了吗？" → 全部没做。

**根因**：Agent 把 Opus 审查当最终步骤，忘了基础设施改动也属于"交付物型任务"，需要走完整管线。

**规则**：任何涉及代码/配置/基础设施改动的任务，Opus 出 diff 后 **不能直接改**，必须走完下面六步。

---

### 第一步：写 sprint-contract

改动前先产出契约文件（`contract_<任务名>_<日期>.md`），定义验收标准、边界、升级规则。参见 `sprint-contract` skill。

### 第二步：写分析文档（嵌入契约要求）

```markdown
# 问题标题

## 一、已遇到的问题清单
（列具体场景，附日志行号、时间戳）

## 二、现有防御机制盘点
（代码位置 + 作用 + 缺口）

## 三、解决方案
（方案 A/B/C，附代码行号）

## 四、待 Opus 审查的问题
（列出 5-10 个具体技术问题，让 Opus 逐一回答）
```

### 第三步：Opus 红队审查

```bash
# 1. 准备 prompt（文档内容嵌入，不能只给路径）
cat > /tmp/opus_review_prompt.txt << 'EOF'
你是红队审查员。批判性审查以下技术方案，只找问题，不找优点。
{文档全文}
EOF

# 2. 后台运行（可能超 600s）
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
claude -p "$(cat /tmp/opus_review_prompt.txt)" --model opus --max-turns 15 --output-format text
```

Opus 返回后：
- 先完整呈现给用户
- 区分「致命/严重/中等/轻微」
- 追问推荐方案：「三个方案里推荐哪个」

### 第四步：用户确认方案

Opus 推荐后，**必须等用户确认**，不能直接动手。

### 第五步：出 diff + 应用

```bash
claude -p "你推荐的方案，给出最小改动的 unified diff，标注每处意图和影响" --model opus --max-turns 10
```

用户说"改吧" → 用 `patch` 应用 diff → 验证语法和导入。

### 第六步：千问 L1 审查

执行 `sprint-contract` 的升级规则：`python scripts/qwen_review.py --contract <契约> --deliverable <交付物汇总>`。通过后告知用户重启生效。

---

## 关键要点

- **文档嵌入，不传路径**：Opus `-p` 模式无本地文件系统权限
- **后台运行**：Opus 分析可能超 600s，用 `background=true` + `notify_on_complete=true`
- **审查提示词要红队化**：「你是红队审查员，只找问题，不找优点」
- **追问要聚焦**：先拿到审查结果，再单独问「三个方案里推荐哪个」「出 diff」
- **六步全走**：contract → 分析 → Opus → 确认 → diff+改 → L1，缺一不可
