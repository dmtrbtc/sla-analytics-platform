"""Business hours engine — supports 24/7, weekday-only, and custom schedules.

Extensible: can be swapped with calendar-based engine later without touching SLA core.
"""

from datetime import datetime, time, timedelta
from typing import Optional


WEEKDAY_SCHEDULE = {
    "monday":    [{"start": "09:00", "end": "18:00"}],
    "tuesday":   [{"start": "09:00", "end": "18:00"}],
    "wednesday": [{"start": "09:00", "end": "18:00"}],
    "thursday":  [{"start": "09:00", "end": "18:00"}],
    "friday":    [{"start": "09:00", "end": "18:00"}],
}


def _resolve_config(config: Optional[dict]) -> Optional[dict]:
    """Return the effective schedule dict, or None for 24/7."""
    if config is None:
        return WEEKDAY_SCHEDULE
    if config.get("24_7"):
        return None
    if not config:
        return WEEKDAY_SCHEDULE
    return config


def is_business_time(ts: datetime, config: Optional[dict] = None) -> bool:
    """True if *ts* falls within business hours."""
    schedule = _resolve_config(config)
    if schedule is None:
        return True
    day_name = ts.strftime("%A").lower()
    slots = schedule.get(day_name, [])
    t = ts.time()
    for slot in slots:
        try:
            start = time.fromisoformat(slot["start"])
            end = time.fromisoformat(slot["end"])
        except (KeyError, ValueError):
            continue
        if start <= t <= end:
            return True
    return False


def calculate_business_seconds(
    start: datetime,
    end: datetime,
    config: Optional[dict] = None,
) -> int:
    """Count seconds between *start* and *end* that fall within business hours."""
    schedule = _resolve_config(config)
    if schedule is None:
        return int((end - start).total_seconds())

    total = 0
    cursor = start
    one_day = timedelta(days=1)

    while cursor < end:
        day_name = cursor.strftime("%A").lower()
        slots = schedule.get(day_name, [])
        day_end = end if cursor.date() == end.date() else cursor.replace(hour=23, minute=59, second=59)

        if slots:
            for slot in slots:
                try:
                    ws = time.fromisoformat(slot["start"])
                    we = time.fromisoformat(slot["end"])
                except (KeyError, ValueError):
                    continue
                slot_start = cursor.replace(hour=ws.hour, minute=ws.minute, second=0)
                slot_end = cursor.replace(hour=we.hour, minute=we.minute, second=0)
                if cursor >= slot_end:
                    continue
                seg_start = max(cursor, slot_start)
                seg_end = min(slot_end, day_end)
                if seg_start < seg_end:
                    total += int((seg_end - seg_start).total_seconds())

        cursor = cursor.replace(hour=0, minute=0, second=0) + one_day

    return total
