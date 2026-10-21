# 跨机分享配置（skill / memory / 用户画像 / 大文件传输）

> 从 SKILL.md 整段搬移，原文未改。什么时候读：要把本机 skill、memory、项目目录传给对端 agent 时。

## 跨机分享配置（skill/memory/规范 → peer agent，2026-09-02 实测 ✅）

场景：把本机沉淀的 skill / memory / 用户规范分享给对端 agent（如「牛来→妈妈」）。**对端是标准 Hermes 但通常零自定义 skill/memory，分享 = 给它补齐方法论与行为规范。**

### 分享前分类三问（决定 ✅直传 / ⚠️参数化 / ❌不分享）

1. **本机路径绑定**：含 `C:/Users/...`、`D:\Workspace`、API key 目录、私有仓库名 → 不分享或删实例细节
2. **凭据**：含真实 token/api key 的 skill（grep 探测：`sk-…`、`Bearer …`、`token*=*"…"`）→ 脱敏或只分享原理，密钥只留占位符
3. **环境差异**：对端可能不用同一套软件（如妈妈不用 Clash）→ **拆「事实结论」与「机器参数」**：依赖出口 IP 的事实（X 走代理、Google CAPTCHA、Bing 直连）同 WiFi 两机通用✅；端口/路径是参数（127.0.0.1:7897）删掉，改成「以本机实际监听为准」+ 自查命令（netstat）

### 用户画像分享原则（用户 2026-09-02 拍板）

- **个人背景 + 行为规范全分享**（两台都是用户自己的机器，无隐私障碍）：33岁男/财务/房贷/定投、执行规范七条、闭环契约流程、决策风格、交付内联要求——**行为规范类比背景更关键**，否则对端干活风格与本机割裂（不发「见 terminal」、守「A then B」、认哨兵语义）
- ❌ 修剪：验证/provider 管线条目（qwen 审查、GPT-5.6/deepseek 分工）→ 留到 skill 环节一起定；一次性技术决策记录（「评估 XX 不装」）分享价值低

### 投递姿势（会话内 a2a 工具未注册时的兜底）

- ⚠️ **a2a_call 等会话工具可能不在当前会话**（tool_search/tool_describe 查不到，「not currently available」）→ 不阻塞：走底层 JSON-RPC `message/send` 直连（见 probe 脚本同款姿势）
- **长中文内容必须 write_file 写 .py 脚本再执行**，勿塞命令行（引号/转义地狱）；token 从 `config.yaml` 的 `a2a_agents.<名>.auth.token` 读入临时文件，用完即删（明文凭证不留盘）
- 超时预期：对端是完整 agent（要思考+写 memory），60s+ 常态（本会话 63.6s），300s 上限安全
- **验证写入成功**：指令里要求对端回复「写了 N 条、存到哪个 target、当前字符数」；字符数/条数对得上才叫落盘
- 完整 runbook（含脚本模板/分类检查表/分享措辞）：`references/share-to-peer-2026-09.md`

### 大文件传输：技能包批量分享（HTTP zip，2026-09-02 实测 ✅ 牛来→妈妈 11 skill）

文本类配置（memory/用户画像）走 message/send 直塞；**skill 包（数百 KB）塞不进单条消息**，用临时 HTTP 服务让对端 curl 下载：

1. **打包**：python zipfile 打 `skills_pack.zip`，**zip 顶层必须是 `skills/<原相对路径>` + `scripts/<依赖脚本>` 两个目录**（对端解压到 hermes 根目录即自动合并进它的 skills/ 和 scripts/）——排除 `__pycache__`/`.pyc`/`.bak`。
2. **依赖脚本一起带**：skill 运行时引用的本机 scripts（qwen_review.py、workflow_check.py、mem_gc.py、review_trend.py、whisper_chunk.py 等）必须打包进 `scripts/`，否则对端 skill 里的命令跑不通。grep skills 目录找 `scripts/xxx.py` 引用。
3. **起服务**：`python -m http.server <端口> --bind 0.0.0.0`（background=true），本地 `curl http://127.0.0.1:<端口>/skills_pack.zip` 探活 200。
4. **防火墙**：netsh 放行入站端口（bat + UAC 提权姿势同 9900，见上）。
5. **A2A 指令**：三大步（下载 → python 解压 extractall 到 hermes 根 → rm zip）+ 注意事项（路径/端口均为示例）+ 回复要求（zip 大小、解压后目录、是否已删）。
6. **坑一（本会话实测最大坑）**：⚠️ **`%LOCALAPPDATA%` 在 MSYS bash 不展开**——给对端的指令里写 `%VAR%` 会导致下载到字面量文件名、对端找不到 zip。**指令里必须用对端实际绝对路径 `C:/Users/<对端用户名>/...`**，或用 bash 变量 `$LOCALAPPDATA`。
7. **坑二**：对端机器用户名可能与本机不同（妈妈= `C:/Users/1`，非 Administrator）——不要假设，下载前先确认对端路径（或在对端回复报「没找到文件」后改用它的绝对路径重发）。
8. **验证**：对端 `skills_list` 列名确认全部 skill 可加载（能列出 name 即成功），不只查目录存在。
9. 分享前先跑数据驱动筛选（会话库统计 skill_view 调用次数，用户标准「常用的才分享」）+ 敏感扫描（sk-/Bearer/token 字面量），完整 runbook：`references/skills-pack-transfer-2026-09.md`
10. **同一通道也传任意项目目录**（非 skill）：zip 顶层放原目录名，对端解压到 home 即用；**凭据文件（token.txt/.env）不进包**，zip 内附手动拷贝说明；Windows 下 zipfile 排除匹配须先 `rel.replace("\\", "/")` 归一化（反斜杠匹配不到的坑）；探活用 `curl -sI` HEAD 验证 Content-Length 而非 `-o /dev/null`（MSYS exit 23）。详见 runbook「通用项目目录传输」节。
11. **传输完成必须收尾（不留暴露面，2026-09-03 用户确认后执行）**：HTTP 服务绑 0.0.0.0 + 防火墙放行 = 局域网任何设备可访问，任务完成即无保留价值 → ① kill 后台进程（process kill）② 删防火墙规则（bat + UAC，同放行姿势，netsh delete rule）③ rm token 临时文件 + skills_share 目录 ④ 三重验证：防火墙规则查询无返回 + `netstat -ano | grep <端口>` 无监听 + 临时文件不存在。下次要传再开，2 分钟成本。风险叙述口径（用户会问"开着有风险吗"）：内容风险低（zip 无密钥）但暴露面没必要常驻；http.server 无认证只读，不会写入，不是入侵级风险，是"用完该关门的攻击面"。
12. **分享完成后给对端留一份"对端视角"身份说明（2026-09-03 牛来→妈妈实测）**：分享完 skill/memory 后，通过 A2A 让对端把「我是谁 / 对端是谁 / a2a 工具怎么用 / 排查 / 安全」写成本机 skill（妈妈存为 `skills/agent-mesh-mama/SKILL.md`）——**只写对端自己视角，不含本机（牛来侧）的 .env/config 细节**；派活方信息（谁 24/7、重活派给谁）要写清，对端以后接活/查档不靠问。文件级验证姿势：让对端贴 `ls -la <路径>` + SKILL.md 前 6 行（frontmatter）原文，字节数 + frontmatter 吻合才算落盘（别只信"已保存"一句话）。

