"""Tests for business_hours.py V2 — BusinessTimeEngine."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.sla.business_hours import (
    BusinessTimeEngine,
    calculate_business_seconds,
)


class TestBusinessTimeEngine:
    def test_default_is_not_24x7(self):
        engine = BusinessTimeEngine(None)
        assert not engine.is_24x7()

    def test_business_time_monday_10am(self):
        engine = BusinessTimeEngine(None)
        dt = datetime(2026, 1, 5, 10, 0)  # Monday
        assert engine.is_business_time(dt)

    def test_business_time_monday_8am(self):
        engine = BusinessTimeEngine(None)
        dt = datetime(2026, 1, 5, 8, 0)  # Monday before hours
        assert not engine.is_business_time(dt)

    def test_business_time_saturday(self):
        engine = BusinessTimeEngine(None)
        dt = datetime(2026, 1, 3, 10, 0)  # Saturday
        assert not engine.is_business_time(dt)

    def test_business_time_sunday(self):
        engine = BusinessTimeEngine(None)
        dt = datetime(2026, 1, 4, 10, 0)  # Sunday
        assert not engine.is_business_time(dt)

    def test_calculate_business_seconds_same_day(self):
        engine = BusinessTimeEngine(None)
        start = datetime(2026, 1, 5, 10, 0)  # Monday
        end = datetime(2026, 1, 5, 12, 0)
        seconds = engine.calculate_business_seconds(start, end)
        assert seconds == 7200  # 2 hours

    def test_calculate_business_seconds_overnight(self):
        engine = BusinessTimeEngine(None)
        start = datetime(2026, 1, 5, 16, 0)  # Monday 4pm
        end = datetime(2026, 1, 6, 10, 0)   # Tuesday 10am
        seconds = engine.calculate_business_seconds(start, end)
        assert seconds == 2 * 3600 + 1 * 3600  # 2h Mon + 1h Tue = 3h

    def test_calculate_business_seconds_weekend(self):
        engine = BusinessTimeEngine(None)
        start = datetime(2026, 1, 2, 16, 0)   # Friday 4pm
        end = datetime(2026, 1, 5, 10, 0)     # Monday 10am
        seconds = engine.calculate_business_seconds(start, end)
        assert seconds == 2 * 3600 + 1 * 3600  # 2h Fri + 1h Mon = 3h

    def test_calculate_business_seconds_24x7(self):
        mock_cal = MagicMock()
        mock_cal.is_24x7 = True
        mock_cal.timezone = "UTC"
        engine = BusinessTimeEngine(mock_cal)
        start = datetime(2026, 1, 3, 10, 0)  # Saturday
        end = datetime(2026, 1, 3, 12, 0)
        seconds = engine.calculate_business_seconds(start, end)
        assert seconds == 7200

    def test_calculate_business_seconds_with_holiday(self):
        mock_cal = MagicMock()
        mock_cal.is_24x7 = False
        mock_cal.timezone = "UTC"
        mock_cal.workdays = {
            "monday": True, "tuesday": True, "wednesday": True,
            "thursday": True, "friday": True,
            "saturday": False, "sunday": False,
        }
        mock_cal.holidays_json = [{"date": "2026-01-05"}]  # Monday is a holiday
        mock_cal.start_time = "09:00"
        mock_cal.end_time = "18:00"
        engine = BusinessTimeEngine(mock_cal)
        start = datetime(2026, 1, 5, 10, 0)  # Monday (holiday)
        end = datetime(2026, 1, 5, 12, 0)
        seconds = engine.calculate_business_seconds(start, end)
        assert seconds == 0  # Holiday, no business time

    def test_is_business_time_with_holiday(self):
        mock_cal = MagicMock()
        mock_cal.is_24x7 = False
        mock_cal.timezone = "UTC"
        mock_cal.workdays = {"monday": True}
        mock_cal.holidays_json = [{"date": "2026-01-05"}]
        engine = BusinessTimeEngine(mock_cal)
        dt = datetime(2026, 1, 5, 10, 0)  # Monday holiday
        assert not engine.is_business_time(dt)

    def test_legacy_calculate_business_seconds(self):
        config = None
        start = datetime(2026, 1, 5, 10, 0)
        end = datetime(2026, 1, 5, 12, 0)
        seconds = calculate_business_seconds(start, end, config)
        assert seconds == 7200

    def test_legacy_24x7_config(self):
        config = {"24_7": True}
        start = datetime(2026, 1, 3, 10, 0)  # Saturday
        end = datetime(2026, 1, 3, 12, 0)
        seconds = calculate_business_seconds(start, end, config)
        assert seconds == 7200
