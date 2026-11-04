"""
TENDERLENS — Date Utilities
Handles robust date arithmetic, ISO parsing, calendar-day intervals, and validity bounds.

Calendar Inclusivity Specification:
- All dates are evaluated at the day level using UTC/local standardized ISO format YYYY-MM-DD.
- A period of N days from date D ends at D + N days (inclusive of the Nth day).
- Example: 90 days bid validity from 2026-01-01 ends on 2026-04-01. Any action on or before 2026-04-01 is valid.
- Bank Guarantee 45-day extension: BG must be valid up to at least D + 90 + 45 days.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Union


def now_iso() -> str:
    """Returns current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_iso() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_date(date_val: Union[str, date, datetime]) -> date:
    """Parses various date/datetime representations into a python date object."""
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    if not date_val:
        raise ValueError("Cannot parse empty date value")
    clean_str = str(date_val).strip()
    # Check if string has timestamp
    if "T" in clean_str:
        clean_str = clean_str.split("T")[0]
    elif " " in clean_str:
        clean_str = clean_str.split(" ")[0]
    return datetime.strptime(clean_str, "%Y-%m-%d").date()


def format_date(d: Union[date, datetime, str]) -> str:
    """Formats date as YYYY-MM-DD."""
    return parse_date(d).strftime("%Y-%m-%d")


def add_days(date_val: Union[str, date], days: int) -> str:
    """Adds N calendar days to a date and returns ISO string."""
    d = parse_date(date_val)
    res = d + timedelta(days=days)
    return res.strftime("%Y-%m-%d")


def days_between(start_date: Union[str, date], end_date: Union[str, date]) -> int:
    """Calculates calendar days between start and end (end - start)."""
    d1 = parse_date(start_date)
    d2 = parse_date(end_date)
    return (d2 - d1).days


def is_on_or_before(date_a: Union[str, date], date_b: Union[str, date]) -> bool:
    """Returns True if date_a <= date_b."""
    return parse_date(date_a) <= parse_date(date_b)


def is_on_or_after(date_a: Union[str, date], date_b: Union[str, date]) -> bool:
    """Returns True if date_a >= date_b."""
    return parse_date(date_a) >= parse_date(date_b)


def years_between(start_date: Union[str, date], end_date: Union[str, date]) -> float:
    """Computes years between two dates using 365.25 days per year."""
    days = days_between(start_date, end_date)
    return days / 365.25
