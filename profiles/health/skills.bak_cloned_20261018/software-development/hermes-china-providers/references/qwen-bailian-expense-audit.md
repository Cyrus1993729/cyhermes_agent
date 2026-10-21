# qwen-bailian（千问直连）费用排查方法论

**实踩日期**：2026-08-31（用户报"千问直连 API 最近一直有费用产生"）

## 核心：区分两种"qwen"——只有直连才产生阿里云百炼费用

| 特征（agent.log） | 归属 | 计费 |
|---|---|---|
| `provider=custom` + base_url 含 `maas.aliyuncs.com`（如 `ws-xxx.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`） | **qwen-bailian 直连** | 阿里云百炼账单 ← 用户所说的"千问直连费用" |
| `provider=opencode-go-anthropic model=qwen3.7-max` | OpenCode 网关的 qwen | OpenCode 订阅，与阿里云无关 |

- 8/29、8/30 网络故障期每天 39 次 qwen3.7-max 调用**全是 opencode-go-anthropic**（订阅），别误判成百炼费用
- grep 特征：`grep -ahE "model=qwen3.7-max" agent.log* | grep -aoE "provider=[a-z-]+" | sort | uniq -c`

## 证据文件定位调用方（agent.log 查不到脚本直连调用）

> 脚本直连（report_gen_qwen.py / qwen_review.py）走 urllib，**不经过 agent.log 的 API call 记录**（成功的 terminal 调用只记 `completed (时长, chars)`，不含命令文本）。要看产物侧证据。

1. **`~/AppData/Local/hermes/reviews/review_log.jsonl`** —— qwen_review.py 每次审查一条 JSON 记录（ts/task/verdict）。L1 审查频率的真相源。
   - 实踩：黄金周报每周一 L1 审查 2-6 次/期（8/03:4 次、8/10:4、8/17:6、8/24:2、8/31:6）→ **规律性费用主力**（每周固定）
2. **日报存档标注** —— qwen 引擎触发痕迹：`archives/crossborder/*.md` 含"⚠️ 今日 DeepSeek 过载，日报由 qwen3.7-max 生成"（8/21、8/27 实踩）
3. **一次性高峰** —— config `cron.model`/`cron.model_provider` 曾整体配 qwen-bailian（8/10 黄金周报会话 18 次 + 跨境日报 16 次 + 8/11 五类 9 次 ≈ 43 次调用）；排查时对比当前 `cron:` 段确认已改回（当前 deepseek-v4-flash @ opencode-go）

## 计费模式定方向（需用户去阿里云控制台确认）

- `maas.aliyuncs.com` 专属部署端点（ws-xxx workspace 端点）**按实例在线时长计费（元/小时），无人调用也在扣**
- 用户报"一直有费用"→ 先让用户看账单：**实例费**（停调用无效，需手动释放专属服务实例）vs **调用费**（上面两个脚本是主源）

## 止血选项（需用户拍板）

- 黄金周报 L1 审查（qwen_review.py）迁移到 GPT-5.6/Opus，或降低审查轮次
- 专属实例若不常用 → 控制台释放，改用按量 dashscope 公共端点