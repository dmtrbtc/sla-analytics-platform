"""Rule engine — matches SLA definitions to tickets and resolves overrides.

Extensible: supports queue_pattern (fnmatch), priority-based override,
and is ready for tags, customer_type, SLA level escalation.
"""

import fnmatch
from typing import Optional

from app.domain.models import SLADefinition, TicketSnapshot


def match_sla(ticket: TicketSnapshot, sla_definitions: list[SLADefinition]) -> Optional[SLADefinition]:
    """Find the *best* SLADefinition for *ticket*.

    Priority order:
        1. queue_pattern + priority match (most specific)
        2. queue_pattern match only (if priority unmatched)
        3. generic fallback (wildcard queue, no priority)
    """
    if not sla_definitions:
        return None

    matches: list[SLADefinition] = []
    for sd in sla_definitions:
        if not sd.is_active:
            continue
        if sd.queue_pattern and not fnmatch.fnmatch(ticket.current_queue or "", sd.queue_pattern):
            continue
        matches.append(sd)

    if not matches:
        matches = [sd for sd in sla_definitions if sd.is_active and
                   (not sd.queue_pattern or sd.queue_pattern == "*")]

    if not matches:
        return None

    return resolve_priority(matches)


def resolve_priority(matches: list[SLADefinition]) -> Optional[SLADefinition]:
    """Score matches by specificity and return the best one.

    Specificity score (higher = more specific):
        +2 if queue_pattern is not "*" and not None
        +1 if priority is not None

    Falls back to first match if no clear winner.
    """
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
    """Return True if *ticket* meets the conditions of *sla_def*.

    Future: add tag matching, customer_type checks, escalation level.
    """
    if not sla_def.is_active:
        return False
    if sla_def.queue_pattern and not fnmatch.fnmatch(ticket.current_queue or "", sla_def.queue_pattern):
        return False
    return True
