# Research Report Summarization via Claude Code

Proven workflow for having Claude (Opus) read a financial research report and produce a structured Chinese summary suitable for WeChat sharing.

## Workflow

1. **Extract text** from PDF (PyPDF2, pdfplumber, or pdftotext)
2. **Save to temp file** → `~/tmp/<report_name>.txt`
3. **Pipe to Claude Opus** with the structured prompt below
4. **Save result** as `.md` on Desktop for MEDIA delivery
5. **Send as WeChat segments** in `(1/N)` format, each ≤1500 chars

## Claude Invocation

```bash
export HTTP_PROXY="http://127.0.0.1:7897" HTTPS_PROXY="http://127.0.0.1:7897"
cat /c/Users/Administrator/tmp/report.txt | claude -p '<prompt>' --model opus --max-turns 8 --output-format text --verbose
```

Always run the Opus smoke test first: `timeout 60 claude -p "回复OK" --model opus --max-turns 1`

## Prompt Template (Chinese Macro Report)

```
你是一名高盛宏观策略分析师。上面是一份[机构名称][日期]发布的《[报告标题]》研报全文。

请用中文撰写一份结构化的核心总结，格式参考：

---
# 标题

**来源**：[机构]，[日期] | 内部分享，仅供参考

---

## 一句话判断

[50字以内，最核心的结论]

---

## 关键数据一览

[用表格列出最重要的5-8个数据点，包括同比变化和对比基准]

---

## 核心发现

[3-4个最重要的发现，每段200-300字。要包括核心逻辑链，不只是罗列事实。]

---

## [机构名称]判断与政策展望

[GDP预测调整、后续判断、核心论点]

---

## 内部速记

[3-5条最值得跟踪的事项，每条一句话]

---

*本小结由 Claude (Opus) 基于[机构][日期]研报撰写，仅供内部分享。*

要求：
1. 数据和判断必须严格基于原文，不添加原文没有的内容
2. 语言精炼、直白、适合快速阅读
3. 表格用简洁的Markdown
4. 总字数控制在1500-2000字
```

## WeChat Delivery Format

- Use `（1/N）` numbering, each segment ≤1500 chars
- Split at natural section boundaries
- Include the full `.md` file as MEDIA attachment as backup

## Pitfalls

- **PDF text extraction can fail on image-heavy reports** — try multiple extractors (PyPDF2 → pdfplumber → pdftotext). If all fail, use OCR-via-vision on page screenshots.
- **Long reports may exceed Claude's stdin limit** — if the report is >20K chars, summarize each section first with Sonnet, then feed the compressed version to Opus for the final synthesis.
- **Opus cold-start latency** — first response can take 2-5 minutes. Always run the smoke test first, and use `--verbose` for progress visibility.
- **Non-Western character encoding** — some PDFs have garbled Chinese text. Try `pdftotext -layout -enc UTF-8` for best results.

## Validated Examples

- 2026-06-22: Goldman Sachs "China Matters: All About Tech" → 5-segment WeChat summary
- 2026-06-16: Goldman Sachs China May Activity Data → similar format
