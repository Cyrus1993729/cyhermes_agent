# 模型版本核实：供应商说更新了，我这边同步没有

> 2026-10-20 实测定型。起因：DeepSeek 官网公告 V4.1 Flash 更新到 **V4.1-Flash-1017**，
> 用户问「我们走 OpenCode Go 网关调用的 `deepseek-v4.1-flash` 同步了吗」。

## 0. 先分清问题本质

**这是一个只能靠间接证据链回答的问题。** 三层证据强度：

| 层级 | 手段 | 能给出的结论 | 成本 |
|---|---|---|---|
| 硬证据 | 官方 API 的 `system_fingerprint` | 确定 | 1 次 API 调用 |
| 断供 | 网关元数据（`/models`、响应头） | **给不出**（实测全空） | 已试，别重复 |
| 旁证 | 行为指纹（逐字匹配率） | 倾向 | 10-20 次调用 |
| 外部 | 供应商公告 / 第三方实测 | 有时有 | 几次抓取 |

**优先级：先拿硬证据；拿不到就明确告诉用户"只能给倾向"，不要含糊其辞。**

---

## 1. `system_fingerprint` —— 唯一硬证据

### 是什么

OpenAI 兼容协议的响应体里有个 `system_fingerprint` 字段，由后端配置生成。
**后端换模型版本，这个值就会变。** 它是判断"到底是不是新后端"的官方指纹。

### 怎么取

发一个最小请求，读响应体：

```python
body = json.dumps({"model": model, "messages": [{"role": "user", "content": "hi"}],
                   "max_tokens": 1, "stream": False}).encode()
resp = urlopen(Request(url, data=body, headers=headers))
d = json.loads(resp.read().decode())
print(d.get("system_fingerprint"))
```

### DeepSeek 已知值

| 版本 | system_fingerprint |
|---|---|
| V4.1 Flash（1017 之前） | `aeb56401…` |
| **V4.1-Flash-1017** | **`e72d3c7f663d3e1383b00b3884cb4501`** |

2026-10-20 实测官方 `deepseek-flash` 返回 `e72d3c7f663d3e1383b00b3884cb4501` → **官方已全量切换**。

> 旁证来源：X 上 @finalbsd 2026-10-17 的观察——「1017 这个名直接调会被拒，
> `/models` 里也只有 `deepseek-flash` 和 `v4-pro` 两个。不过调 `deepseek-flash` 时
> `system_fingerprint` 从 `aeb56401` 变成 `e72d3c7f`，后端应该已经换了」。
> **官方文档不写 fingerprint 值，这类信息只能从第三方实测或自己比对历史得到。**

---

## 2. 网关为什么给不出 —— 别在这浪费时间

OpenCode Go 网关（`https://opencode.ai/zen/go/v1`）实测**三个通道全空**：

```
响应体 system_fingerprint : None
响应头                      : Date / Content-Type / x-zen-model / Server: cloudflare / CF-RAY
                             （x-zen-model 只回模型名，无版本）
GET /models 的 created    : 1792463815 → 解析出来就是「现在」
                             动态生成，不是模型真实创建时间
响应顶层字段              : ['choices','created','id','model','object','usage']
```

**结论：网关是纯转发层，不透传任何后端版本信号。这条路是死的。**

（顺带：`/models` 端口径可靠——2026-10-20 实拉 **37 个在线模型**，可用来核对我们配置引用的模型是否还在售。）

---

## 3. 行为指纹 —— 只能给倾向

### 设计要点（第一版做错了，这是修正后的）

❌ **错误设计**：用综合性/长回答 prompt 比对。措辞自由度太大，同后端也会措辞不同。
第一版 5 个长 prompt → 只有 2/5 完全一致，无法判断。

✅ **正确设计**：**单值短答案**（一个数 / 一个词），`temperature=0`，`max_tokens=40`。
输出空间极小，同后端几乎不可能分叉。

```python
PROMPTS = [
    "17 的平方是多少？只回答数字。",
    "中国的首都是哪里？只回答城市名。",
    "水的化学式是什么？只回答化学式。",
    "二进制 1011 转成十进制是多少？只回答数字。",
    "3 的 10 次方是多少？只回答数字。",
    "元素符号 Fe 代表哪种金属？只回答中文名称。",
]
# 比对前归一：去空白/标点/大小写
```

### 2026-10-20 实测结果

| 题 | 网关 | 官方 | 一致 |
|---|---|---|---|
| 17² | 289 | 289 | ✅ |
| 中国首都 | 北京 | 北京 | ✅ |
| 二进制 1011 | 11 | 11 | ✅ |
| 光合作用细胞器 | 叶绿体 | 叶绿体 | ✅ |
| 3^10 | 59049 | 59049 | ✅ |
| book 复数 | books | books | ✅ |
| Fe | 铁 | 铁 | ✅ |
| 水化学式 | H₂O | （空） | ❌（官方侧空返回，非真分叉） |

**9/10 逐字一致（90%）。**

### 🔴 必须对用户说清楚的限制

**高一致率 ≠ 证明是新版。** 旧版 V4.1 Flash 在这些基础事实上也会给出**完全相同**的答案。
没有旧版实例可比对时，行为指纹只能证明"是同一后端家族"，不能证明"是新版本"。

---

## 4. 供应商公告 —— OpenCode 的答案是「没有」

2026-10-20 四渠道全查（fresh curl，非 web_extract）：

| 页面 | 结果 |
|---|---|
| `opencode.ai/changelog` | 有页面（58KB），但**最新条目停在 10-16**（客户端 v2.0.32），**比 1017 发布早一天**；全是客户端功能改动，不涉及模型后端 |
| `opencode.ai/docs/go` → 跳 `/v2/docs/console/go/` | 模型列表只写「DeepSeek V4.1 Flash」，**无版本号、无 1017** |
| `opencode.ai/blog` | **404** |
| `opencode.ai/notes` | **404** |

**结论：OpenCode 作为转售/代理方，静默跟随上游，不发模型版本公告。**
拿确证只剩两条路：去 `anomalyco/opencode` 提 issue，或等 1017 的行为特征（agent 编码能力跃升）显现。

---

## 5. 实际结论模板（照抄改数字即可）

```
直接回答：{供应商} 官网没有任何 {版本} 公告，技术上也无法确证。

① 官方侧已确认：官方 deepseek-flash 的 system_fingerprint = e72d3c7f… = 1017 版（硬证据）
② 网关侧读不出：OpenCode 不透传 fingerprint，响应头和 /models 均无版本信息
③ 行为对比：短答案 9/10 逐字一致 → 同一后端家族，但不能证明是 1017（老版这些题也一样）

我的判断：大概率已同步（OpenCode 转售官方额度、价格也同步官方，官方 10/17 全量切换后
转售方自动跟随；模型名 deepseek-v4.1-flash 本身是「最新 V4.1 Flash」的别名而非版本锁定），
但没有硬证据。要确证只能去 anomalyco/opencode 提 issue，或观察 agent 编码表现。
```

---

## 附：现成脚本

`scripts/probe_model_version.py` —— 一次比对官方与网关的 `system_fingerprint`，
自动区分「已是新版 / 仍是旧版 / 拿不到」。直接改 `TARGETS` 即可复用到其他模型对。
