"""Tests for timeline_engine.py — ticket lifecycle reconstruction."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.sla.timeline_engine import (
    TicketTimeline,
    TimelineInterval,
    _deduplicate_events,
    _build_queue_intervals,
    _build_owner_intervals,
    _build_pending_intervals,
    _build_working_intervals,
    _merge_adjacent_intervals,
    build_timeline,
)


class TestTimelineInterval:
    def test_to_dict_with_end(self):
        iv = TimelineInterval(
            start=datetime(2026, 1, 1, 10, 0),
            end=datetime(2026, 1, 1, 11, 0),
            interval_type="queue",
            label="Support",
        )
        d = iv.to_dict()
        assert d["type"] == "queue"
        assert d["label"] == "Support"
        assert d["start"] == "2026-01-01T10:00:00"
        assert d["end"] == "2026-01-01T11:00:00"

    def test_to_dict_without_end(self):
        iv = TimelineInterval(
            start=datetime(2026, 1, 1, 10, 0),
            end=None,
            interval_type="queue",
            label="Support",
        )
        d = iv.to_dict()
        assert d["end"] is None

    def test_duration_seconds(self):
        iv = TimelineInterval(
            start=datetime(2026, 1, 1, 10, 0),
            end=datetime(2026, 1, 1, 11, 30),
            interval_type="queue",
            label="Support",
        )
        assert iv.duration_seconds() == 5400.0

    def test_duration_seconds_no_end(self):
        iv = TimelineInterval(
            start=datetime(2026, 1, 1, 10, 0),
            end=None,
            interval_type="queue",
            label="Support",
        )
        assert iv.duration_seconds() is None


class TestTicketTimeline:
    def test_initialization(self):
        tl = TicketTimeline(ticket_id=123, import_id="imp-1")
        assert tl.ticket_id == 123
        assert tl.import_id == "imp-1"
        assert tl.intervals == []
        assert tl.events == []


class TestDeduplicateEvents:
    def test_empty(self):
        assert _deduplicate_events([]) == []

    def test_single(self):
        events = [{"event_type": "Create", "new_state": "new"}]
        assert _deduplicate_events(events) == events

    def test_deduplicates_consecutive_duplicates(self):
        events = [
            {"event_type": "Create", "new_state": "new", "queue_name": "Q1", "owner_name": "A"},
            {"event_type": "Create", "new_state": "new", "queue_name": "Q1", "owner_name": "A"},
            {"event_type": "StateUpdate", "new_state": "open", "queue_name": "Q1", "owner_name": "A"},
        ]
        deduped = _deduplicate_events(events)
        assert len(deduped) == 2

    def test_keeps_different_events(self):
        events = [
            {"event_type": "Create", "new_state": "new", "queue_name": "Q1", "owner_name": None},
            {"event_type": "OwnerUpdate", "new_state": "new", "queue_name": "Q1", "owner_name": "A"},
        ]
        deduped = _deduplicate_events(events)
        assert len(deduped) == 2


class TestBuildQueueIntervals:
    def test_empty_events(self):
        assert _build_queue_intervals([]) == []

    def test_single_queue(self):
        events = [
            {"queue_name": "Support", "event_time": datetime(2026, 1, 1, 10, 0)},
        ]
        intervals = _build_queue_intervals(events)
        assert len(intervals) == 1
        assert intervals[0].label == "Support"

    def test_queue_transition(self):
        events = [
            {"queue_name": "Support", "event_time": datetime(2026, 1, 1, 10, 0)},
            {"queue_name": "Billing", "event_time": datetime(2026, 1, 1, 11, 0)},
        ]
        intervals = _build_queue_intervals(events)
        assert len(intervals) == 2
        assert intervals[0].label == "Support"
        assert intervals[1].label == "Billing"


class TestBuildOwnerIntervals:
    def test_empty_events(self):
        assert _build_owner_intervals([]) == []

    def test_owner_transition(self):
        events = [
            {"owner_name": "Alice", "new_owner": None, "event_time": datetime(2026, 1, 1, 10, 0)},
            {"owner_name": "Bob", "new_owner": None, "event_time": datetime(2026, 1, 1, 11, 0)},
        ]
        intervals = _build_owner_intervals(events)
        assert len(intervals) == 2

    def test_falls_back_to_new_owner(self):
        events = [
            {"owner_name": None, "new_owner": "Charlie", "event_time": datetime(2026, 1, 1, 10, 0)},
        ]
        intervals = _build_owner_intervals(events)
        assert len(intervals) == 1
        assert intervals[0].label == "Charlie"


class TestBuildPendingIntervals:
    def test_empty_events(self):
        assert _build_pending_intervals([]) == []

    def test_detects_pending_state(self):
        events = [
            {"state_name": "", "new_state": "pending auto", "event_type": "StateUpdate",
             "event_time": datetime(2026, 1, 1, 10, 0), "pending_until": None},
            {"state_name": "pending auto", "new_state": "open", "event_type": "StateUpdate",
             "event_time": datetime(2026, 1, 1, 12, 0), "pending_until": None},
        ]
        intervals = _build_pending_intervals(events)
        assert len(intervals) == 1
        assert intervals[0].type == "pending"

    def test_no_pending(self):
        events = [
            {"state_name": "", "new_state": "open", "event_type": "Create",
             "event_time": datetime(2026, 1, 1, 10, 0), "pending_until": None},
            {"state_name": "open", "new_state": "closed", "event_type": "StateUpdate",
             "event_time": datetime(2026, 1, 1, 12, 0), "pending_until": None},
        ]
        intervals = _build_pending_intervals(events)
        assert len(intervals) == 0


class TestBuildWorkingIntervals:
    def test_no_events(self):
        assert _build_working_intervals([], []) == []

    def test_no_pending(self):
        events = [
            {"event_time": datetime(2026, 1, 1, 10, 0)},
            {"event_time": datetime(2026, 1, 1, 12, 0)},
        ]
        intervals = _build_working_intervals(events, [])
        assert len(intervals) == 1
        assert intervals[0].label == "active"

    def test_with_pending(self):
        events = [
            {"event_time": datetime(2026, 1, 1, 10, 0)},
            {"event_time": datetime(2026, 1, 1, 16, 0)},
        ]
        pending = [
            TimelineInterval(
                start=datetime(2026, 1, 1, 11, 0),
                end=datetime(2026, 1, 1, 13, 0),
                interval_type="pending",
                label="pending auto",
            ),
        ]
        intervals = _build_working_intervals(events, pending)
        assert len(intervals) == 2  # before and after pending


class TestMergeAdjacentIntervals:
    def test_empty(self):
        assert _merge_adjacent_intervals([]) == []

    def test_merges_same_label(self):
        intervals = [
            TimelineInterval(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 11, 0), "queue", "Support"),
            TimelineInterval(datetime(2026, 1, 1, 11, 0), datetime(2026, 1, 1, 12, 0), "queue", "Support"),
        ]
        merged = _merge_adjacent_intervals(intervals)
        assert len(merged) == 1

    def test_keeps_different_labels(self):
        intervals = [
            TimelineInterval(datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 11, 0), "queue", "Support"),
            TimelineInterval(datetime(2026, 1, 1, 11, 0), datetime(2026, 1, 1, 12, 0), "queue", "Billing"),
        ]
        merged = _merge_adjacent_intervals(intervals)
        assert len(merged) == 2


class TestBuildTimeline:
    def test_no_events(self):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = []
        tl = build_timeline(mock_db, ticket_id=1, import_id="imp-1")
        assert tl.ticket_id == 1
        assert tl.events == []
        assert tl.intervals == []

    @patch("app.services.sla.timeline_engine._normalize_event")
    @patch("app.services.sla.timeline_engine._deduplicate_events")
    def test_with_events(self, mock_dedup, mock_norm):
        mock_db = MagicMock()
        mock_db.execute().mappings().all.return_value = [
            {"event_seq": 1, "event_time": datetime(2026, 1, 1, 10, 0), "event_type": "Create",
             "queue_name": "Support", "state_name": "new", "owner_name": None,
             "new_state": "new", "new_owner": None, "old_state": "", "old_owner": None,
             "src_queue": None, "dest_queue": None, "pending_until": None, "is_system_action": False},
        ]
        mock_norm.return_value = {"event_seq": 1, "event_time": datetime(2026, 1, 1, 10, 0),
                                   "event_type": "Create", "queue_name": "Support",
                                   "state_name": "new", "owner_name": None,
                                   "new_state": "new", "new_owner": None,
                                   "old_state": "", "old_owner": None,
                                   "src_queue": None, "dest_queue": None,
                                   "pending_until": None, "is_system_action": False}
        mock_dedup.return_value = [mock_norm.return_value]
        tl = build_timeline(mock_db, 1, "imp-1")
        assert tl.ticket_id == 1
