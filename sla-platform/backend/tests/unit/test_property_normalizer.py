"""Property-based tests for normalizer_service.py — _build_normalized.

Uses hypothesis to verify invariants across a wide range of inputs.
"""

from datetime import datetime, timezone
from uuid import uuid4

from hypothesis import assume, given, settings, strategies as st
from hypothesis.strategies import composite

settings.register_profile("ci", max_examples=20)
settings.load_profile("ci")

from app.services.normalizer_service import NormalizerService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

event_names = st.sampled_from([
    "OwnerUpdate", "Move", "StateUpdate", "Lock", "Unlock",
    "SendAnswer", "EmailCustomer", "PhoneCallCustomer",
    "SetPendingTime", "Merged", "TitleUpdate", "PriorityUpdate",
    "EscalationSolutionTimeStart", "EscalationResponseTimeStop",
    "AddNote", "FollowUp",
])

owners = st.one_of(st.none(), st.just("root@localhost"), st.emails())
queues = st.one_of(st.none(), st.text(min_size=1, max_size=20))
states = st.one_of(st.none(), st.text(min_size=1, max_size=20))
timestamps = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2026, 12, 31),
)


@composite
def raw_event(draw):
    return {
        "ticket_number": draw(st.one_of(st.none(), st.text(max_size=20))),
        "event_time": draw(timestamps),
        "event_name": draw(event_names),
        "queue_name": draw(queues),
        "state_name": draw(states),
        "event_owner_name": draw(owners),
        "src_queue": draw(st.one_of(st.none(), st.text(max_size=20))),
        "dest_queue": draw(st.one_of(st.none(), st.text(max_size=20))),
        "old_state": draw(st.one_of(st.none(), st.text(max_size=20))),
        "new_state": draw(st.one_of(st.none(), st.text(max_size=20))),
        "new_owner": draw(st.one_of(st.none(), st.emails())),
        "pending_until": draw(st.one_of(st.none(), timestamps)),
        "duplicate_key": draw(st.text(max_size=50)),
        "event_raw_name": draw(st.text(max_size=50)),
        "id": draw(st.integers(min_value=1, max_value=999999)),
    }


raw_event_lists = st.lists(raw_event(), min_size=0, max_size=20)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_output_length_matches_input(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    assert len(result) == len(events)


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_event_seq_is_sequential(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for i, ev in enumerate(result, start=1):
        assert ev["event_seq"] == i


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_ticket_id_consistent(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for ev in result:
        assert ev["ticket_id"] == ticket_id


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_import_id_consistent(ticket_id, events):
    imp_id = uuid4()
    result = NormalizerService._build_normalized(ticket_id, events, imp_id)
    for ev in result:
        assert ev["import_id"] == imp_id


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_event_type_preserved(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for raw, norm in zip(events, result):
        assert norm["event_type"] == raw["event_name"]


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_is_system_action_computed(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for raw, norm in zip(events, result):
        owner = raw.get("event_owner_name")
        expected = owner is None or owner == "root@localhost"
        assert norm["is_system_action"] == expected


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_no_nan_or_inf_values(ticket_id, events):
    import math
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for ev in result:
        for v in ev.values():
            if isinstance(v, float):
                assert not (math.isnan(v) or math.isinf(v))


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_raw_event_id_carried(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for raw, norm in zip(events, result):
        assert norm["raw_event_id"] == raw["id"]


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_ticket_number_carried(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for raw, norm in zip(events, result):
        assert norm["ticket_number"] == raw.get("ticket_number")


@given(ticket_id=st.integers(min_value=1, max_value=99999), events=raw_event_lists)
def test_queue_name_carried(ticket_id, events):
    result = NormalizerService._build_normalized(ticket_id, events, uuid4())
    for raw, norm in zip(events, result):
        assert norm["queue_name"] == raw.get("queue_name")


@given(ticket_id=st.integers(min_value=1, max_value=99999))
def test_empty_events_empty_result(ticket_id):
    result = NormalizerService._build_normalized(ticket_id, [], uuid4())
    assert result == []
