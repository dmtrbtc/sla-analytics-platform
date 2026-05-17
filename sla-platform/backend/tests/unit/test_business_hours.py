"""Unit tests for business_hours.py — schedule resolution, weekdays, custom configs."""

from datetime import datetime, timezone

from app.services.sla.business_hours import (
    _resolve_config,
    calculate_business_seconds,
    is_business_time,
)

# Reference dates (2025-01-06 is Monday)
MON_10AM = datetime(2025, 1, 6, 10, 0, 0)
MON_8AM = datetime(2025, 1, 6, 8, 0, 0)
MON_7PM = datetime(2025, 1, 6, 19, 0, 0)
MON_5PM = datetime(2025, 1, 6, 17, 0, 0)
MON_9AM = datetime(2025, 1, 6, 9, 0, 0)
TUE_10AM = datetime(2025, 1, 7, 10, 0, 0)
TUE_9AM = datetime(2025, 1, 7, 9, 0, 0)
FRI_5PM = datetime(2025, 1, 10, 17, 0, 0)
SAT_12PM = datetime(2025, 1, 11, 12, 0, 0)
SUN_12PM = datetime(2025, 1, 12, 12, 0, 0)


def test_is_business_time_monday_10am():
    assert is_business_time(MON_10AM) is True


def test_is_business_time_monday_8am():
    assert is_business_time(MON_8AM) is False


def test_is_business_time_monday_7pm():
    assert is_business_time(MON_7PM) is False


def test_is_business_time_saturday():
    assert is_business_time(SAT_12PM) is False


def test_is_business_time_sunday():
    assert is_business_time(SUN_12PM) is False


def test_is_business_time_24_7():
    config = {"24_7": True}
    assert is_business_time(SAT_12PM, config) is True
    assert is_business_time(SUN_12PM, config) is True
    assert is_business_time(MON_3AM := datetime(2025, 1, 6, 3, 0, 0), config) is True


def test_is_business_time_custom_schedule():
    config = {"monday": [{"start": "10:00", "end": "16:00"}]}
    assert is_business_time(MON_10AM, config) is True
    assert is_business_time(MON_9AM, config) is False
    assert is_business_time(MON_5PM, config) is False


def test_is_business_time_custom_multi_slot():
    config = {"monday": [{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "18:00"}]}
    assert is_business_time(datetime(2025, 1, 6, 11, 0, 0), config) is True
    assert is_business_time(datetime(2025, 1, 6, 12, 30, 0), config) is False
    assert is_business_time(datetime(2025, 1, 6, 14, 0, 0), config) is True


def test_is_business_time_empty_day():
    config = {"monday": []}
    assert is_business_time(MON_10AM, config) is False


def test_is_business_time_bad_slot():
    config = {"monday": [{"start": "invalid", "end": "18:00"}]}
    assert is_business_time(MON_10AM, config) is False


def test_calculate_business_seconds_same_day():
    result = calculate_business_seconds(MON_10AM, datetime(2025, 1, 6, 12, 0, 0))
    assert result == 7200


def test_calculate_business_seconds_overnight():
    result = calculate_business_seconds(MON_5PM, TUE_10AM)
    assert result == 7200


def test_calculate_business_seconds_weekend():
    result = calculate_business_seconds(FRI_5PM, datetime(2025, 1, 13, 10, 0, 0))
    assert result == 7200


def test_calculate_business_seconds_24_7():
    config = {"24_7": True}
    result = calculate_business_seconds(SAT_12PM, datetime(2025, 1, 11, 14, 0, 0), config)
    assert result == 7200


def test_calculate_business_seconds_outside_hours():
    result = calculate_business_seconds(MON_8AM, MON_9AM)
    assert result == 0


def test_calculate_business_seconds_spanning_week():
    """Mon 10am to next Mon 10am = 5 weekdays * 9 hours * 3600."""
    next_mon_10am = datetime(2025, 1, 13, 10, 0, 0)
    result = calculate_business_seconds(MON_10AM, next_mon_10am)
    assert result == 5 * 9 * 3600


def test_calculate_business_seconds_zero_duration():
    result = calculate_business_seconds(MON_10AM, MON_10AM)
    assert result == 0


def test_calculate_business_seconds_exact_slot_boundary():
    """Start at 9am, end at 6pm = 9 hours."""
    result = calculate_business_seconds(MON_9AM, MON_7PM.replace(hour=18, minute=0, second=0))
    assert result == 9 * 3600


def test_calculate_business_seconds_partial_hour():
    result = calculate_business_seconds(datetime(2025, 1, 6, 9, 30, 0), datetime(2025, 1, 6, 11, 15, 0))
    assert result == 6300


def test_calculate_business_seconds_custom_schedule():
    config = {"monday": [{"start": "10:00", "end": "16:00"}]}
    result = calculate_business_seconds(MON_9AM, MON_5PM, config)
    assert result == 6 * 3600


def test_resolve_config_none():
    result = _resolve_config(None)
    assert result is not None
    assert "monday" in result


def test_resolve_config_24_7():
    result = _resolve_config({"24_7": True})
    assert result is None


def test_resolve_config_empty():
    result = _resolve_config({})
    assert result is not None
    assert "monday" in result


def test_resolve_config_custom():
    config = {"saturday": [{"start": "10:00", "end": "14:00"}]}
    result = _resolve_config(config)
    assert result == config


def test_monday_boundary_8_59am():
    """1 minute before business hours."""
    assert is_business_time(datetime(2025, 1, 6, 8, 59, 0)) is False


def test_monday_boundary_9_00am():
    """Exactly at business hours start."""
    assert is_business_time(datetime(2025, 1, 6, 9, 0, 0)) is True


def test_monday_boundary_6_00pm():
    """Exactly at business hours end."""
    assert is_business_time(datetime(2025, 1, 6, 18, 0, 0)) is True


def test_monday_boundary_6_01pm():
    """1 minute after business hours end."""
    assert is_business_time(datetime(2025, 1, 6, 18, 1, 0)) is False


def test_friday_to_monday_multi_day():
    """Fri 5pm to Mon 10am = 1h Fri + 1h Mon = 7200."""
    next_mon_10am = datetime(2025, 1, 13, 10, 0, 0)
    result = calculate_business_seconds(FRI_5PM, next_mon_10am)
    assert result == 7200


def test_calculate_business_seconds_24_7_overnight():
    config = {"24_7": True}
    start = datetime(2025, 1, 11, 22, 0, 0)
    end = datetime(2025, 1, 12, 6, 0, 0)
    result = calculate_business_seconds(start, end, config)
    assert result == 8 * 3600
