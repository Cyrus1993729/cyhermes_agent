# 双机 Hermes 架构与跨版本能力评估（2026-09-01 会话沉淀）

## 背景

用户两台电脑分工：老机 = 10 年前双核 Windows 笔记本（本机，Hermes v0.19.1，24/7 在线，Clash 代理 127.0.0.1:7897）；新机 = 高配新电脑（装 v0.21 Pantheon，工作时间开机）。定位：老机轻助理（小红书理解、固定 cron 日报）+ 定时任务 + 派活方；新机执行重活（深挖分析等）。零额外费用，不租服务器。

## 版本能力实测表（决定性证据，v0.19.1 为本机实测）

| 能力 | v0.19.1（本机实测） | v0.21 Pantheon（文档/GPT-5.6 分析） |
|---|---|---|
| webhook 订阅 | ✅ CLI 存在未启用（`hermes webhook list` 提示 enable） | ✅ |
| api_server 平台 | ✅ Connected | ✅（peer 依赖它） |
| `hermes peer`（官方跨机 A2A） | ❌ `hermes --help \| grep -i peer` 无结果，`hermes peer --help` 报 usage | ✅ 新增：跨 profile/gateway、canonical 会话交棒 |
| 跨机器 peer 条件 | — | API server + `API_SERVER_KEY` + LAN/Tailscale 网络可达 |

判据：**评估双机通信方案前先实测每台机版本能力，不假设功能对齐**。

## `hermes peer` 要点（摘自 2026-08-31 Pantheon GPT-5.6 分析，D:\Workspace\output\2026-08-31_Hermes万神殿Pantheon_GPT5.6分析.md）

- 跨 profile、跨 gateway（不限于同一 Hermes 实例）；消息进入接收方**永久的 canonical Bot Chat**，非一次性子 Agent 调用——交棒语义
- 群聊硬限制：1 群 2–6 Bot、一次用户发送最多产生 10 条消息、3 轮响应
- Bot 发起的消息**不会实时插入另一个运行中的对话**（live interrupt 是未来工作）→ 派活 = 异步等结果
- 每个 Bot 独立调 pin 的模型，费用叠加
- GPT-5.6 升级建议：peer/Bot Mode 放升级验证清单最后，**不是恢复生产的必要条件**；v0.19.1→v0.21 跨约 5800 commits，cron 数据结构迁移、Bot Machine 默认开启有回归风险，等首个稳定补丁 + 独立副本旁路验证

## 双核机升级提速组合拳（升级超时误判「安装错误」的解法）

升级链路 = git 拉取 + pip 下载/构建/安装依赖 + 校验；双核老机上各环节慢 → 超过执行侧超时阈值 → 被误判安装错误。解法（按效果排序）：

1. **停 gateway 再升级**——Windows 文件锁：运行中的 gateway 占用 venv 的 .pyd → `hermes update --force-venv` 帮助文本明确警告依赖同步会半截失败（WinError 32）。交接包路径 B（先停 gateway）才是 Windows 正确姿势
2. **pip 换国内镜像**——`PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/`（或清华源），下载耗时最大头，几分钟 → 几十秒
3. **Defender 排除 hermes 数据目录**——`Add-MpPreference -ExclusionPath 'C:\Users\<user>\AppData\Local\hermes'`（需管理员）；pip 安装写大量小文件时实时扫描吃满一核
4. **执行侧超时给 600s+**——terminal/GPT 接手执行升级时默认 180-300s 会判死还在跑的安装
5. **插电 + 高性能电源计划**——防老本散热老化降频

注：`update_cmd.py` 内固定超时（120s import 探测、10s PATH 探测、300s gateway prompt）是辅助步骤，主坑在执行侧等待超时与文件锁。

## 租服务器否决理由（30 元/月档，2026-09 评估）

- 30 元档 = 2C2G，**同样是双核**，升级一样慢；4 核超预算（50-100 元档才有意义）
- 国内云服务器挂代理是**合规红线**（TG Bot API 被墙需代理）→ 封机风险；境外机 30 元内选择差、晚高峰丢包
- 现有 computer-use 桌面运维流程（升级/停 gateway）在无桌面服务器上作废，需重学 SSH 运维
- 备份/auth/config/cron 迁移成本不变，只是换地方麻烦

## skill / memory 跨机器共享结论

- skills/memory 是本地文件（`%LOCALAPPDATA%\hermes\`），默认不共享；跨机共享 = Git 备份仓库（白名单含 memories/+skills/）或 `hermes profile export/import`
- **skills 可共享**（可复用流程，跨机器有效）；**memory 大多机器特定**（路径/代理/cron 体系/API key 目录），整份搬会误导新机器
- auth.json（凭证池）、.env（API key）、**cron 任务定义不在备份内**，新机要重配（hermes auth + 填 key + 重建 cron）