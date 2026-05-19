"""Operational Intelligence analytics service.

All methods use SQL aggregation — no Python row-by-row loops.
"""

from datetime import datetime, timedelta

from sqlalchemy import select, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached
from app.domain.models import (
    QueuePeriod,
    SLAMetric,
    TicketEvent,
    TicketSnapshot,
)


class AnalyticsService:

    @staticmethod
    @cached(ttl=120, key_prefix="analytics", skip_args=1)
    async def get_overview(db: AsyncSession, days: int = 30) -> dict:
        """Operational intelligence KPI cards."""
        now = datetime.utcnow()
        since = now - timedelta(days=days)

        # Tickets at risk (non-breached with elapsed > 80% of target)
        tickets_at_risk = (
            await db.execute(
                select(func.count(func.distinct(SLAMetric.ticket_id)))
                .where(
                    SLAMetric.computed_at >= since,
                    SLAMetric.sla_breached == False,
                    SLAMetric.risk_level.in_(["high", "critical"]),
                )
            )
        ).scalar() or 0

        # Overloaded queues — queues where breach rate > 20%
        overloaded = (
            await db.execute(
                select(SLAMetric.queue_name)
                .where(
                    SLAMetric.computed_at >= since,
                    SLAMetric.queue_name.isnot(None),
                )
                .group_by(SLAMetric.queue_name)
                .having(
                    func.sum(case((SLAMetric.sla_breached == True, 1), else_=0)) * 1.0
                    / func.nullif(func.count(SLAMetric.id), 0) > 0.20
                )
            )
        ).all()
        overloaded_queues = len(overloaded)

        # Average queue wait time
        avg_wait = (
            await db.execute(
                select(func.avg(QueuePeriod.duration_seconds))
                .where(QueuePeriod.entered_at >= since)
            )
        ).scalar() or 0

        # Average reassignments per ticket
        reassign_data = (
            await db.execute(
                select(
                    func.count(TicketEvent.id) * 1.0
                    / func.nullif(func.count(func.distinct(TicketEvent.ticket_id)), 0)
                )
                .where(
                    TicketEvent.event_type == "OwnerUpdate",
                    TicketEvent.event_time >= since,
                )
            )
        ).scalar() or 0

        # Most problematic queue
        problematic = (
            await db.execute(
                select(
                    SLAMetric.queue_name,
                    func.sum(case((SLAMetric.sla_breached == True, 1), else_=0)).label("breaches"),
                )
                .where(
                    SLAMetric.computed_at >= since,
                    SLAMetric.queue_name.isnot(None),
                )
                .group_by(SLAMetric.queue_name)
                .order_by(text("breaches desc"))
                .limit(1)
            )
        ).first()
        most_problematic = problematic[0] if problematic else None

        # Unowned tickets
        unowned = (
            await db.execute(
                select(func.count(TicketSnapshot.ticket_id))
                .where(
                    TicketSnapshot.current_owner.is_(None),
                    TicketSnapshot.is_closed == False,
                )
            )
        ).scalar() or 0

        return {
            "tickets_at_risk": tickets_at_risk,
            "overloaded_queues": overloaded_queues,
            "avg_wait_seconds": round(float(avg_wait), 2) if avg_wait else 0.0,
            "avg_reassignments": round(float(reassign_data), 2) if reassign_data else 0.0,
            "most_problematic_queue": most_problematic,
            "unowned_tickets": unowned,
        }

    @staticmethod
    @cached(ttl=300, key_prefix="analytics", skip_args=1)
    async def get_queue_heatmap(db: AsyncSession, days: int = 30) -> list[dict]:
        """Queue heatmap data: breach count by (queue, weekday, hour)."""
        now = datetime.utcnow()
        since = now - timedelta(days=days)

        rows = (
            await db.execute(
                select(
                    SLAMetric.queue_name,
                    func.extract("dow", SLAMetric.computed_at).label("weekday"),
                    func.extract("hour", SLAMetric.computed_at).label("hour"),
                    func.count(SLAMetric.id).label("breach_count"),
                )
                .where(
                    SLAMetric.computed_at >= since,
                    SLAMetric.sla_breached == True,
                    SLAMetric.queue_name.isnot(None),
                )
                .group_by(
                    SLAMetric.queue_name,
                    text("weekday"),
                    text("hour"),
                )
                .order_by(SLAMetric.queue_name, text("weekday"), text("hour"))
            )
        ).all()

        return [
            {
                "queue": r[0],
                "weekday": int(r[1]),
                "hour": int(r[2]),
                "breach_count": r[3] or 0,
            }
            for r in rows
        ]

    @staticmethod
    @cached(ttl=120, key_prefix="analytics", skip_args=1)
    async def get_bottlenecks(db: AsyncSession, days: int = 90) -> list[dict]:
        """Bottleneck detection per queue."""
        now = datetime.utcnow()
        since = now - timedelta(days=days)

        # Avg wait per queue
        wait_rows = (
            await db.execute(
                select(
                    QueuePeriod.queue_name,
                    func.avg(QueuePeriod.duration_seconds).label("avg_wait"),
                )
                .where(
                    QueuePeriod.entered_at >= since,
                    QueuePeriod.queue_name.isnot(None),
                )
                .group_by(QueuePeriod.queue_name)
            )
        ).all()
        wait_map = {r[0]: float(r[1]) if r[1] else 0.0 for r in wait_rows}

        # Reassignments per queue
        reassign_rows = (
            await db.execute(
                select(
                    TicketEvent.dest_queue,
                    func.count(TicketEvent.id).label("reassignments"),
                )
                .where(
                    TicketEvent.event_type == "Move",
                    TicketEvent.event_time >= since,
                    TicketEvent.dest_queue.isnot(None),
                )
                .group_by(TicketEvent.dest_queue)
            )
        ).all()
        reassign_map = {r[0]: r[1] or 0 for r in reassign_rows}

        # Stalled tickets per queue (in queue > 48h)
        stalled_rows = (
            await db.execute(
                select(
                    QueuePeriod.queue_name,
                    func.count(func.distinct(QueuePeriod.ticket_id)).label("stalled"),
                )
                .where(
                    QueuePeriod.entered_at >= since,
                    QueuePeriod.queue_name.isnot(None),
                    QueuePeriod.duration_seconds > 172800,  # > 48 hours
                )
                .group_by(QueuePeriod.queue_name)
            )
        ).all()
        stalled_map = {r[0]: r[1] or 0 for r in stalled_rows}

        # SLA breach rate per queue
        breach_rows = (
            await db.execute(
                select(
                    SLAMetric.queue_name,
                    func.count(SLAMetric.id).label("total"),
                    func.sum(case((SLAMetric.sla_breached == True, 1), else_=0)).label("breached"),
                )
                .where(
                    SLAMetric.computed_at >= since,
                    SLAMetric.queue_name.isnot(None),
                )
                .group_by(SLAMetric.queue_name)
            )
        ).all()

        all_queues = set(wait_map.keys()) | set(reassign_map.keys()) | set(stalled_map.keys()) | {r[0] for r in breach_rows}

        results = []
        for q in sorted(all_queues):
            avg_wait = wait_map.get(q, 0.0)
            avg_reassign = reassign_map.get(q, 0)
            stalled = stalled_map.get(q, 0)

            match = [r for r in breach_rows if r[0] == q]
            if match:
                total = match[0][1] or 0
                breached = match[0][2] or 0
                sla_pct = round((1 - breached / total) * 100, 1) if total else 100.0
                breached_tickets = breached
            else:
                sla_pct = 100.0
                breached_tickets = 0

            risk_score = min(100, int(
                (min(avg_wait / 3600, 1) * 30) +
                (min(avg_reassign / 5, 1) * 25) +
                (min(stalled / 10, 1) * 25) +
                ((100 - sla_pct) / 100 * 20)
            ))

            results.append({
                "queue_name": q,
                "avg_wait_minutes": round(avg_wait / 60, 2) if avg_wait else 0.0,
                "avg_reassignments": avg_reassign,
                "stalled_tickets": stalled,
                "sla_pct": sla_pct,
                "breached_tickets": breached_tickets,
                "risk_score": risk_score,
            })

        return sorted(results, key=lambda r: r["risk_score"], reverse=True)

    @staticmethod
    async def get_sla_risks(db: AsyncSession, limit: int = 50) -> list[dict]:
        """Return tickets currently at high/critical risk."""
        rows = (
            await db.execute(
                select(
                    SLAMetric.ticket_id,
                    SLAMetric.queue_name,
                    SLAMetric.metric_name,
                    SLAMetric.metric_seconds,
                    SLAMetric.sla_risk_score,
                    SLAMetric.risk_level,
                    SLAMetric.risk_reason,
                    SLAMetric.computed_at,
                )
                .where(
                    SLAMetric.risk_level.in_(["high", "critical"]),
                    SLAMetric.sla_breached == False,
                )
                .order_by(SLAMetric.sla_risk_score.desc().nullslast())
                .limit(limit)
            )
        ).all()

        return [
            {
                "ticket_id": r[0],
                "queue_name": r[1],
                "metric_name": r[2],
                "elapsed_seconds": r[3] or 0,
                "risk_score": r[4] or 0,
                "risk_level": r[5] or "unknown",
                "risk_reason": r[6] or "",
            }
            for r in rows
        ]
