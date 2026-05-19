"""Advanced analytics service — 10 analytical dimensions.

All methods use raw SQL aggregates for performance; no row-by-row loading.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    ImportSession,
    OwnershipPeriod,
    QueuePeriod,
    SLADefinition,
    SLAMetric,
    Team,
    TicketEvent,
    TicketSnapshot,
)


class AdvancedAnalytics:
    """Ten analytical dimensions for SLA platform intelligence."""

    @staticmethod
    async def sla_trend_forecast(db: AsyncSession, days: int = 90) -> dict:
        """1. SLA trend forecasting — 7-day moving average + linear projection."""
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    func.date_trunc("day", SLAMetric.computed_at).label("day"),
                    func.count(SLAMetric.id).label("total"),
                    func.sum(SLAMetric.sla_breached.cast(type(1))).label("breached"),
                )
                .where(SLAMetric.computed_at >= since)
                .group_by(text("day"))
                .order_by(text("day"))
            )
        ).all()

        daily = []
        for r in rows:
            total = r[1] or 0
            breached = r[2] or 0
            rate = round(breached / total * 100, 2) if total else 0.0
            daily.append({"date": str(r[0].date()), "total": total, "breached": breached, "breach_pct": rate})

        # 7-day moving average
        moving_avg = []
        for i in range(len(daily)):
            window = daily[max(0, i - 6): i + 1]
            avg = round(sum(d["breach_pct"] for d in window) / len(window), 2)
            moving_avg.append({"date": daily[i]["date"], "moving_avg_pct": avg})

        # Simple linear projection (next 7 days)
        if len(daily) >= 7:
            recent = [d["breach_pct"] for d in daily[-7:]]
            slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
            projection = []
            last_date = daily[-1]["date"]
            from datetime import datetime as dt
            last_dt = dt.strptime(last_date, "%Y-%m-%d")
            for i in range(1, 8):
                proj_dt = last_dt + timedelta(days=i)
                proj = round(recent[-1] + slope * i, 2)
                projection.append({"date": proj_dt.strftime("%Y-%m-%d"), "forecast_pct": max(0, proj)})
        else:
            projection = []

        return {
            "daily": daily,
            "moving_average": moving_avg,
            "forecast": projection,
            "current_breach_pct": daily[-1]["breach_pct"] if daily else 0.0,
            "trend_direction": "improving" if moving_avg and len(moving_avg) >= 2 and moving_avg[-1]["moving_avg_pct"] < moving_avg[-2]["moving_avg_pct"] else "worsening" if moving_avg and len(moving_avg) >= 2 else "stable",
        }

    @staticmethod
    async def queue_overload_prediction(db: AsyncSession, days: int = 30) -> list:
        """2. Queue overload — identify queues with high volume + slow resolution."""
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    QueuePeriod.queue_name,
                    func.count(func.distinct(QueuePeriod.ticket_id)).label("tickets"),
                    func.avg(QueuePeriod.duration_seconds).label("avg_duration"),
                    func.count(QueuePeriod.id).label("visits"),
                )
                .where(QueuePeriod.entered_at >= since)
                .group_by(QueuePeriod.queue_name)
                .order_by(func.count(func.distinct(QueuePeriod.ticket_id)).desc())
            )
        ).all()

        result = []
        for r in rows:
            avg_dur = round(float(r[2]), 2) if r[2] else 0.0
            tickets = r[1] or 0
            visits = r[3] or 0
            overload_score = round(tickets * (avg_dur / 3600) * (visits / max(tickets, 1)), 2)
            result.append({
                "queue_name": r[0],
                "tickets": tickets,
                "visits": visits,
                "avg_duration_seconds": avg_dur,
                "avg_duration_hours": round(avg_dur / 3600, 2),
                "overload_score": overload_score,
                "risk_level": "high" if overload_score > 100 else "medium" if overload_score > 30 else "low",
            })

        return sorted(result, key=lambda x: x["overload_score"], reverse=True)

    @staticmethod
    async def reassignment_analysis(db: AsyncSession, days: int = 90) -> dict:
        """3. Mean reassignment analysis — handoffs per ticket."""
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    TicketEvent.ticket_id,
                    func.count(TicketEvent.id).label("handoffs"),
                )
                .where(
                    TicketEvent.event_type == "OwnerUpdate",
                    TicketEvent.new_owner.isnot(None),
                    TicketEvent.old_owner.isnot(None),
                    TicketEvent.new_owner != TicketEvent.old_owner,
                    TicketEvent.event_time >= since,
                )
                .group_by(TicketEvent.ticket_id)
            )
        ).all()

        all_handoffs = [r[1] for r in rows]
        total_tickets = len(all_handoffs)
        avg_handoffs = round(sum(all_handoffs) / total_tickets, 2) if total_tickets else 0.0
        max_handoffs = max(all_handoffs) if all_handoffs else 0

        distribution = {}
        for h in all_handoffs:
            bucket = str(h) if h <= 5 else "6+"
            distribution[bucket] = distribution.get(bucket, 0) + 1

        return {
            "average_handoffs_per_ticket": avg_handoffs,
            "max_handoffs_per_ticket": max_handoffs,
            "tickets_with_reassignments": total_tickets,
            "distribution": distribution,
        }

    @staticmethod
    async def agent_workload(db: AsyncSession, days: int = 30) -> list:
        """4. Agent workload analytics — tickets per owner, avg time, open count."""
        since = datetime.utcnow() - timedelta(days=days)

        # Current open tickets per owner
        open_by_owner = (
            await db.execute(
                select(
                    TicketSnapshot.current_owner,
                    func.count(TicketSnapshot.ticket_id).label("open_tickets"),
                )
                .where(TicketSnapshot.is_closed == False, TicketSnapshot.current_owner.isnot(None))
                .group_by(TicketSnapshot.current_owner)
                .order_by(func.count(TicketSnapshot.ticket_id).desc())
            )
        ).all()
        open_map = {r[0]: r[1] for r in open_by_owner}

        # Ownership history
        owner_rows = (
            await db.execute(
                select(
                    OwnershipPeriod.owner,
                    func.count(func.distinct(OwnershipPeriod.ticket_id)).label("tickets_handled"),
                    func.avg(OwnershipPeriod.duration_seconds).label("avg_duration"),
                    func.sum(OwnershipPeriod.duration_seconds).label("total_duration"),
                )
                .where(
                    OwnershipPeriod.owner.isnot(None),
                    OwnershipPeriod.start_time >= since,
                )
                .group_by(OwnershipPeriod.owner)
                .order_by(func.count(func.distinct(OwnershipPeriod.ticket_id)).desc())
            )
        ).all()

        result = []
        for r in owner_rows:
            owner = r[0]
            result.append({
                "owner": owner,
                "open_tickets": open_map.get(owner, 0),
                "tickets_handled": r[1] or 0,
                "avg_ownership_seconds": round(float(r[2]), 2) if r[2] else 0.0,
                "total_active_seconds": round(float(r[3]), 2) if r[3] else 0.0,
            })

        return result

    @staticmethod
    async def top_problematic_queues(db: AsyncSession, days: int = 90) -> list:
        """5. Top problematic queues — highest breach rate, slowest resolution."""
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            await db.execute(
                select(
                    SLAMetric.queue_name,
                    func.count(SLAMetric.id).label("total"),
                    func.sum(SLAMetric.sla_breached.cast(type(1))).label("breached"),
                    func.avg(SLAMetric.metric_seconds).label("avg_seconds"),
                )
                .where(SLAMetric.queue_name.isnot(None), SLAMetric.computed_at >= since)
                .group_by(SLAMetric.queue_name)
                .having(func.count(SLAMetric.id) >= 5)
                .order_by(func.sum(SLAMetric.sla_breached.cast(type(1))).desc())
            )
        ).all()

        result = []
        for r in rows:
            total = r[1] or 0
            breached = r[2] or 0
            rate = round(breached / total * 100, 2) if total else 0.0
            result.append({
                "queue_name": r[0],
                "total_metrics": total,
                "breached": breached,
                "breach_pct": rate,
                "avg_metric_seconds": round(float(r[3]), 2) if r[3] else 0.0,
            })

        return sorted(result, key=lambda x: x["breach_pct"], reverse=True)

    @staticmethod
    async def mttr_mtta(db: AsyncSession, days: int = 90, by_queue: Optional[str] = None) -> dict:
        """6. MTTR / MTTA — Mean Time To Resolve / Respond."""
        since = datetime.utcnow() - timedelta(days=days)

        base = select(SLAMetric).where(SLAMetric.computed_at >= since, SLAMetric.metric_seconds.isnot(None))
        if by_queue:
            base = base.where(SLAMetric.queue_name == by_queue)

        async def _stat(name: str):
            q = (
                select(
                    func.avg(SLAMetric.metric_seconds).label("avg"),
                    func.percentile_cont(0.5).within_group(SLAMetric.metric_seconds).label("median"),
                    func.min(SLAMetric.metric_seconds).label("min"),
                    func.max(SLAMetric.metric_seconds).label("max"),
                    func.count(SLAMetric.id).label("count"),
                )
                .where(
                    SLAMetric.metric_name == name,
                    SLAMetric.metric_seconds.isnot(None),
                    SLAMetric.computed_at >= since,
                )
            )
            if by_queue:
                q = q.where(SLAMetric.queue_name == by_queue)
            row = (await db.execute(q)).one()
            return {
                "avg_seconds": round(float(row[0]), 2) if row[0] else 0.0,
                "avg_hours": round(float(row[0]) / 3600, 2) if row[0] else 0.0,
                "median_seconds": round(float(row[1]), 2) if row[1] else 0.0,
                "min_seconds": round(float(row[2]), 2) if row[2] else 0.0,
                "max_seconds": round(float(row[3]), 2) if row[3] else 0.0,
                "sample_count": row[4] or 0,
            }

        return {
            "mtta": await _stat("response_time"),
            "mttr": await _stat("resolution_time"),
            "period_days": days,
            "queue_filter": by_queue,
        }

    @staticmethod
    async def aging_tickets(db: AsyncSession) -> dict:
        """7. Aging ticket analysis — tickets open beyond thresholds."""
        now = datetime.utcnow()
        thresholds = {"24h": 24, "48h": 48, "7d": 168, "30d": 720, "90d": 2160}

        closed = TicketSnapshot.is_closed == False

        # Single query with FILTER expressions instead of 5 separate COUNTs
        cutoff_24h = now - timedelta(hours=24)
        cutoff_48h = now - timedelta(hours=48)
        cutoff_7d = now - timedelta(hours=168)
        cutoff_30d = now - timedelta(hours=720)
        cutoff_90d = now - timedelta(hours=2160)

        row = (
            await db.execute(
                select(
                    func.count(TicketSnapshot.ticket_id).filter(TicketSnapshot.created_at < cutoff_24h).label("c24h"),
                    func.count(TicketSnapshot.ticket_id).filter(TicketSnapshot.created_at < cutoff_48h).label("c48h"),
                    func.count(TicketSnapshot.ticket_id).filter(TicketSnapshot.created_at < cutoff_7d).label("c7d"),
                    func.count(TicketSnapshot.ticket_id).filter(TicketSnapshot.created_at < cutoff_30d).label("c30d"),
                    func.count(TicketSnapshot.ticket_id).filter(TicketSnapshot.created_at < cutoff_90d).label("c90d"),
                ).where(closed)
            )
        ).one()

        buckets = {
            "24h": row.c24h or 0,
            "48h": row.c48h or 0,
            "7d": row.c7d or 0,
            "30d": row.c30d or 0,
            "90d": row.c90d or 0,
        }

        oldest = (
            await db.execute(
                select(TicketSnapshot)
                .where(closed)
                .order_by(TicketSnapshot.created_at.asc())
                .limit(5)
            )
        ).scalars().all()

        return {
            "aging_buckets": buckets,
            "oldest_tickets": [
                {
                    "ticket_id": t.ticket_id,
                    "ticket_number": t.ticket_number,
                    "created_at": str(t.created_at),
                    "current_queue": t.current_queue,
                    "current_owner": t.current_owner,
                    "age_hours": round((now - t.created_at).total_seconds() / 3600, 1) if t.created_at else 0,
                }
                for t in oldest
            ],
        }

    @staticmethod
    async def first_touch_resolution(db: AsyncSession, days: int = 90) -> dict:
        """8. First-touch resolution rate — tickets resolved without reassignment."""
        since = datetime.utcnow() - timedelta(days=days)

        handoff_subq = (
            select(
                TicketEvent.ticket_id,
                func.count(TicketEvent.id).label("handoff_count"),
            )
            .where(
                TicketEvent.event_type == "OwnerUpdate",
                TicketEvent.new_owner.isnot(None),
                TicketEvent.old_owner.isnot(None),
                TicketEvent.new_owner != TicketEvent.old_owner,
            )
            .group_by(TicketEvent.ticket_id)
        ).subquery()

        row = (
            await db.execute(
                select(
                    func.count(TicketSnapshot.ticket_id).label("total_resolved"),
                    func.sum(
                        case(
                            (handoff_subq.c.handoff_count.is_(None), 1),
                            else_=0,
                        )
                    ).label("ftr_count"),
                )
                .outerjoin(
                    handoff_subq,
                    TicketSnapshot.ticket_id == handoff_subq.c.ticket_id,
                )
                .where(
                    TicketSnapshot.resolution_at.isnot(None),
                    TicketSnapshot.resolution_at >= since,
                )
            )
        ).one()

        total_resolved = row[0] or 0
        ftr_count = row[1] or 0

        return {
            "ftr_rate": round(ftr_count / total_resolved * 100, 2) if total_resolved else 0.0,
            "ftr_tickets": ftr_count,
            "total_resolved": total_resolved,
        }

    @staticmethod
    async def reopen_rate(db: AsyncSession, days: int = 90) -> dict:
        """9. Reopen rate — tickets reopened after resolution."""
        since = datetime.utcnow() - timedelta(days=days)

        from sqlalchemy import and_

        post_subq = (
            select(
                TicketSnapshot.ticket_id,
                func.count(TicketEvent.id).label("post_count"),
            )
            .outerjoin(
                TicketEvent,
                and_(
                    TicketEvent.ticket_id == TicketSnapshot.ticket_id,
                    TicketEvent.event_time > TicketSnapshot.resolution_at,
                    TicketEvent.event_type.in_(["OwnerUpdate", "StateUpdate"]),
                ),
            )
            .where(
                TicketSnapshot.resolution_at.isnot(None),
                TicketSnapshot.resolution_at >= since,
            )
            .group_by(TicketSnapshot.ticket_id)
        ).subquery()

        row = (
            await db.execute(
                select(
                    func.count().label("total_resolved"),
                    func.sum(
                        case(
                            (post_subq.c.post_count > 0, 1),
                            else_=0,
                        )
                    ).label("reopened"),
                ).select_from(post_subq)
            )
        ).one()

        total_resolved = row[0] or 0
        reopened = row[1] or 0

        return {
            "reopen_rate": round(reopened / total_resolved * 100, 2) if total_resolved else 0.0,
            "reopened_tickets": reopened,
            "total_resolved": total_resolved,
        }

    @staticmethod
    async def breach_root_cause(db: AsyncSession, days: int = 90) -> dict:
        """10. Breach root-cause breakdown — breaches by queue, owner, SLA definition."""
        since = datetime.utcnow() - timedelta(days=days)

        breached = SLAMetric.sla_breached == True

        # By queue
        by_queue_rows = (
            await db.execute(
                select(
                    SLAMetric.queue_name,
                    func.count(SLAMetric.id).label("breaches"),
                )
                .where(breached, SLAMetric.queue_name.isnot(None), SLAMetric.computed_at >= since)
                .group_by(SLAMetric.queue_name)
                .order_by(func.count(SLAMetric.id).desc())
                .limit(20)
            )
        ).all()
        by_queue = [{"queue": r[0], "breaches": r[1]} for r in by_queue_rows]

        # By owner
        by_owner_rows = (
            await db.execute(
                select(
                    SLAMetric.owner,
                    func.count(SLAMetric.id).label("breaches"),
                )
                .where(breached, SLAMetric.owner.isnot(None), SLAMetric.computed_at >= since)
                .group_by(SLAMetric.owner)
                .order_by(func.count(SLAMetric.id).desc())
                .limit(20)
            )
        ).all()
        by_owner = [{"owner": r[0], "breaches": r[1]} for r in by_owner_rows]

        # By metric type
        by_metric_rows = (
            await db.execute(
                select(
                    SLAMetric.metric_name,
                    func.count(SLAMetric.id).label("breaches"),
                )
                .where(breached, SLAMetric.computed_at >= since)
                .group_by(SLAMetric.metric_name)
                .order_by(func.count(SLAMetric.id).desc())
            )
        ).all()
        by_metric = [{"metric_name": r[0], "breaches": r[1]} for r in by_metric_rows]

        # By SLA definition
        by_def_rows = (
            await db.execute(
                select(
                    SLADefinition.name,
                    func.count(SLAMetric.id).label("breaches"),
                )
                .join(SLAMetric, SLAMetric.sla_definition_id == SLADefinition.id)
                .where(breached, SLAMetric.computed_at >= since)
                .group_by(SLADefinition.name)
                .order_by(func.count(SLAMetric.id).desc())
                .limit(10)
            )
        ).all()
        by_definition = [{"name": r[0], "breaches": r[1]} for r in by_def_rows]

        total_breaches = sum(b["breaches"] for b in by_queue) or 0

        return {
            "total_breaches": total_breaches,
            "by_queue": by_queue,
            "by_owner": by_owner,
            "by_metric_type": by_metric,
            "by_sla_definition": by_definition,
        }
