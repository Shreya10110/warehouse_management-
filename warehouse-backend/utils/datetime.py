from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current aware UTC time."""
    return datetime.now(timezone.utc)
