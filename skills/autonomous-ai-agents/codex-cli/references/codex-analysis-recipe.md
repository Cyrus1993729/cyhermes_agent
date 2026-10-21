# 经 Codex(GPT-5.6-Sol)做长文本深度分析配方(2026-09-08 实测:瑞幸vs爱回收选址前景)

适用于:用户要一份有深度、结合真实业务数据的对比/前景/方案分析(非图片、非审查 findings 结构)。

## 流程骨架
1. **先 web_search 抓真实数据**(财报、门店数、战略、竞品、风险),越多越好;数据归我整理成段落
2. **写 prompt.txt**(UTF-8),角色设定 + 明确任务 + 补充信息(用户口述的关键点,如岗位性质/汇报线,要单列并注明权重)+ 已搜集数据 + 要求
3. **后台运行避免前台 timeout**(长分析 1-4 分钟,前台 420s 会被杀):
```bash
mkdir -p /c/Users/Administrator/<task_dir> && cd /c/Users/Administrator/<task_dir>
export HTTP_PROXY=http://127.0.0.1:10808 HTTPS_PROXY=http://127.0.0.1:10808
CODEX="$LOCALAPPDATA/OpenAI/Codex/bin/$(ls "$LOCALAPPDATA/OpenAI/Codex/bin" | head -1)/codex.exe"
"$CODEX" exec --skip-git-repo-check --sandbox read-only -C "C:/Users/Administrator/<task_dir>" \
  -c 'model="gpt-5.6-sol"' < prompt.txt > codex_out.txt 2>&1   # background=true notify=true
```
4. **从 codex_out.txt 提取正文**:ANSI 清洗(re.sub ANSI + 控制字符)→ `
codex` 后到第一个 `tokens used` 之前的正文;codex_out 常把整段分析重复两次,取第一个 `tokens used` 前为止,`body[body.find('# ') :]` 去起手杂质,存 analysis.md
5. **通读全文再交付**(quality check),交付时 MEDIA: 附 .md 文件路径

## 分析 prompt 关键要素
- 角色:深耕零售/组织人力等对应领域的资深顾问
- 任务逐条列清(不并作一段);用户补充信息单独给并注明"务必纳入并给权重"
- 已搜集数据按公司分块,标注数字+来源方向;**明确告诉它"数据可能不精确,引用时注意,如有错误请校正"**
- 输出要求:排序论证链(因为…所以…)、对不确定处标"待验证"、要立场和可执行建议(结论金句收尾)、禁正确的废话

## 核心发现:GPT-5.6-Sol 会主动校正你的二手数据
- 本会话我喂的 3 处数据被它纠正:瑞幸证券已转场外OTC非纳斯达克、爱回收-京东协议2026年3月已修订续至2030年底(我给的旧信息是2027年底到期)、瑞幸Q2同店销售进一步降至-5.3%(我只有Q1的-0.1%)
- 它会在输出正文最前面以"另有 N 处数据需要校正"列出来,并附来源 URL
- → 策略价值:分析类任务里,与其我自己逐条交叉核验所有数据,**不如把候选数据+来源 URL 喂给 GPT-5.6-Sol,让它做校正**。比自己全量验证省力且覆盖面更广(它会抓出我没想到要查的点)
- 对用户画像:用户(2026-08-17)对价格/额度/事实类论断会凭直觉质疑且常对——交付前用 GPT-5.6 校正过一遍的数据更抗质疑

## 交付
- 正文直接内联输出完整分析(用户不要"见 terminal");分析长可分段贴
- 结尾说明:由 GPT-5.6-Sol 生成、基于我搜集的2026最新财报、它校正了哪些数据;附 analysis.md 路径
- 可主动提供后续:压到一页执行清单 / 按真实 offer 条件做针对性复核
