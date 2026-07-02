# Claude Code Investment Research → PNG 输出

将深度投资研究（通过 Claude Code + serenity-skill/serenity-value 运行）的完整输出渲染为可分享的 PNG 信息图。

## 触发条件

- 用户请求 "用 serenity 深度调研"、"用 Claude 研究"、"生成研究长图"
- 用户引用 serenity-value/serenity-skill 研究任务

## 完整工作流

### 1. 将 prompt 写入临时文件

```
write_file(path="/tmp/serenity-prompt.txt", content="<完整中文研究 prompt>")
```

Prompt 模板（推荐使用文件模板 `~/.claude/skills/serenity-value/assets/prompt-template.md`，含硬约束 + 防漂移规则）：

**⚠️ 关键**：必须包含「硬约束」节 — 指定市场、产业链范围、明确排除项。缺少否定约束时 serenity-skill 可能默认跑偏（例如 A 股 AI 芯片 → 美股存储链）。
```
用 serenity-skill 和 serenity-value 深度调研 {市场} {产业链}。

## 硬约束
1. 仅限{市场}上市公司。禁止非目标市场标的。
2. 产业链范围：{产业链}。
3. 排除项：{排除项}，不在本次范围。
4. 缺优质标的直接说，不跨市场凑数。

## 研究要求
联网查公告、财报、问询函、互动易、招投标、环评/能评、专利、客户认证和财务质量。
先排产业链层级，再找 {N} 个最值得优先研究的标的。
说明卡住的环节、产业链位置、证据、排序理由、主要风险、📊 综合吸引力。
输出用中文。
```

### 2. 用 Opus 运行 Claude Code（后台）

```
terminal(
  background=true,
  notify_on_complete=true,
  timeout=600,
  command='export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897" && claude -p "$(cat /tmp/serenity-prompt.txt)" --model opus --max-turns 30 --allowedTools "Read,WebSearch,WebFetch,Bash" --output-format text --verbose 2>&1'
)
```

### 3. 等待完成后读取完整输出

```
process(action="log", session_id="<id>", limit=500)
```

### 4. 渲染为 HTML 信息图

创建深色主题 HTML 卡片（`#161b22` 背景、`#f0c040` 金色强调、`#c9d1d9` 文字），镜像研究结构：

- **Header**：标题、日期、数据源数量徽章
- **Section 1**：需求背景（"为什么是现在"）
- **Section 2**：产业链层级排序及层级标签
- **Section 3**：每只股票：名称/代码、瓶颈描述、证据（绿色）、排序理由、风险（红色）、`📊 卡脖子强度 | 估值 | 吸引力 ★` 摘要行
- **Section 4**：排除的股票及原因
- **Section 5**：什么可能推翻论点
- **Section 6**：下一步验证步骤
- **Section 7**：综合判断
- **Footer**：免责声明

样式规则：14px 基准字号、1.8 行高、PingFang SC 字体栈、边框卡片、无外部依赖。

### 5. 渲染 HTML → PNG（Playwright + Edge）

```python
from playwright.sync_api import sync_playwright

html_path = r"C:\Users\Administrator\Desktop\研究标题.html"
png_path = r"C:\Users\Administrator\Desktop\研究标题.png"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 800, "height": 600})
    page.goto(f"file:///{html_path.replace(chr(92), '/')}", wait_until="networkidle")
    full_height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": 800, "height": full_height})
    page.screenshot(path=png_path, full_page=True)
    browser.close()
```

依赖安装：
```bash
pip install playwright
# 无需 playwright install chromium — 使用 channel="msedge"
```

### 6. 交付给用户

在回复中包含 `MEDIA:C:\Users\Administrator\Desktop\研究标题.png`，或通过 `send_message` 发送。

## 注意事项

- **Opus 很慢**：首次响应可能需要 5-10 分钟。print 模式缓冲所有输出——完成前看不到进度。告诉用户正在运行，完成后交付。
- **不要未经允许切换模型**：中途不要从 Opus 切换到 Sonnet（反之亦然），除非用户明确同意。
- **Playwright Chromium 在国内下载失败**：使用 `channel="msedge"` 利用系统 Edge 浏览器，无需下载 Chromium。
- **内存接近上限**：长时间研究任务前检查内存使用情况——必要时压缩。
- **Prompt 文件**：始终先将 prompt 写入 `/tmp/serenity-prompt.txt`，避免中文 shell 引号问题。
- **所有 CSS/字体必须内联**：HTML 不能依赖外部 CDN。
- **文件路径反斜杠**：`\\` 必须替换为 `/` 才能用于 `file:///` URL。
- **`full_page=True`**：一次性截取完整长图。
