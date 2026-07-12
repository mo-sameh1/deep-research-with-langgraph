"""Date helpers used by date-aware research prompts."""

from __future__ import annotations

from datetime import datetime


def get_today_str() -> str:
    """Return today's date in the same readable style as the course notebooks."""

    return datetime.now().strftime("%a %b %-d, %Y")
