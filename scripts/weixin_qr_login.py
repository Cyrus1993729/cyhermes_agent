"""
Run WeChat QR login flow and save credentials, then update config + .env.
"""
import asyncio
import os
import sys

# Add hermes-agent to path
HERMES_AGENT = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
sys.path.insert(0, HERMES_AGENT)

from hermes_constants import get_hermes_home
from gateway.platforms.weixin import qr_login
from gateway.config import Platform, PlatformConfig
import yaml

HERMES_HOME = str(get_hermes_home())
CONFIG_PATH = os.path.join(HERMES_HOME, "config.yaml")
ENV_PATH = os.path.join(HERMES_HOME, ".env")

async def main():
    print("=" * 50)
    print("WeChat / 微信 QR 扫码登录")
    print("=" * 50)

    creds = await qr_login(HERMES_HOME, timeout_seconds=480)

    if not creds:
        print("\n❌ 登录失败或超时，请重试。")
        return 1

    account_id = creds["account_id"]
    token = creds["token"]
    base_url = creds.get("base_url", "https://ilinkai.weixin.qq.com")

    print(f"\n✅ 登录成功!")
    print(f"   account_id: {account_id}")
    print(f"   base_url: {base_url}")

    # --- Update config.yaml ---
    print("\n📝 更新 config.yaml ...")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "platforms" not in config:
        config["platforms"] = {}

    config["platforms"]["weixin"] = {
        "enabled": True,
        "extra": {
            "account_id": account_id,
            "base_url": base_url,
            "dm_policy": "open",
            "group_policy": "disabled",
        },
        "token": token,
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"   ✅ config.yaml 已更新")

    # --- Update .env ---
    print("\n📝 更新 .env ...")
    env_lines = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    env_lines[key.strip()] = val.strip()

    env_lines["WEIXIN_ACCOUNT_ID"] = account_id
    env_lines["WEIXIN_TOKEN"] = token
    env_lines["WEIXIN_BASE_URL"] = base_url
    env_lines["WEIXIN_DM_POLICY"] = "open"

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for key, val in env_lines.items():
            f.write(f"{key}={val}\n")

    print(f"   ✅ .env 已更新")

    print("\n" + "=" * 50)
    print("🎉 微信接入配置完成!")
    print("   请重启 gateway 使配置生效:")
    print("   hermes gateway restart")
    print("=" * 50)
    return 0

if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消")
        rc = 1
    sys.exit(rc)
