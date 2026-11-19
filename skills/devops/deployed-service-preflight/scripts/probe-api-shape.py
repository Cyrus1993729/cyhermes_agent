#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只读探针：GET /api/v1/<route>，只报 status / 形状 / 条数 / 字段并集 / 字节数。

不打印 url、key、正文；不发 POST；不需要 PowerShell（与 probe-endpoint-shape.mjs 互补）。

用法：
    python probe-api-shape.py <connection.json|auto> <route> [route ...]
    python probe-api-shape.py auto "reminders/due" "reminders/due?calendarChanges=1&lead=18"

必需知识：缺 User-Agent 会被 Cloudflare 回 403 `error code: 1010`（与 key 无关），
所以下面的 UA 头是它的本职功能，不许删。
"""
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "dayflow-probe/1.0 (read-only shape probe)"

def find_conn(explicit):
    if explicit and explicit.lower() != "auto":
        return pathlib.Path(explicit)
    root = pathlib.Path.home() / "AppData/Local/DayflowHome/releases"
    cands = sorted(root.glob("*/runtime/.local/hermes-cloud-connection.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None

def proxy_of(conn):
    try:
        cfg = json.loads((conn.parent / "calendar-automation.json").read_text(encoding="utf-8-sig"))
        return (cfg.get("httpProxy") or "").strip() or None
    except Exception:
        return None

def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    conn = find_conn(argv[1])
    if not conn or not conn.exists():
        print(json.dumps({"error": "connection-file-not-found"}, ensure_ascii=False))
        return 1
    conf = json.loads(conn.read_text(encoding="utf-8-sig"))
    base, key = (conf.get("url") or "").rstrip("/"), conf.get("key") or ""
    if not base or not key:
        print(json.dumps({"error": "connection-file-incomplete"}, ensure_ascii=False))
        return 1
    proxy = proxy_of(conn)
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy \
        else [urllib.request.ProxyHandler({})]
    opener = urllib.request.build_opener(*handlers)

    out = {"connection": "located", "proxyUsed": bool(proxy), "probes": []}
    for route in argv[2:]:
        url = "%s/api/v1/%s" % (base, route.lstrip("/"))
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + key, "User-Agent": UA, "Accept": "application/json"})
        rec = {"route": route}
        try:
            with opener.open(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
                rec.update(status=r.status, bytes=len(body))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:120]
            except Exception:
                pass
            rec.update(status=e.code, bytes=len(body), hint=body.strip()[:80])
            out["probes"].append(rec)
            continue
        except Exception as e:
            rec.update(status=0, bytes=0, hint="%s" % type(e).__name__)
            out["probes"].append(rec)
            continue
        try:
            d = json.loads(body)
        except Exception:
            rec.update(shape="non-json")
            out["probes"].append(rec)
            continue
        if isinstance(d, list):
            items, rec["shape"] = d, "array"
        elif isinstance(d, dict):
            rec["shape"] = "object:" + ",".join(sorted(d)[:8])
            items = next((d[k] for k in ("candidates", "due", "reminders", "items")
                          if isinstance(d.get(k), list)), [])
        else:
            items, rec["shape"] = [], "scalar"
        rec["count"] = len(items)
        fields = set()
        for it in items:
            if isinstance(it, dict):
                fields |= set(it)
        rec["fieldUnion"] = sorted(fields)   # 只有字段名，不含值
        out["probes"].append(rec)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
