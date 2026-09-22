import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Resolved at import so a bad APP_TIMEZONE fails at startup, not on the first
# /summary request.
APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Kolkata"))


def today() -> date:
    """The calendar date for the user. The server's own clock/zone is irrelevant:
    at 01:00 IST on the 1st, UTC is still on the previous month."""
    return datetime.now(APP_TIMEZONE).date()


def seed_on_startup() -> bool:
    """Read at startup, not import, so tests can set it with monkeypatch."""
    return os.environ.get("SEED_ON_STARTUP", "false").strip().lower() == "true"
