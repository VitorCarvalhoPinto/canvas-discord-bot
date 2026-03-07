"""Configuration loaded from environment variables."""
import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _int_list(value: str) -> List[int]:
    if not value or not value.strip():
        return []
    return [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]


# Discord
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
# Optional: server (guild) ID for instant slash command sync. If set, commands appear in seconds; if not, global sync can take up to 1 hour.
GUILD_ID: int = int(os.getenv("GUILD_ID", "0") or "0")

# Canvas
CANVAS_TOKEN: str = os.getenv("CANVAS_TOKEN", "")
CANVAS_BASE_URL: str = os.getenv(
    "CANVAS_BASE_URL", "https://canvas.instructure.com/api/v1"
).rstrip("/")
CANVAS_COURSE_IDS: List[int] = _int_list(os.getenv("CANVAS_COURSE_IDS", ""))

# Discord channels
CHANNEL_NEWS_ID: int = int(os.getenv("CHANNEL_NEWS_ID", "0") or "0")
CHANNEL_PRAZOS_ID: int = int(os.getenv("CHANNEL_PRAZOS_ID", "0") or "0")

# Polling
POLL_INTERVAL_MINUTES: int = int(os.getenv("POLL_INTERVAL_MINUTES", "15") or "15")
REMINDER_DAYS_BEFORE: int = int(os.getenv("REMINDER_DAYS_BEFORE", "2") or "2")

# News: daily check at fixed time (e.g. 18:00)
NEWS_CHECK_HOUR: int = int(os.getenv("NEWS_CHECK_HOUR", "18") or "18")
NEWS_CHECK_MINUTE: int = int(os.getenv("NEWS_CHECK_MINUTE", "0") or "0")

# Cache: TTL in minutes for Canvas API responses
CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "120") or "120")
