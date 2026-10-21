"""向 A2A 对端发送消息（长文本走文件，无代理 opener，token 不回显）。

用法:
    python a2a_send.py <消息.txt 路径> [peer_url 覆盖]

- 消息正文写进 .txt 再传路径：长中文/多段落塞命令行会遇引号与转义地狱。
- peer_url 可选：本机 config.yaml 里的 url 陈旧时，直接指到探活到的真实 IP。
  ⚠️ 这只影响本次发送，不改任何配置文件，因此不触发「改配置须用户同意」。
- 回执解析只用结构化字段：result.status.state / status.message.parts[*].text
- ⚠️ 对端回 "Provider authentication failed" = 对方模型凭据坏了（消息已送达），重试无用。
"""
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERMES = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.hermes")), "hermes")


def peer_conf(name, config_path=None):
    """从 config.yaml 读 a2a_agents.<name> 的 url/token。

    缩进实测：4 空格（peer 名）/ 6 空格（url、token）——按相对缩进解析，别写死。
    """
    cfg = config_path or os.path.join(HERMES, "config.yaml")
    lines = open(cfg, encoding="utf-8").read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.rstrip() == "a2a_agents:")

    base = None
    body = []
    for l in lines[start + 1:]:
        if not l.strip():
            continue
        cur = len(l) - len(l.lstrip())
        if base is None:
            base = cur
        if cur < base:
            break
        body.append(l)

    block = "\n".join(body)
    m = re.search(r"^\s{%d}\s*%s:\s*$((?:\n(?:.*))*)" % (base, re.escape(name)), block, re.M)
    if not m:
        found = re.findall(r"^\s{%d}(\S+):" % base, block, re.M)
        raise SystemExit(f"config.yaml 里找不到 a2a_agents.{name}；现有键：{found}")
    sub = m.group(1)
    url = re.search(r"url:\s*(\S+)", sub).group(1)
    tok = re.search(r"token:\s*(\S+)", sub).group(1).strip("'\"")
    return url.rstrip("/"), tok


def send(text, name="妈妈", timeout=280, url_override=None):
    url, tok = peer_conf(name)
    if url_override:
        url = url_override.rstrip("/")
        print(f"[url_override] 本次发往 {url}（config 未改）")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {"message": {
            "role": "user",
            "messageId": "msg-" + str(abs(hash(text))),
            "parts": [{"kind": "text", "text": text}],
        }},
    }
    req = urllib.request.Request(
        url + "/",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    # Clash/v2rayN 常驻代理会劫持 LAN 直连 → 必须用无代理 opener
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    d = json.loads(op.open(req, timeout=timeout).read().decode("utf-8"))

    res = d.get("result", {})
    state = res.get("status", {}).get("state")
    parts = [p.get("text") for p in res.get("status", {}).get("message", {}).get("parts", [])
             if p.get("kind") == "text"]
    return state, "\n".join(parts) or json.dumps(d, ensure_ascii=False)[:2000]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    text = open(sys.argv[1], encoding="utf-8").read()
    override = sys.argv[2] if len(sys.argv) > 2 else None
    state, reply = send(text, url_override=override)
    print("STATE:", state)
    print("REPLY:\n" + reply)
