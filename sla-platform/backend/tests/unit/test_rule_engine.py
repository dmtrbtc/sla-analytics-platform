"""Unit tests for rule_engine.py — SLA matching, priority resolution, condition evaluation."""

from app.domain.models import SLADefinition, TicketSnapshot
from app.services.sla.rule_engine import evaluate_conditions, match_sla, resolve_priority


def _sla(**overrides):
    defaults = dict(
        id=1, name="Test SLA", queue_pattern="*", priority=None,
        response_target_seconds=3600, resolution_target_seconds=86400,
        pause_on_pending=True, business_hours_only=False,
        business_hours=None, is_active=True,
    )
    defaults.update(overrides)
    return SLADefinition(**defaults)


def _ticket(queue="Support", priority=None):
    return TicketSnapshot(
        ticket_id=1001, ticket_number="T-1001",
        current_queue=queue, current_state="open",
        created_at=None, updated_at=None,
        current_owner="agent", confidence="full",
        last_import_id=None, updated_at_ts=None,
    )


def test_match_sla_exact_queue():
    ticket = _ticket(queue="Support-Queue")
    defs = [_sla(id=1, queue_pattern="Support*", priority="3")]
    result = match_sla(ticket, defs)
    assert result is not None
    assert result.id == 1


def test_match_sla_no_match():
    ticket = _ticket(queue="Billing-Queue")
    defs = [_sla(id=1, queue_pattern="Support*")]
    result = match_sla(ticket, defs)
    assert result is None


def test_match_sla_fallback_wildcard():
    ticket = _ticket(queue="Billing-Queue")
    defs = [
        _sla(id=1, queue_pattern="Support*"),
        _sla(id=2, queue_pattern="*"),
    ]
    result = match_sla(ticket, defs)
    assert result is not None
    assert result.id == 2


def test_match_sla_most_specific_wins():
    ticket = _ticket(queue="Support-Premium", priority="1")
    defs = [
        _sla(id=1, queue_pattern="Support*", priority="1"),
        _sla(id=2, queue_pattern="Support*"),  # less specific
        _sla(id=3, queue_pattern="*"),
    ]
    result = match_sla(ticket, defs)
    assert result.id == 1


def test_match_sla_inactive_skipped():
    ticket = _ticket(queue="Support")
    defs = [
        _sla(id=1, queue_pattern="Support*", is_active=False),
        _sla(id=2, queue_pattern="*"),
    ]
    result = match_sla(ticket, defs)
    assert result.id == 2


def test_match_sla_none_when_empty():
    ticket = _ticket()
    result = match_sla(ticket, [])
    assert result is None


def test_resolve_priority_single():
    defs = [_sla(id=1, queue_pattern="*")]
    result = resolve_priority(defs)
    assert result.id == 1


def test_resolve_priority_higher_score():
    defs = [
        _sla(id=1, queue_pattern="*", priority="3"),
        _sla(id=2, queue_pattern="Support*", priority="1"),
    ]
    result = resolve_priority(defs)
    # id=2: queue_pattern "Support*" != "*" (+2) + priority (+1) = 3
    # id=1: "*" queue (+0) + priority (+1) = 1
    assert result.id == 2


def test_resolve_priority_queue_pattern_without_priority():
    defs = [
        _sla(id=1, queue_pattern="*"),  # score 0
        _sla(id=2, queue_pattern="Support*"),  # score 2 (queue pattern specific)
    ]
    result = resolve_priority(defs)
    assert result.id == 2


def test_resolve_priority_empty():
    result = resolve_priority([])
    assert result is None


def test_resolve_priority_tie_breaks_by_id():
    defs = [
        _sla(id=5, queue_pattern="*", priority="3"),
        _sla(id=3, queue_pattern="*", priority="3"),
    ]
    result = resolve_priority(defs)
    assert result.id == 3


def test_evaluate_conditions_active():
    sla = _sla(queue_pattern="Support*")
    ticket = _ticket(queue="Support-Queue")
    assert evaluate_conditions(ticket, sla) is True


def test_evaluate_conditions_inactive():
    sla = _sla(is_active=False)
    ticket = _ticket()
    assert evaluate_conditions(ticket, sla) is False


def test_evaluate_conditions_queue_mismatch():
    sla = _sla(queue_pattern="Support*")
    ticket = _ticket(queue="Billing")
    assert evaluate_conditions(ticket, sla) is False


def test_evaluate_conditions_no_queue_pattern():
    sla = _sla(queue_pattern=None)
    ticket = _ticket()
    assert evaluate_conditions(ticket, sla) is True


def test_match_sla_priority_tie():
    """When scores are equal, lower id wins."""
    ticket = _ticket(queue="Support", priority="2")
    defs = [
        _sla(id=10, queue_pattern="Support", priority="2"),
        _sla(id=5, queue_pattern="Support", priority="2"),
    ]
    result = match_sla(ticket, defs)
    assert result.id == 5


def test_match_sla_queue_pattern_fnmatch():
    ticket = _ticket(queue="IT-Support-Level2")
    defs = [_sla(id=1, queue_pattern="IT-*")]
    result = match_sla(ticket, defs)
    assert result.id == 1
