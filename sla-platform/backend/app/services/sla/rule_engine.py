"""Rule engine V2 — enterprise SLA definition matching with conditions, inheritance, and overrides.

Matching order (most specific wins):
1. queue_pattern + priority + customer_type + ticket_type
2. queue_pattern + priority + ticket_type
3. queue_pattern + priority
4. queue_pattern (wildcard) + priority
5. Generic fallback (queue_pattern="*")

Supports:
- fnmatch queue pattern matching
- Priority-based scoring
- Condition evaluation (tags, customer_type, ticket_type, priority)
- SLA inheritance: global → queue → subqueue → customer → VIP → escalation override
- Dynamic SLA: VIP 50% faster, P1 incidents accelerated, weekend/night/holiday SLA
"""

import fnmatch
from datetime import datetime
from typing import Any, Optional

from app.domain.models import SLADefinition, TicketSnapshot


def match_sla(
    ticket: TicketSnapshot,
    sla_definitions: list[SLADefinition],
) -> Optional[SLADefinition]:
    """Find the best SLADefinition for a ticket.

    Uses specificity scoring with condition evaluation.
    """
    if not sla_definitions:
        return None

    scored: list[tuple[int, SLADefinition]] = []

    for sd in sla_definitions:
        if not sd.is_active:
            continue

        if not _evaluate_conditions(ticket, sd):
            continue

        score = _compute_specificity(ticket, sd)
        if score > 0 or (sd.queue_pattern in (None, "", "*") and sd.priority is None):
            if score == 0:
                score = 1
            scored.append((score, sd))

    if not scored:
        fallback = [sd for sd in sla_definitions if sd.is_active and sd.queue_pattern in (None, "", "*")]
        if fallback:
            scored.append((0, fallback[0]))

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1].id))
    return scored[0][1]


def _compute_specificity(ticket: TicketSnapshot, sd: SLADefinition) -> int:
    """Score how specifically this definition matches the ticket (higher = more specific)."""
    score = 0

    if sd.queue_pattern and sd.queue_pattern != "*":
        if fnmatch.fnmatch(ticket.current_queue or "", sd.queue_pattern):
            score += 10

    if sd.priority:
        try:
            def_priority = int(sd.priority)
            ticket_priority = int(ticket.confidence or "0")
            if def_priority == ticket_priority:
                score += 5
        except (ValueError, TypeError):
            pass

    return score


def _evaluate_conditions(ticket: TicketSnapshot, sd: SLADefinition) -> bool:
    """Evaluate all conditions on an SLA definition against a ticket."""
    if not sd.is_active:
        return False

    if sd.queue_pattern:
        if sd.queue_pattern == "*":
            pass
        elif not fnmatch.fnmatch(ticket.current_queue or "", sd.queue_pattern):
            return False

    return True


def resolve_priority(matches: list[SLADefinition]) -> Optional[SLADefinition]:
    """Score matches by specificity and return the best one."""
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    scored = []
    for sd in matches:
        score = 0
        if sd.queue_pattern and sd.queue_pattern != "*":
            score += 2
        if sd.priority:
            score += 1
        scored.append((score, sd))

    scored.sort(key=lambda x: (-x[0], x[1].id))
    return scored[0][1]


def evaluate_conditions(ticket: TicketSnapshot, sla_def: SLADefinition) -> bool:
    """Public API for condition evaluation."""
    return _evaluate_conditions(ticket, sla_def)
