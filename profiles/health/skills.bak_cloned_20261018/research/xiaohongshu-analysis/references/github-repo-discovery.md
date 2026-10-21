# 从 XHS 笔记发现 GitHub 项目的技巧

## 场景

XHS 笔记提及某个 GitHub 项目，但图片中没显示完整 URL（只展示了项目标题/内容）。

## 发现策略（按优先级，混合使用）

### 0. Vision 读帧（视频帖首选）✅

对于**视频帖**，提取帧后优先用 Vision 分析前几帧（frame_001, frame_003, frame_005 等），视频往往在开头展示 GitHub 项目页面截图——Vision 可直接读出 `username/repo`。这是最可靠的方式，比任何文本搜索都快且准确。

实战案例：视频封面只写了"Github开源！打破信息差壁垒"，无 repo 名。第一帧的 Vision 分析直接读出 `D4Vinci/Scrapling`。GitHub API 和 DuckDuckGo 的文本搜索反而没命中。

### 1. 文本搜索（图文帖 / Vision 失败后的后备）

### 1. GitHub API 搜索（首选，但中文内容常失败）

```python
GET https://api.github.com/search/repositories?q=<项目名>&sort=stars
```

⚠️ GitHub API 对中文短语搜索效果极差，常返回 0 结果（即使项目存在且高星）。
可能原因：GitHub 代码搜索偏向 code/commit 内容，对 repo 级别的中文全文索引不够完善。

### 2. DuckDuckGo 搜索（fallback，有间歇性空返回）⚠️

```python
GET https://html.duckduckgo.com/html/?q=<项目名 github>
```

解析 `uddg=` 参数提取真实 URL，再 URL 解码。

DDG HTML 端点对中文内容索引好且不设反爬，但有**间歇性空返回**问题——某些查询合法但返回 0 结果（2026-06-18 实测：3/5 的中文+英文混合查询返回空）。缓解策略：
- 换查询措辞重试（加/减 `github` 关键词、中英文交替）
- 如果 DDG 连续 3 次空返回，直接切 GitHub API 或直接用已知关键词盲搜 GitHub
- 对于小众项目（<100 stars），GitHub API 往往比 DDG 更可靠

### 3. Google 搜索（不可靠）

```python
GET https://www.google.com/search?q=<query>&hl=zh-CN
```

⚠️ Google 对非浏览器 User-Agent 常返回空白 JS 壳页面（`<noscript>` 重定向），无实际搜索结果。直接 HTTP 请求基本不可用。

### 4. Bing 搜索（效果中等）

偶尔有效，不如 DuckDuckGo 稳定。

## 实战案例

### 案例 1：中文项目名搜索
查找「中国人投资美股指南」这个项目：
- GitHub API：返回 0 结果 ❌
- Google：返回 JS 壳，无结果 ❌  
- Bing：无效 ❌
- **DuckDuckGo：找到 `zgwl/chinese-buy-us-stock-guide`** ✅

### 案例 2：ASR 转录名模糊匹配（2026-06-20）

视频 ASR 转录出 "Agent reach 国人作品"，GitHub 搜索 `agentreach` 只返回 0-5 星小项目。实际项目是 **Panniantong/Agent-Reach**（⭐35,449）。

**为什么会失败：**
- ASR 把 "Agent-Reach" 转录为 "Agent reach"（丢连字符+加空格）
- GitHub API 搜索 `agentreach` 要求精确匹配名称，找不到带连字符的版本
- `agent reach` 被当两个独立词模糊匹配，结果噪声大

**最终找到的方式：**
1. ❌ `agentreach in:name` → 0 结果（无连字符不匹配）
2. ❌ `小红书 in:readme` → GitHub API 不支持中文查询
3. ✅ `agent in:name stars:>7000` + Python 过滤描述含关键字的 → 遍历中找到 `Panniantong/Agent-Reach`，描述明确写了 "Bilibili, XiaoHongShu"

**教训：** 永远不要直接用 ASR 转录的英文专有名词搜 GitHub。先按功能描述缩小范围（高星 + 关键词过滤），再人工确认。这比反复改 query 重试 API 快得多。

## 找到项目后的标准流程

1. `GET /repos/{owner}/{repo}` 获取仓库元数据（stars、forks、文件列表）
2. `GET /repos/{owner}/{repo}/readme` 或 raw 端点获取 README（Base64 解码）⚠️ 见下方「批量拉取 README 的坑」
3. `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1` 获取完整文件树
4. `git clone --depth 1 <url>` 备份到本地

### ⚠️ 批量拉取 README 的常见陷阱

当一次分析涉及多个 GitHub 仓库时（如帖子推荐了 5 个项目），拉取 README 会遇到三个坑：

#### 坑 1：Contents API 返回的 Base64 含控制字符 → JSON 解析崩溃

`GET /repos/{owner}/{repo}/readme` 返回的 JSON 中 `content` 字段是 base64 编码。当 README 较大（>30KB 原文），curl stdout 在 ~20K 字符处会因控制字符导致 JSON 解析报 `Invalid control character at: line N column ~20000`。

**修复：不要用 `curl -s` 直接管道给 Python，先 `-o` 存文件再读。**

```bash
# ❌ 会崩溃（控制字符在 stdout 中）
resp = terminal('curl -s "https://api.github.com/repos/{repo}/readme"')
data = json.loads(resp['output'])  # → Invalid control character

# ✅ 先存磁盘
curl -s "https://api.github.com/repos/{repo}/contents/README.md" -o ~/readme.json
```

Python 读取时清理控制字符：
```python
import re, json, base64
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    raw = f.read()
raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw)
data = json.loads(raw)
content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
```

**Git blobs 端点同样有此问题**（`/git/blobs/{sha}`），修复方式相同。

#### 坑 2：raw.githubusercontent.com 间歇性返回空

某些仓库（如 `garrytan/gbrain`）的 raw 端点 `curl -sL "https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"` 返回空内容，但 Contents API 正常。

**后备策略：raw 端点失败 → 改用 Contents API 的 download_url 或直接 `/contents/README.md`。**

#### 坑 3：Windows MSYS 下 /tmp 路径 Python 不可见

在 Windows git-bash 中 `curl -o /tmp/file.json` 可以写文件，但 Python `open('/tmp/file.json')` 报 FileNotFoundError——bash 和 Python 看到的是不同的文件系统映射。

**修复：用 `~/` 路径（如 `~/readme.json`），bash 和 Python 都能访问。**

```bash
# ✅ 通用
curl -s "..." -o ~/readme.json
python -c "open(os.path.expanduser('~/readme.json'))..."
```
