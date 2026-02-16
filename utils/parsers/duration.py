import re
import time
from datetime import timedelta

from utils.cache.global_variables import TESTING_GA

# 30 minutes in seconds
MIN_GA_DURATION_SECONDS = 30 * 60


def parse_total_seconds(duration_str: str) -> int:
    """Parses a duration string and returns total seconds."""
    # Normalize for matching
    duration_str = duration_str.lower().replace(" ", "")

    # Match patterns like 4d, 4days, 4d12h, 4days12hours, 30m, 1h30m, 45s, etc.
    match = re.fullmatch(
        r"(?:(\d+)\s*d(?:ays?)?)?"  # days
        r"(?:(\d+)\s*h(?:ours?)?)?"  # hours
        r"(?:(\d+)\s*m(?:inutes?)?)?"  # minutes
        r"(?:(\d+)\s*s(?:econds?)?)?",  # seconds
        duration_str,
    )
    if not match:
        raise ValueError(
            "Invalid format. Examples: `3d`, `3 days`, `4d12h`, `4 days 12 hours`, `30m`, `1h30m`, `45s`, `1m30s`"
        )

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0
    seconds = int(match.group(4)) if match.group(4) else 0

    total_seconds = timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    ).total_seconds()
    return int(total_seconds)


def parse_total_duration(duration_str: str) -> int:
    """Parses a duration string and returns total seconds."""
    # Normalize for matching
    duration_str = duration_str.lower().replace(" ", "")

    # Match patterns like 4d, 4days, 4d12h, 4days12hours, 30m, 1h30m, 45s, etc.
    match = re.fullmatch(
        r"(?:(\d+)\s*d(?:ays?)?)?"  # days
        r"(?:(\d+)\s*h(?:ours?)?)?"  # hours
        r"(?:(\d+)\s*m(?:inutes?)?)?"  # minutes
        r"(?:(\d+)\s*s(?:econds?)?)?",  # seconds
        duration_str,
    )
    if not match:
        raise ValueError(
            "Invalid format. Examples: `3d`, `3 days`, `4d12h`, `4 days 12 hours`, `30m`, `1h30m`, `45s`, `1m30s`"
        )

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0
    minutes = int(match.group(3)) if match.group(3) else 0
    seconds = int(match.group(4)) if match.group(4) else 0

    total_seconds = timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    ).total_seconds()
    if total_seconds < MIN_GA_DURATION_SECONDS and not TESTING_GA:
        raise ValueError("Giveaway duration must be at least 30 minutes.")

    unix_end = int(time.time() + total_seconds)
    return int(unix_end)
