#!/usr/bin/env python3
"""A2A 双机连通探针：Agent Card + message/send 一键验证（2026-09-02 本机实测成形）。

用法:
    python a2a_probe.py <peer_url> <bearer_token> [timeout_s]

示例:
    python a2a_probe.py http://192.168.0.106:9900 5lVF...ud4 60

输出:
    1) GET  /.well-known/agent-card.json  —— 秒回=平台活着、鉴权对；name 字段=权威身份（改名后以此为准）
    2) POST message/send JSON-RPC 1.0     —— 7~35s 回=模型处理中（30s 超时会误报，给 60s+）；
                                            状态 TASK_STATE_COMPLETED 即通，回复文本打印出来

坑：
    - 30s 超时 ≠ 不通（对端模型调用慢）；用 60s+，或先看 card 秒回即平台正常
    - 对端开着 Clash 等代理时，本机 curl/urllib 会被本地 127.0.0.1:7897 劫持 LAN 直连 →
      必须无代理；本脚本探测对端 LAN IP 前确保不走 127.0.0.1 代理
"""
import json
import sys
import time
import urllib.request


def probe(base_url: str, token: str, text: str = "连通测试：请只回复'通'。", timeout: int = 60) -> None:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}

    # 1) Agent Card（身份权威来源）
    req = urllib.request.Request(
        base + "/.well-known/agent-card.json", headers=headers, method="GET"
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=8) as r:
        card = json.loads(r.read().decode("utf-8"))
    print(f"[{time.time()-t0:.1f}s] agent-card OK: name={card.get('name')!r}")

    # 2) message/send（真实往返）
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"text": text}],
                    "metadata": {"taskId": f"probe-{int(time.time())}"},
                }
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base + "/",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "A2A-Version": "1.0", **headers},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode("utf-8"))
    dt = time.time() - t0
    st = resp["result"]["status"]
    reply = ""
    parts = st.get("message", {}).get("parts", [])
    if parts and "text" in parts[0]:
        reply = parts[0]["text"]
    print(f"[{dt:.1f}s] message/send OK: state={st.get('state')} reply={reply[:200]!r}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    url, token = sys.argv[1], sys.argv[2]
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    probe(url, token, timeout=timeout)
