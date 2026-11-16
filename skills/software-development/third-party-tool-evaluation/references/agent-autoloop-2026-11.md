# Agent-Autoloop 评估案例（2026-11-05，结论：暂不部署，2026-11-08 后复评）

来源：小红书「数字生命卡兹克」图文帖（24 图）+ GitHub 仓库核对。

## 项目事实（已核实）

- 仓库 `KKKKhazix/agent-autoloop`，MIT，TypeScript，2545 star / 502 fork，创建 2026-11-03
- 定位：给命令行 Agent（Claude Code / Codex / ACP / 通用命令）加一层确定性的自动化中台
- 架构：~1600-1800 行、零运行时依赖的内核（Node）+ 四方向全部插件化：事件（GitHub/GitLab Webhook、HTTP、定时、轮询脚本）、Agent、通道（桌面通知/飞书/钉钉/企微/Slack/Discord）、交付（deliver 标签 → 审代码→等 CI→合并→等发布→核对线上版本）
- 内核只干四件事：收事件、按规则派活、派给 Agent、记日志；**不联网、不写死产品名**，有测试强制架构边界
- Hermes 被官方列为可直接接入的 Agent：`hermes chat -q {prompt}`

## 四个机制（真正值得借的部分）

1. **挂起零消耗**：等拍板时进程退出、状态落库，三天不回不烧 Token，点一下接原对话继续（借自审批/订单长流程的存档读档）
2. **事件溯源**：只追加账本，同一件事只记一次；`why N` 一条命令翻出任意一轮的来龙去脉（借自银行账本）
3. **指令数据分离**：外部文字（Issue 正文等）只落文件当资料，不拼进提示词；权限/目录只由本机 rules.json 决定（借自 SQL 参数化，防 Prompt 注入）
4. **跳数熔断**：Agent 叫醒 Agent 层数累加，超 8 层只记录不再派活（借自网络包 TTL）

## 对照结论（用户现有系统 = Hermes + 18 cron）

已有（≈70% 重叠）：定时触发、多通道送达（TG / 微信）、多 Agent 编排、Skill 体系、会话续接（`hermes -c`）。

真正缺的：
- 事件驱动几乎为零（18 个 job 里 14 个纯时间触发）
- 没有存档—读档：请示后答复飘在聊天流里，接不住就断
- 外部文本（小红书/公众号/PDF）直接进上下文，无架构级防注入
- 多模型互调靠 skill 里写死的「≤3 轮」自律，无系统强制熔断
- 4 个看门狗 + 3 个投递检查 = 用定时任务互修不可靠的定时任务

## 裁决

**现在不装**。三条理由：① 官方明确只支持 macOS/Linux，Windows 版作者称 2026-11-07~08 才开发测试（issue #17）；② 装了就是 Hermes + Autoloop 双系统（两套 cron / 会话 / 通知），维护成本翻倍；③ 真正的价值是四个机制，不是这个软件。

（GitHub 上有第三方移植 `yangfan27/agent-autoloop-win`，5 star，不碰。）

## 复评触发点

2026-11-08 之后：若官方 Windows 版如约发布且 star/issue 健康度正常，重新评估「Autoloop 当内核 + Hermes 当 Agent 插件」的组合。

完整交付：`~/AppData/Local/hermes/output/2026-11-05_Agent-Autoloop开源_personal-meaning.md`
