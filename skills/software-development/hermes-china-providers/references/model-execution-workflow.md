# OpenCode 库模型执行任务工作流

## 触发条件
用户指定使用 OpenCode 库中的某个模型（如 kimi-k3、deepseek-v4-pro、qwen3.7-max）执行特定任务，而非默认模型。

## 5 种指定通道

| 通道 | 适用场景 | 示例 |
|---|---|---|
| 会话级 | 当前会话切换模型 | `/model kimi-k3` |
| cron级 | 定时任务指定模型 | cron 任务配置中指定 model 字段 |
| MoA级 | 混合智能体编排 | MoA 配置中为各层指定模型 |
| 脚本直连 | 一次性长任务、研究类任务 | curl 直连 `opencode.ai/zen/go/v1/chat/completions` |
| delegate_task | 子代理任务 | 子代理继承父模型或显式指定 |

## 脚本直连模式（推荐用于长任务）

```bash
# 1. 构造 payload
python - << 'PYEOF'
import json
payload = {
    "model": "kimi-k3",  # 指定模型
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 16000,
    "stream": True  # 必须流式，否则代理掐断
}
json.dump(payload, open("payload.json","w",encoding="utf-8"), ensure_ascii=False)
PYEOF

# 2. 从 ~/.env 读取 token
KEY=$(grep "^OPENCODE_GO_API_KEY=" ~/AppData/Local/hermes/.env | cut -d= -f2 | tr -d '\r')

# 3. 流式调用 + 重试
for i in 1 2 3; do
  curl -s -x http://127.0.0.1:7897 --max-time 900 \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -H "User-Agent: curl/8.0.0" \
    https://opencode.ai/zen/go/v1/chat/completions \
    --data-binary @payload.json > stream.txt && \
    [ -s stream.txt ] && echo "try$i ok size=$(stat -c%s stream.txt)" && break || \
    echo "try$i fail exit=$?"; sleep 5
done
```

## 长报告截断处理（finish_reason=length）

kimi-k3 等模型生成长报告时易触发 `finish_reason=length`（非 `stop`），必须自动续写：

```python
# 检查 finish_reason
def extract_content(path):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    parts, finish = [], None
    for line in lines:
        line = line.strip()
        if not line.startswith("data:"):
            continue
        d = line[5:].strip()
        if d == "[DONE]":
            break
        try:
            obj = json.loads(d)
            finish = obj.get("choices", [{}])[0].get("finish_reason")
            delta = obj.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                parts.append(delta["content"])
        except Exception:
            continue
    return "".join(parts), finish

content, finish = extract_content("stream.txt")
if finish == "length":
    # 自动续写：把已生成内容 + 续写指令喂回
    prompt = f"""你之前的报告在截断处被切断。以下是已生成内容，请从截断处继续，不要重复已写内容。
--- 已生成内容 ---
{content}
---
请续写。"""
    # 再次调用（max_tokens 可设为 8000）
```

## 坑与注意事项

### 1. 非流式请求被代理掐断
- **问题**：urllib/requests 非流式请求到 `opencode.ai` 时，代理（127.0.0.1:7897）会 `RemoteDisconnected`
- **解决**：必须用 `stream: True` + curl，或 Python httpx stream
- **影响范围**：qwen_review.py 的 L1 审查脚本也受此影响，需改用 curl 流式调用

### 2. SSL 错误 exit 35
- **问题**：curl 偶发 `exit 35`（SSL connect error / connection reset）
- **解决**：重试循环（最多 3 次，间隔 5s）
- **示例**：见上方脚本直连模式

### 3. 长报告生成超时（>600s）
- **问题**：kimi-k3 生成 6000+ 字报告需 5-10 分钟，前台 terminal 超时
- **解决**：`terminal(background=True, notify_on_complete=True)` + `process(action="wait")`
- **注意**：wait 最多 180s，但 notify_on_complete 会在完成时通知，不要轮询

### 4. 路径格式
- **问题**：Python pathlib 不识别 `/d/Workspace/` 格式
- **解决**：传 Windows 绝对路径 `D:\Workspace\...` 或先 `cd` 到目录用相对路径

### 5. L1 审查需完整上下文
- **问题**：qwen_review.py 只传交付物路径，L1 模型看不到 D1 数据包 / D3 归档证据 → 误判 FAIL
- **解决**：手动构造审查 prompt，把 contract + D1 + D2 + D3 证据一并传入，用 curl 流式调用 qwen3.7-max

## 模型能力与配额

| 模型 | 适合任务 | 单次 max_tokens | 备注 |
|---|---|---|---|
| kimi-k3 | 深度研究、长报告 | 16000（流式） | 生成慢（5-10min），易截断 |
| deepseek-v4-pro | 审查、分析 | 16000（流式） | 推理 token 消耗大 |
| qwen3.7-max | L1 审查、轻量分析 | 8000 | 快，适合审查 |
| deepseek-v4-flash | 交互、生成 | 8000 | 快，日常用 |

## 验证步骤

1. 检查 finish_reason 是否为 `stop`（非 `length`）
2. 检查 content 长度是否合理（kimi-k3 长报告通常 6000-8000 字）
3. 若 `length`，自动续写并拼接
4. 最终检查拼接后报告是否完整（有无截断残留如"存货 +36.6"无后续）
