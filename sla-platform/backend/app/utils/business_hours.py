"""Business hours engine supporting 24/7, weekday-only, and custom schedules."""

from datetime import datetime, timedelta, time, date
from typing import Optional


BUSINESS_HOURS_DEFAULT = {
    "monday":    [{"start": "09:00", "end": "18:00"}],
    "tuesday":   [{"start": "09:00", "end": "18:00"}],
    "wednesday": [{"start": "09:00", "end": "18:00"}],
    "thursday":  [{"start": "09:00", "end": "18:00"}],
    "friday":    [{"start": "09:00", "end": "18:00"}],
}


def _config_to_windows(config: dict) -> dict:
    """Normalise a business_hours config dict into day→list[(start_time, end_time)]."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    windows = {}
    for day in days:
        entries = config.get(day, [])
        if not entries:
            windows[day] = []
            continue
        pairs = []
        for e in entries:
            try:
                s = time.fromisoformat(e["start"])
                t = time.fromisoformat(e["end"])
            except (KeyError, ValueError):
                continue
            pairs.append((s, t))
        windows[day] = pairs
    return windows


def is_business_time(ts: datetime, config: Optional[dict] = None) -> bool:
    """Return True if *ts* falls within business hours according to *config*."""
    if config is None:
        config = {}
    is_247 = config.get("24_7", False)
    if is_247:
        return True

    if not config:
        config = BUSINESS_HOURS_DEFAULT

    windows = _config_to_windows(config)
    day_name = ts.strftime("%A").lower()
    day_windows = windows.get(day_name, [])
    if not day_windows:
        return False
    t = ts.time()
    for start, end in day_windows:
        if start <= t <= end:
            return True
    return False


def filter_business_seconds(
    start: datetime,
    end: datetime,
    config: Optional[dict] = None,
) -> int:
    """Return the number of business-seconds between *start* and *end*."""
    if config is None:
        config = {}
    is_247 = config.get("24_7", False)
    if is_247:
        return int((end - start).total_seconds())

    if not config:
        config = BUSINESS_HOURS_DEFAULT

    windows = _config_to_windows(config)
    total = 0
    cursor = start

    while cursor < end:
        day_name = cursor.strftime("%A").lower()
        day_windows = windows.get(day_name, [])
        day_end = datetime(end.year, end.month, end.day, 23, 59, 59)
        if cursor.date() == end.date():
            day_end = end

        if not day_windows:
            cursor = cursor.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue

        for ws, we in day_windows:
            slot_start = cursor.replace(hour=ws.hour, minute=ws.minute, second=0)
            slot_end = cursor.replace(hour=we.hour, minute=we.minute, second=0)

            if cursor >= slot_end:
                continue
            if cursor < slot_start:
                cursor = slot_start

            seg_end = min(slot_end, day_end)
            if cursor < seg_end:
                total += int((seg_end - cursor).total_seconds())
                cursor = seg_end

        if cursor.date() == start.date() or cursor < day_end:
            cursor = cursor.replace(hour=0, minute=0, second=0) + timedelta(days=1)

    return total


def calculate_effective_time(
    periods: list[tuple[datetime, datetime]],
    pause_rules: Optional[list[tuple[datetime, datetime]]] = None,
    business_hours_config: Optional[dict] = None,
) -> int:
    """Calculate total effective seconds from *periods*, subtracting *pause_rules*
    intervals and optionally filtering to business hours only."""
    if pause_rules is None:
        pause_rules = []

    all_seconds = 0
    for ps, pe in periods:
        seg_start = ps
        seg_end = pe
        if seg_start >= seg_end:
            continue

        for prs, pre in sorted(pause_rules):
            if prs >= seg_end or pre <= seg_start:
                continue
            if prs > seg_start:
                all_seconds += _business_or_raw(seg_start, prs, business_hours_config)
            seg_start = max(seg_start, pre)

        if seg_start < seg_end:
            all_seconds += _business_or_raw(seg_start, seg_end, business_hours_config)

    return all_seconds


def _business_or_raw(start: datetime, end: datetime, config: Optional[dict]) -> int:
    if config:
        return filter_business_seconds(start, end, config)
    return int((end - start).total_seconds())
