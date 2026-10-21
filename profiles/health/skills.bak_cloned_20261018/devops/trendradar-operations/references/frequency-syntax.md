# TrendRadar 关键词语法（frequency_words.txt）与防串领域设计

## 文件结构与解析规则（trendradar/core/frequency.py 实测确认）

```
[GLOBAL_FILTER]   # 排除区：命中任一即整条排除（优先级最高）
绯闻
...

[WORD_GROUPS]     # ⚠️ 必须存在的区段标记！漏了它 → 解析 0 组 → 所有标题匹配（静默失效）
[组名]
词1
+必须词
/正则|备选/ => 显示名
```

### 组匹配语义（matches_word_groups，frequency.py:291-307）
- 组内所有 `+词`（required）**必须全部出现**（AND）
- 组内普通词（normal）**至少一个出现**（OR）
- 两条件都满足才匹配该组
- **推论**：组合锁定（如"电商+关税"）必须独立成组（两行都是 +词，无普通词）；若与普通词混一组，普通词会变成"必须任一"条件，导致该组几乎无法命中

### 返回结构字段
- `display_name` = [组名]（方括号内文本）
- `group_key` = 组内所有词的空格拼接（验证断言别用 group_key 查组名）

## 防串领域三原则（跨境电商 1.0 设计验证）

### ① 通用词绝不单用（会串其他领域）
| 词 | 会串成什么 |
|---|---|
| 爆款 | 爆款游戏/剧集/手机 |
| 测评 | 数码/汽车测评 |
| 汇率 | 外汇宏观新闻 |
| 商标/知识产权/合规 | 全行业通用 |
| 关税 | 中美宏观贸易（非电商视角） |
| 亚马逊 | AWS/云计算新闻 |
| 沃尔玛 | 线下零售 |
| TikTok | 短视频娱乐 |

### ② 组合锁定用独立组（纯 +词）
```
[电商关税]
+电商
+关税
```
匹配"跨境电商遭遇美国关税冲击"✓；"美国对华加征关税"（无"电商"）不命中 ✓

### ③ 领域专属词放心单用
T86 / de minimis / 小额豁免 / 海外仓 / FBA / 跨境物流 / 结汇 / PingPong / 独立站 / Shopify / Temu / SHEIN / 虾皮 / 美客多 / Coupang

## 1.0 词组结构（v1.0，2026-08-07 用户确认）
13 组：美股市场 / 黄金贵金属 / 中国科技公司 / AI半导体 / 宏观经济 / 跨境电商平台 / 跨境电商市场 / 跨境电商环节 / 跨境电商政策 / 亚马逊卖家(+组合) / 沃尔玛电商(+组合) / 电商关税(+组合) / 跨境贸易摩擦(+组合)
GLOBAL_FILTER：绯闻/恋情/出轨/离婚/塌房/选秀/综艺/八卦/吃瓜/应援/LPL/KPL/英雄联盟

## 验证方法（改动后必做）
用项目 venv（`uv run python`，因依赖 trendradar 包）：
```python
from trendradar.core.frequency import load_frequency_words, matches_word_groups
groups, filters, global_filters = load_frequency_words(r"...\config\frequency_words.txt")
# 断言：13 组、display_name 命中、防串用例：
#  "亚马逊 AWS 推出新一代 AI 芯片" → 命中[AI半导体]、不命中[亚马逊卖家]
#  "跨境电商遭遇美国关税冲击" → 命中[电商关税]
#  "TikTok 短视频挑战赛走红" → 不命中
#  "明星绯闻曝光" → 全局过滤
```
注意：验证脚本必须用 `uv run python`（系统 python 缺 litellm）。
