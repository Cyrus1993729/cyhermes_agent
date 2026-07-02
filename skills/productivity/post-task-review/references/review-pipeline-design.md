# 三层审查管线设计方案（Opus 设计，2026-07-02）

> 和 Opus（Claude Code CLI）多轮讨论后产出的审查系统设计。
> P0 已落地（脚本写盘+冒烟通过），P1-P3 待实施。

## 一句话概括

干活前先定验收标准（Sprint Contract）→ 干完后千问逐条检查（L1）→ 有问题再让 Opus 深查（L2，仅手动）。

## 架构

```
用户任务
  ↓
[事前] Sprint Contract：列出验收标准，用户确认
  ↓
[干活] DeepSeek v4-pro 执行
  ↓
[事后] 千问 L1 逐条审查 → PASS / CONDITIONAL / FAIL
  ↓
[升级] FAIL 或 CONDITIONAL≥3 → 用户手动决定是否上 Opus L2
```

## 四个组件

### 1. Sprint Contract（任务契约）
- 任务开始前，Agent 自动起草验收清单
- 包含：交付物清单、每项验收标准、口径定义、边界（不做什么）
- 用户确认后才开工
- 实现：`sprint-contract` skill（待创建）

### 2. L1 审查（千问 3.7 Max）
- 干完后自动调千问，对照契约逐条打分
- 三维度：任务完成度 / 过程质量（事实-推理-判断三分类）/ 风险合规
- 逐条裁决，不打包
- 实现：`l1-review` skill（待创建）+ `scripts/qwen_review.py`（✅ 已落地）

### 3. L2 升级（Opus，仅手动）
- L1 判定 FAIL 或 CONDITIONAL≥3 时，向用户建议升级
- 用户说"让 Opus 看"才触发
- 走 Claude Code CLI + 代理 `127.0.0.1:7897`，永不自动
- 实现：`scripts/l2_opus.sh`（待创建）

### 4. 记忆时效检查
- 扫描 MEMORY.md / USER.md 中的过期、重复、未定状态条目
- 只出报告，不自动删
- 实现：`scripts/mem_gc.py`（✅ 已落地）

## L1 审查技术细节

### 为什么不用 delegate_task？
`delegate_task` 不支持 per-call 指定 provider，子代理继承父模型（DeepSeek），无法单独指定千问。详见 `hermes-china-providers` skill。

### 替代方案：execute_code 直连千问 API
`qwen_review.py` 从 config.yaml 动态读取 qwen-bailian 的 `api_key` 和 `base_url`，用标准库 `urllib.request` 直接调 `/chat/completions`。

调用方式：
```bash
python scripts/qwen_review.py --contract contract.md --deliverable report.md
```

API 格式：
```json
{
  "model": "qwen3.7-max",
  "messages": [{"role": "system", "content": "<审查规则>"}, {"role": "user", "content": "<契约+交付物>"}],
  "temperature": 0.2,
  "response_format": {"type": "json_object"}
}
```

### 关键发现

- **delegate_task 不支持 per-call provider** — 改走 execute_code 直连
- **千问 API 在中国大陆直连，不需代理** — base_url 是阿里云北京节点
- **config.yaml 中 qwen-bailian 的 api_key 是 `sk-ws-` 开头的工作空间密钥** — OpenAI 兼容模式（chat_completions）可用

## Memory 文件

- 路径：`C:\Users\Administrator\AppData\Local\hermes\memories\MEMORY.md` 和 `USER.md`
- 格式：`§` 单行分隔条目，条目可多行，纯 markdown
- mem_gc.py 直接读文件，不通过 memory 工具

## P0 冒烟结果（2026-07-02）

**mem_gc.py** ✅：
- 发现 2 VOLATILE（"雷达层待定"、"Free额度耗尽待充值"）
- 发现 2 SUPERSEDED（"任务复盘已迁移为 skill"等）
- 发现 1 DUP 0.91（MEMORY.md ↔ USER.md 中 Opus 调用规则跨文件重复）

**qwen_review.py** ✅：
- 千问 API 连通，33秒返回
- 测试"1+1=3"样例，千问正确判 FAIL，逐条指出错误
- JSON 解析正常，escalate 逻辑正常

## 待落地文件

| 文件 | 路径 | 状态 |
|:---|:---|:---|
| mem_gc.py | `scripts/mem_gc.py` | ✅ |
| qwen_review.py | `scripts/qwen_review.py` | ✅ |
| sprint-contract skill | `skills/productivity/sprint-contract/` | ⏳ |
| l1-review skill | `skills/productivity/l1-review/` | ⏳ |
| l2_opus.sh | `scripts/l2_opus.sh` | ⏳ |

## 分阶段计划

- **P0** ✅：mem_gc.py + qwen_review.py 写盘并冒烟验证
- **P1** ⏳：l1-review skill + 用历史交付物跑一次验证审查质量
- **P2** ⏳：sprint-contract skill + 跑通完整任务闭环
- **P3** ⏳：记忆治理常态化 + cron + L2 兜底

## 红线

- 所有脚本/skill 只报告不自动改
- Opus 升级永远手动，不自动触发
- 改文件/config 前必须先给草案让用户确认
- 审查结果写 `reviews/` 不入 memory（memory 已 94% 满）
