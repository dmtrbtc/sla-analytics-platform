"""Tests for pause_engine.py V2 — compute_pause_segments_v2, calculate_active_time."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.sla.pause_engine import (
    PauseSegment,
    compute_pause_segments,
    compute_pause_segments_v2,
    calculate_active_time,
)


class TestPauseSegment:
    def test_to_dict_with_end(self):
        seg = PauseSegment(
            pause_start=datetime(2026, 1, 1, 10, 0),
            pause_end=datetime(2026, 1, 1, 12, 0),
            reason="pending_customer",
            trigger_event="pending auto",
        )
        d = seg.to_dict()
        assert d["reason"] == "pending_customer"
        assert d["trigger_event"] == "pending auto"

    def test_to_dict_without_end(self):
        seg = PauseSegment(
            pause_start=datetime(2026, 1, 1, 10, 0),
            pause_end=None,
            reason="pending_customer",
            trigger_event="pending auto",
        )
        d = seg.to_dict()
        assert d["pause_end"] is None


class TestComputePauseSegmentsV2:
    def test_empty_events(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = []
        segments = compute_pause_segments_v2(mock_db, 1, "imp-1")
        assert segments == []

    def test_no_pause(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 10, 0), "event_type": "Create",
             "state_name": "", "new_state": "new",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 12, 0), "event_type": "StateUpdate",
             "state_name": "new", "new_state": "closed",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
        ]
        segments = compute_pause_segments_v2(mock_db, 1, "imp-1")
        assert segments == []

    def test_detects_pending(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 10, 0), "event_type": "Create",
             "state_name": "", "new_state": "new",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 11, 0), "event_type": "StateUpdate",
             "state_name": "", "new_state": "pending auto",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 13, 0), "event_type": "StateUpdate",
             "state_name": "pending auto", "new_state": "open",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
        ]
        segments = compute_pause_segments_v2(mock_db, 1, "imp-1")
        assert len(segments) >= 1
        assert any(s.reason == "pending_customer" for s in segments)

    def test_skips_system_actions(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 10, 0), "event_type": "Create",
             "state_name": "", "new_state": "new",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": True},
            {"event_time": datetime(2026, 1, 1, 11, 0), "event_type": "StateUpdate",
             "state_name": "", "new_state": "pending auto",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": True},
        ]
        segments = compute_pause_segments_v2(mock_db, 1, "imp-1")
        assert segments == []

    def test_set_pending_time_event(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 10, 0), "event_type": "Create",
             "state_name": "", "new_state": "new",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 11, 0), "event_type": "SetPendingTime",
             "state_name": "", "new_state": "",
             "pending_until": datetime(2026, 1, 1, 12, 0), "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 13, 0), "event_type": "StateUpdate",
             "state_name": "", "new_state": "open",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
        ]
        segments = compute_pause_segments_v2(mock_db, 1, "imp-1")
        assert len(segments) == 1


class TestComputePauseSegmentsLegacy:
    def test_returns_tuples(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 11, 0), "event_type": "StateUpdate",
             "state_name": "", "new_state": "pending auto",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 13, 0), "event_type": "StateUpdate",
             "state_name": "pending auto", "new_state": "open",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
        ]
        segments = compute_pause_segments(mock_db, 1, "imp-1")
        assert len(segments) == 1
        assert isinstance(segments[0], tuple)
        assert len(segments[0]) == 2


class TestCalculateActiveTime:
    def test_no_pause(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = []
        result = calculate_active_time(
            mock_db, 1, "imp-1",
            [(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 12, 0))],
        )
        assert result["active_time_seconds"] == 7200
        assert result["paused_time_seconds"] == 0

    def test_full_pause(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_time": datetime(2026, 1, 1, 10, 30), "event_type": "StateUpdate",
             "state_name": "", "new_state": "pending auto",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
            {"event_time": datetime(2026, 1, 1, 11, 30), "event_type": "StateUpdate",
             "state_name": "pending auto", "new_state": "open",
             "pending_until": None, "new_owner": None,
             "dest_queue": None, "is_system_action": False},
        ]
        result = calculate_active_time(
            mock_db, 1, "imp-1",
            [(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 12, 0))],
        )
        assert result["active_time_seconds"] == 3600  # 1h active out of 2h
        assert result["paused_time_seconds"] == 3600  # 1h paused

    def test_business_hours(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = []
        result = calculate_active_time(
            mock_db, 1, "imp-1",
            [(datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 12, 0))],  # Monday
            business_hours_config={"monday": [{"start": "09:00", "end": "18:00"}]},
        )
        # Only 9-12 should count = 3h business time
        assert result["active_time_seconds"] == 10800

    def test_has_pause_audit(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = []
        result = calculate_active_time(
            mock_db, 1, "imp-1",
            [(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 12, 0))],
        )
        assert "pause_audit" in result
        assert isinstance(result["pause_audit"], list)
