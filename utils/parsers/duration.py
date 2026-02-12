import re
import time
from datetime import timedelta

def parse_total_seconds(duration_str: str) -> int:
    """Parses a duration string and returns total seconds."""
    # Normalize for matching
    duration_str = duration_str.lower().replace(" ", "")

    # Match patterns like 4d, 4days, 4d12h, 4days12hours, 30m, 1h30m, etc.
    match = re.fullmatch(
        r"(?:(\d+)\s*d(?:ays?)?)?"  # days
        r"(?:(\d+)\s*h(?:ours?)?)?"  # hours
        r"(?:(\d+)\s*m(?:inutes?)?)?",  # minutes
        duration_str,
    )
    if not match:
        raise ValueError(
            "Invalid format. Examples: `3d`, `3 days`, `4d12h`, `4 days 12 hours`, `30m`, `1h30m`"
        )

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0

    total_seconds = timedelta(days=days, hours=hours, minutes=minutes).total_seconds()
    return int(total_seconds)
