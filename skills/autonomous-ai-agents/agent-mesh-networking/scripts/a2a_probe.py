#!/usr/bin/env python3
"""A2A 双机连通探针：Agent Card + message/send 一键验证（2026-09-02 成形；2026-10-07 修代理劫持）。

用法:
    python a2a_probe.py <peer_url> <bearer_token> [timeout_s] [--proxy]

示例:
    python a2a_probe.py http://192.168.0.113:9900 5lVF...ud4 60
    python a2a_probe.py http://192.168.0.113:9900 $TOK 60 --proxy   # 探非 LAN 地址时才加

输出:
    1) GET  /.well-known/agent-card.json  —— 秒回=平台活着、鉴权对；name 字段=权威身份（改名/换 IP 后以此为准）
    2) POST message/send JSON-RPC 1.0     —— 7~35s 回=模型处理中（30s 超时会误报，给 60s+）；
                                            状态 TASK_STATE_COMPLETED 即通，回复文本打印出来

坑（实测，务必照抄）:
    - 本机常驻 HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:10808 (v2rayN) 时，python 裸
      urllib.request.urlopen 打 LAN 对端会走代理 → 失败/超时。本脚本已内置
      ProxyHandler({}) 无代理 opener；手写探针必须照抄（curl 对应姿势 --noproxy '*'）。
      2026-10-07 实证：同一 A2A 报文裸 urlopen FAIL、无代理 opener 200 + 对端回执。
    - 30s 超时 != 不通（对端模型慢）；先看 card 是否秒回，card 通即平台正常。
    - 报错若返回 -32700 parse error，多半是本机 curl 内联中文 JSON 在 bash 传参中损坏，
      不是对端问题 —— 用 write_file 落盘 + curl --data-binary @file 重发。
    - 探测用途区分：新 IP 认身份时，card 的 name 必须等于对端名才算核验通过。
"""
import json
import sys
import time
import urllib.request

# 无代理 opener：LAN 直连的生命线（见文件头坑 1）
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def probe(base_url: str, token: str, text: str = "连通测试：请只回复'通'。",
          timeout: int = 60, use_proxy: bool = False) -> None:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    opener = urllib.request.urlopen if use_proxy else _NO_PROXY.open

    # 1) Agent Card（身份权威来源）
    req = urllib.request.Request(
        base + "/.well-known/agent-card.json", headers=headers, method="GET"
    )
    t0 = time.time()
    with opener(req, timeout=8) as r:
        card = json.loads(r.read().decode("utf-8"))
    print(f"[{time.time()-t0:.1f}s] agent-card OK: name={card.get('name')!r} url={card.get('url')!r}")

    # 2) message/send（真实往返）；老版本网关方法名是 SendMessage + role ROLE_USER，失败则回退
    for method, role in (("message/send", "user"), ("SendMessage", "ROLE_USER")):
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": {"message": {
                "messageId": f"probe-{int(time.time())}",
                "role": role,
                "parts": [{"text": text}],
            }},
        }).encode("utf-8")
        req = urllib.request.Request(
            base + "/", data=body, method="POST",
            headers={"Content-Type": "application/json", "A2A-Version": "1.0", **headers},
        )
        t0 = time.time()
        try:
            with opener(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"[{time.time()-t0:.1f}s] {method} FAIL: {type(e).__name__}: {e}")
            continue
        if "error" in resp:
            print(f"[{time.time()-t0:.1f}s] {method} error: {resp['error']}")
            continue
        task = resp.get("result", {}).get("task", resp.get("result", {}))
        st = task.get("status", {})
        reply = ""
        parts = st.get("message", {}).get("parts", [])
        if parts and "text" in parts[0]:
            reply = parts[0]["text"]
        print(f"[{time.time()-t0:.1f}s] {method} OK: state={st.get('state')} reply={reply[:200]!r}")
        return
    print("两侧方法名都失败：先确认 card 是否 200（card 通=平台活着）→ 再查 token / 无代理姿势")


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--proxy"]
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    url, token = argv[0], argv[1]
    timeout = int(argv[2]) if len(argv) > 2 else 60
    probe(url, token, timeout=timeout, use_proxy="--proxy" in sys.argv)
