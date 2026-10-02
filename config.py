import os

from dotenv import load_dotenv

load_dotenv()


def _ids(name: str) -> set[int]:
    raw = os.getenv(name, "").replace(" ", "")
    return {int(x) for x in raw.split(",") if x.isdigit()}


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SELLAUTH_API_KEY = os.getenv("SELLAUTH_API_KEY")
SELLAUTH_SHOP_ID = os.getenv("SELLAUTH_SHOP_ID")
GUILD_ID = int(os.getenv("GUILD_ID") or 0) or None

OWNER_IDS = _ids("OWNER_IDS")
STAFF_IDS = _ids("STAFF_IDS")

# Low stock alerts (leave LOW_STOCK_CHANNEL_ID empty to disable)
LOW_STOCK_CHANNEL_ID = int(os.getenv("LOW_STOCK_CHANNEL_ID") or 0) or None
LOW_STOCK_THRESHOLD = int(os.getenv("LOW_STOCK_THRESHOLD") or 5)
LOW_STOCK_INTERVAL_MIN = int(os.getenv("LOW_STOCK_INTERVAL_MIN") or 15)

EMBED_COLOR = 0x5865F2
SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
