
import asyncio, sys, os
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent")

print("1. importing...", flush=True)
from gateway.platforms.weixin import qr_login
from hermes_constants import get_hermes_home
print("2. imports ok", flush=True)

HERMES_HOME = str(get_hermes_home())
print(f"3. hermes_home={HERMES_HOME}", flush=True)

async def test():
    print("4. entering async", flush=True)
    try:
        result = await qr_login(HERMES_HOME, timeout_seconds=30)
        print(f"5. result={result}", flush=True)
    except Exception as e:
        print(f"5. ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

asyncio.run(test())
