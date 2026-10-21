#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地 A2A 假对端 (mock) —— 离线验证跨机修复/通信脚本，不必等真对端开机（2026-10-07 实测沉淀）。

用法:
  python mock_a2a_peer.py [port] [canned_reply]     # 起服务并打印捕获到的指令

    GET  /.well-known/agent-card.json  → {"name": "mock-peer"}
    POST / (JSON-RPC message/send)     → 捕获指令原文打到 stdout，回固定回复

验证姿势（被测脚本是模块常量时）：
  import importlib.util, sys
  spec = importlib.util.spec_from_file_location("m", r"C:/.../被测脚本.py")
  m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
  m.PEER_URL = "http://127.0.0.1:9911"     # 指到 mock
  m.PEER_IP  = "127.0.0.1"
  m.STATE_PATH = Path(r"C:/.../Temp/state_test.json")   # 用临时 state，别碰真文件
  sys.argv = ["x"]
  m.main()

  # 跑两轮验证幂等/去重；覆盖成功与失败两种 canned_reply。
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9911
REPLY = sys.argv[2] if len(sys.argv) > 2 else (
    "已完成。BASE_IP 改动前 → 改动后:\n"
    '  BASE_IP = "192.168.0.110"  →  BASE_IP = "192.168.0.113"\n'
    "并在告警分支末尾追加了把新 IP 写回 BASE_IP 的一行，已读回验证。"
)


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/.well-known/agent-card.json"):
            b = json.dumps({"name": "mock-peer"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n).decode("utf-8"))
        parts = req.get("params", {}).get("message", {}).get("parts", [])
        instr = parts[0].get("text", "") if parts else ""
        print(f"[mock] 收到指令 {len(instr)} 字符 → 回复: {REPLY[:60]!r}")
        b = json.dumps({
            "jsonrpc": "2.0", "id": req.get("id"),
            "result": {"status": {
                "state": "completed",
                "message": {"parts": [{"text": REPLY}]},
            }},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


if __name__ == "__main__":
    print(f"mock A2A peer on 127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), _H).serve_forever()
