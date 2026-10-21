"""Telegram 补发通道：绕开 Hermes 网关直连 Bot API 发送消息数组。
用法: python tg_resend.py <msgs.json> [chat_id]
  msgs.json = JSON 字符串数组，每条作为一条消息发送（HTML 格式，& < > 需转义，每块 <=1500 字）。
  chat_id 缺省取 .env 的 TELEGRAM_HOME_CHANNEL。
凭证: 自动读 ~/AppData/Local/hermes/.env 的 TELEGRAM_BOT_TOKEN。
      config.yaml 的 telegram.token 是残缺占位符，直调 API 404，勿用。
代理: 默认 http://127.0.0.1:10808，可用 HERMES_TG_PROXY 覆盖。
重试: 10 次 / 4s 间隔——网络抖动期网关侧重试窗口(2次/~7s)不够，这里必须带足。
"""
import json, os, re, sys, time, urllib.parse, urllib.request

HOME = os.path.expanduser("~")
ENV = os.path.join(HOME, "AppData", "Local", "hermes", ".env")

def read_dotenv(key):
    if not os.path.exists(ENV):
        return None
    for ln in open(ENV, encoding="utf-8"):
        m = re.match(rf"^\s*{key}\s*=\s*['\"]?([^'\"]+)", ln)
        if m:
            return m.group(1).strip()
    return None

if len(sys.argv) < 2:
    raise SystemExit("用法: python tg_resend.py <msgs.json> [chat_id]")
chat = sys.argv[2] if len(sys.argv) > 2 else read_dotenv("TELEGRAM_HOME_CHANNEL")
tok = read_dotenv("TELEGRAM_BOT_TOKEN")
if not tok or not chat:
    raise SystemExit("token/chat 缺失：检查 .env 的 TELEGRAM_BOT_TOKEN / TELEGRAM_HOME_CHANNEL")
proxy = os.getenv("HERMES_TG_PROXY", "http://127.0.0.1:10808")

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": proxy, "https": proxy})
)
with open(sys.argv[1], encoding="utf-8") as f:
    msgs = json.load(f)

for i, text in enumerate(msgs, 1):
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    ok = False
    for a in range(10):
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{tok}/sendMessage", data=data)
            res = json.loads(opener.open(req, timeout=20).read().decode())
            print(f"chunk {i}: OK msg_id={res['result']['message_id']} len={len(text)}")
            ok = True
            break
        except Exception as e:
            print(f"chunk {i} attempt {a+1} failed: {type(e).__name__}: {e}")
            time.sleep(4)
    if not ok:
        print(f"chunk {i}: FAILED")
    time.sleep(1.5)
