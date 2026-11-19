---
name: local-cli-client-ops
description: "Use when 调用本机部署的 node/python CLI 客户端做增删改查。"
version: 1.0.0
author: agent
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cli, node, json, local-deployment, api-client, ops]
    related_skills: [dayflow-personal-planner, hermes-windows-ops, local-service-deployment]
---

# 调用本机部署的原生 CLI 客户端

本机有多个「自部署服务 + 自带 CLI 客户端」的组合（Dayflow 日程 `home.mjs client ...`、
钉钉 `dws.exe`、TrendRadar 等）。共同形态：**原生可执行文件读 JSON 文件、
打 JSON 到 stdout、写操作要幂等键**。

本 skill 收**跨服务通用**的坑。服务专属规则看各自 skill
（如 `dayflow-personal-planner` 的字段/分类/提醒口径）。

---

## 一、🔴 stdout 可能是多行 JSON，不是单一个 JSON 值

```bash
node.exe home.mjs client items > items.json
```

文件内容实际是**两行**：

```json
[{"id":"...","title":"..."}, ...]
{"requestId":"","operation":"items","attempt":1,"durationMs":1807,"status":200,"recoverable":false}
```

第 1 行是业务数据，第 2 行是**诊断行**。整体 `json.load(fp)` 抛：

```
JSONDecodeError: Extra data: line 2 column 1
```

报错只给一个行号，很容易被误读成「数据坏了」。

→ **只解析第一行**（只有一行的旧版本上也正确）：

```python
obj = json.loads(open('items.json', encoding='utf-8').readline())
```

⚠️ 反过来也成立：**如果看到 stdout 里只有那行 `{"requestId":...}`，别把它当成接口返回内容**
——真正的数据已被它盖掉/截掉，换个文件重新接。

🔴 **不要用 `> f.json 2>&1` 收口**：诊断行还会往 stderr 再打一份，两路混进同一文件后
`readline()` 也不一定靠得住（行序取决于 flush 时机）。要么只重定向 stdout，要么用容错解析：

```python
import json
dec, i, objs = json.JSONDecoder(), 0, []
while i < len(raw):
    while i < len(raw) and raw[i].isspace(): i += 1
    if i >= len(raw): break
    o, i = dec.raw_decode(raw, i); objs.append(o)
items = next(o for o in objs if isinstance(o, list))
```

---

## 二、🔴 寻址必须用完整 ID，短 id 会报「不存在」

传 8 位截断 id（如 `bcd9a23a`）去 `patch` / `delete` / `execution`：

```
{"error":"事项不存在","details":null}   HTTP 404
```

**这看起来像记录被删了，其实是寻址失败。** 排查时先怀疑 id 截断，别先怀疑丢数据。

→ 一律从列表命令回读**完整** id（`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）再拿去写。
打印给用户看用短 id 没问题（好认），但**喂回 CLI 的必须是全长**。

---

## 三、写操作的四个固定动作

1. **幂等键**：`--request-id <稳定 UUID>`。重试必须复用**同一个键**（含 JSON 内容、对象 id、version）；
   换新键「再试试」可能重复写入。环境变量往往传不进去，只能走 flag。
2. **先回读版本号**：这类 API 的 `patch` 多要带当前 `version`，不带或传旧值 → `version_conflict`。
   顺序固定：`list` → 拿 id+version → `patch` → `list` 回读。
3. **写好 JSON 文件**：用 python 生成，`ensure_ascii=False`；否则中文落盘成 `\uXXXX`，
   服务端能读但人工核对一片乱码。
4. **回读才叫成功**：收到 200 不等于用户看到的状态对了，必须再 list 一次核对 status/version 再回话。

```python
import json
json.dump({'status':'completed','version':1,'notes':'用户原话…'},
          open('p.json','w',encoding='utf-8'), ensure_ascii=False)
```

---

## 四、超时与重试

- 这类客户端一次云端往返常 2–8 秒；**terminal 显式给 ≥120s 时限**，别用默认值。
- 只有可恢复传输错误 / 502 / 503 / 504 / 429 值得重试；400/401/403/404/409 不要重试。
- 超时后**不要说「保存失败」**——正确说法是「保存结果暂未确认」，
  然后用**原幂等键**重试或直接回读核对。

---

## 五、大输出别接 tail，会截断回执

后台跑 `... | tail -80` 收口时，**回执前半段被切掉**，拿到输出时已经少了一半条目
（本例 12 项午餐只看到后 5 项，只能回档案里补读）。

- 需要完整回执 → 别接 tail，落文件再 `read_file` 分段读。
- 用 `process(action='wait')` 等待时，进程运行期间 `output` 只有启动行
  （`bash: no job control in this shell`）—— **这是正常的**，不是没动静。

---

## 六、🔴 Windows 上「薄包装器」常缺 PATH 里的运行时

有些客户端不是直接跑 node，而是**包装器再 spawn 系统程序**。Dayflow 的
`runtime/scripts/hermes-local.mjs` 就是这样：win32 上它 spawn 裸 `pwsh` 去执行
`http-request.ps1`。PWSh7 只装在 `DayflowHome/tools/pwsh7/`、不在系统 PATH 时：

```
{"errorType":"runtime_missing","phase":"startup","durationMs":19}
{"error":"读取未完成，请稍后重试"}      退出码 1
```

**19ms 秒挂 + `phase:startup` + `runtime_missing` = 子进程拉不起来，不是接口/凭证/版本问题。**
修法是调用前把运行目录前置到 PATH（一行 export，不改系统环境、不改配置）：

```bash
export PATH="/c/Users/Administrator/AppData/Local/DayflowHome/tools/pwsh7:$PATH"
```

同理适用于任何自带 `tools/` 运行时的部署包（node/python/pwsh 一律先前置再跑）。

---

## 七、想「验证写链路但不改行为」时：同值 pin 法

只读验证走不通（GET 不覆盖写路径）时，用**写入一个与当前 effective 完全相同的值**，
让变更面只剩元数据。判定标准必须是「来源变了、行为没变」：

| 观察点 | 期望 |
|:--|:--|
| 目标项来源标记 | 跟随 → 独立（或反之） |
| 目标项实际生效值 | 与写入前**一模一样** |
| 其他项 + 全局默认 | 一字不变 |
| 全局版本号 | 恰好 +1 |

回读四条全中才算通过；任何一条不符先停，别继续叠加写入。

---

## 八、🔴 「修改」先对号入座；同步来源的记录改不了就去回源系统改

**先匹配，再写**：用户说「改一下明天的日程」并给一串时段时，先把当天条目全拉下来，
按 **日期 + 主题 + 时段重叠** 找对应项：对得上 → `patch` 改时间；对不上 → 才是 `create`。
默认全新建 = 重复条目，用户会当场发现。

**同步来源的记录是只读的**：`source` 是外部系统（钉钉日历等）同步来的条目，
标题/日期/时间一律被服务端锁死，`patch` 返回 **HTTP 400 + 业务文案**：

```json
{"error":"请到钉钉修改工作日程；这里可以记录完成情况和关联目标","details":null}
```

- `recoverable:false`，**重试无用、换 request-id 也无用**（不是网络/版本问题，别浪费时间排查）。
- 但 `status`（完成/取消）通常仍可本地改——锁的是「事实性字段」，不是「执行状态」。
- 字段锁粒度拿不准时，先用一条无关紧要的字段试，别拿用户真实日程做实验。

**被锁时的正确回应**（不能只说“改不了”就停）：
1. 同一条消息里**能做的其他写入照常做**——一条被挡不等于整批放弃。
2. **不擅自补建本地副本顶替**，会与同步条目时间重叠、双份显示。
3. 回执原文照实给用户，附上当天完整清单（标出被锁那条），再给两条明确选项：
   ① 他去源系统改（同步回来自动更新）；② 我建本地副本，并告知会重叠显示。
4. 只有用户选 ② 才建。

## 九、route 是常量的包装器：带参路由 / 查询参数只能自建探针

很多 CLI 包装器把 **route 写成常量 mapping**（Dayflow `hermes-client.mjs`：`due:['GET','reminders/due']`），
`args` 只喂给少数几个 op（`models-test-status`、`category-patch`、`confirm`）。
⇒ **查询参数根本发不出去**（`client due --foo` 被当未知参数或直接忽略）。别因为客户端不接受就断定服务端不支持。

判断「服务端到底支不支持某参数」用**独立只读探针**（现成：`scripts/probe-auth-get.mjs <releaseRoot> "<route>?<query>"`）：

- 只读 import 部署自带的 `runtime/scripts/http-request.mjs`，**别用裸 fetch**（win32 上边缘层挡 undici 指纹，回 403 HTML）。
- 复刻入口脚本的 `environment()`：`calendar-automation.json` 的 `pwshExe` 目录前置到 PATH，`httpProxy` 设成 `HTTP_PROXY`/`HTTPS_PROXY`；只前置本次进程环境，不改系统 PATH。
- 凭据只从私有连接文件读，**只输出 status / bodyKind / count / 字段名**，正文与密钥一句不打。

🔴 **「契约未上线」的长相不是 4xx**：把参数设成**非法值**（`?lead=abc`）或胡编一个（`?bogus=1`），
仍 200 ⇒ 服务端既不解析也不校验，只是恰好现在没数据。2026-11-18 Dayflow `/api/v1/reminders/due`
四种写法（无参 / `calendarChanges=1&lead=18` / `lead=abc` / `bogus=1`）全 200 空数组，凭这一组才敢判「契约未上线」。
反之非法值若 400，说明参数已被解析，可以继续验语义。

🔴 **别为了加参数去改 release 里的包装器**：`manifest.json` 的 sha256 会让 `verify`/`preflight`/`smoke`/`run` 全挂，
而 `client` 子命令不校验 → 症状是「查询读写照跑、定时同步静默死掉」（你只会看到 22:00 的活没了）。
要扩展就新增独立脚本，或走官方补丁包。

**服务端回执键 ≠ 本地去重键**：ack 要的是服务端给的 key（Dayflow 形如 `id:date:start:reminderMinutes`），
不是本地 `id|start|date`。两个都落库，否则「发成功但 ack 用错键」会重复提醒；且 lead 或时间一变服务端键就变
⇒ 改期必然二次提醒，任何「改期优先处理」的设计都要先处理这个键。

**白名单外的子命令要 stdin + 幂等键**：`hermes-local.mjs` 只对 `state/items/due/categories/category-delete/models/models-catalog/models-test-status` 免 stdin；
`ack` 这类写命令必须 `--json-file` + `--request-id`，否则报「请求必须是 JSON」/「写入前设置 DAYFLOW_REQUEST_ID」。

🔴 **「服务端已发布新版本」不等于「本地客户端已升级」**：对端说正式站已到 Sites43 时，先看本地
活动 release 目录名（实测仍 `releases/sites29-afdf902-home1`，`df_common.HOME_MJS` 指着它）。
两者不同时，所有「新契约」探测都只能打到旧客户端，回 `200 []` 要同时报三件事：本地 release 名、
参数是否被包装器丢弃、body 形状与条数。空数组 + 参数被丢 ⇒「真无候选 / 旧契约 / 参数没透传」
三种成因，**只读无法区分**，别写成「接口正常」。要给这种判读做旁证，先看同目录空数组、再拿非法值探
（见上一节）；验收流程与回执形状见 `deployed-service-preflight` 的「暂存补丁的验收」。

## 参考

- `references/reminders-due-ack-contract-2026-11.md` — Dayflow 提醒 due/ack 契约核查：客户端 mapping 能力边界、
  due 返回字段、df_watch 逐函数边界与 6 处适配点、缺口清单（2026-11-18 A2A 联调）。
- `scripts/probe-auth-get.mjs` — 只读探针：`node probe-auth-get.mjs <releaseRoot> "<route>?<query>"`，
  自动复刻 PATH/代理，stdout 只给 status/形状/字段名。
- `references/dayflow-client-2026-11.md` — Dayflow `home.mjs client` 实测证据：
  两行 JSON 原文、full-UUID 404 回执、钉钉字段锁粒度、批量写三条的完整命令。
- `references/hermes-local-wrapper-2026-11.md` — `runtime/scripts/hermes-local.mjs`（`--connection`
  入口）实测：pwsh PATH 坑原文、`models`/`models-set` stdin 规则、同型号 pin 的写读判据、脱敏汇报口径。
- `dayflow-personal-planner` — Dayflow 业务口径（字段、分类、提醒、钉钉源约束）。
- `deployed-service-preflight` — 暂存补丁验收（只跑已有测试/py_compile/哈希/备份可用性/只读 GET）与回执形状。
- `hermes-windows-ops` — MSYS 路径参数、杀进程、gateway 重启。
