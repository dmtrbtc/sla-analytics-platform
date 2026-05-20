"""SLA Forensic Attribution Engine V3.

Additive module — does not modify or replace existing SLA engine V2.
All forensic computations are derived from the same source-of-truth tables:
  - raw_events / ticket_events
  - queue_periods
  - ownership_periods
  - ticket_snapshots
  - sla_metrics (read-only consumers)

Public surface:
  - attribution_engine.ForensicAttributionEngine
  - inactivity_engine.InactivityEngine
  - queue_forensics.QueueForensicsService
  - owner_forensics.OwnerForensicsService
"""

from app.services.forensics.attribution_engine import ForensicAttributionEngine
from app.services.forensics.inactivity_engine import InactivityEngine
from app.services.forensics.queue_forensics import QueueForensicsService
from app.services.forensics.owner_forensics import OwnerForensicsService

__all__ = [
    "ForensicAttributionEngine",
    "InactivityEngine",
    "QueueForensicsService",
    "OwnerForensicsService",
]
