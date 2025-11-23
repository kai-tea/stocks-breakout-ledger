from __future__ import annotations
from datetime import datetime, date

# Accepted input shapes (seperated by spaces):
# "12 25 2020", "Dec 25 2020", "December 25 20"

_FORMATS: tuple[str, ...] = ("%m %d %Y", "%b %d %Y", "%B %d %Y")

def parse_date(text: str) -> date | None:
    """
    Parse 'month day year' into a datetime.date.
    Raises:
        ValueError if the string doesn't match an accepted format
        or is not a real calendar date.
    """
    s = " ".join(text.strip().split())  # normalize whitespace

    for fmt in _FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    return None

__all__ = ["parse_date"]