"""Tests for excel_writer utility functions."""

from app.utils.excel_writer import format_duration, fmt_time_columns


class TestFormatDuration:
    def test_none(self):
        assert format_duration(None) == "0 sec"

    def test_zero(self):
        assert format_duration(0) == "0 sec"

    def test_seconds(self):
        assert format_duration(45) == "45 sec"
        assert format_duration(1) == "1 sec"
        assert format_duration(59) == "59 sec"

    def test_minutes(self):
        assert format_duration(60) == "1 min"
        assert format_duration(120) == "2 min"
        assert format_duration(3540) == "59 min"

    def test_hours_only(self):
        assert format_duration(3600) == "1 h"

    def test_hours_minutes(self):
        assert format_duration(3660) == "1 h 1 min"
        assert format_duration(7200) == "2 h"
        assert format_duration(7500) == "2 h 5 min"

    def test_large_values(self):
        assert format_duration(86400) == "24 h"
        assert format_duration(90000) == "25 h"

    def test_negative(self):
        assert format_duration(-100) == "0 sec"


class TestFmtTimeColumns:
    def test_none(self):
        assert fmt_time_columns(None) == ["", "", ""]

    def test_zero(self):
        assert fmt_time_columns(0) == [0, 0, 0]

    def test_seconds_only(self):
        result = fmt_time_columns(45)
        assert result[0] == 45
        assert result[1] == 0.75
        assert result[2] == 0.01

    def test_full_hour(self):
        result = fmt_time_columns(3600)
        assert result[0] == 3600
        assert result[1] == 60
        assert result[2] == 1

    def test_large(self):
        result = fmt_time_columns(93784)
        assert result[0] == 93784
        assert result[1] == 1563.07
        assert result[2] == 26.05
