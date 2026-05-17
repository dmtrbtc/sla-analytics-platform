"""Dashboard overview aggregation service — SQL aggregate queries only, no loading all rows."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, case, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.models import (
    ImportSession,
    OwnershipPeriod,
    QueuePeriod,
    SLAMetric,
    SLADefinition,
    Team,
    TicketEvent,
    TicketSnapshot,
)


class DashboardService:
    """Aggregate dashboard data using SQL GROUP BY — no row-by-row loading."""

    @staticmethod
    async def get_overview(db: AsyncSession, days: int = 30) -> dict:
        now = datetime.utcnow()
        since = now - timedelta(days=days)

        # Total tickets
        total_tickets = (await db.execute(select(func.count(TicketSnapshot.ticket_id)))).scalar() or 0

        open_tickets = (
            await db.execute(
                select(func.count(TicketSnapshot.ticket_id)).where(TicketSnapshot.is_closed == False)
            )
        ).scalar() or 0

        closed_tickets = total_tickets - open_tickets

        # SLA summary
        sla_total = (await db.execute(select(func.count(SLAMetric.id)))).scalar() or 0
        sla_breached = (
            await db.execute(select(func.count(SLAMetric.id)).where(SLAMetric.sla_breached == True))
        ).scalar() or 0
        breach_pct = round(sla_breached / sla_total * 100, 2) if sla_total else 0.0

        # Avg response/resolution
        async def _avg_metric(name: str):
            q = select(func.avg(SLAMetric.metric_seconds)).where(
                SLAMetric.metric_name == name, SLAMetric.metric_seconds.isnot(None)
            )
            val = (await db.execute(q)).scalar()
            return round(float(val), 2) if val else 0.0

        avg_response = await _avg_metric("response_time")
        avg_resolution = await _avg_metric("resolution_time")

        # Completed imports
        imports_done = (
            await db.execute(
                select(func.count(ImportSession.id)).where(ImportSession.status == "completed")
            )
        ).scalar() or 0

        # Tickets by queue
        queue_rows = (
            await db.execute(
                select(TicketSnapshot.current_queue, func.count(TicketSnapshot.ticket_id))
                .group_by(TicketSnapshot.current_queue)
                .order_by(func.count(TicketSnapshot.ticket_id).desc())
            )
        ).all()
        tickets_by_queue = {r[0] or "Unknown": r[1] for r in queue_rows}

        # Tickets by state
        state_rows = (
            await db.execute(
                select(TicketSnapshot.current_state, func.count(TicketSnapshot.ticket_id))
                .group_by(TicketSnapshot.current_state)
                .order_by(func.count(TicketSnapshot.ticket_id).desc())
            )
        ).all()
        tickets_by_state = {r[0] or "Unknown": r[1] for r in state_rows}

        # Tickets by confidence
        conf_rows = (
            await db.execute(
                select(TicketSnapshot.confidence, func.count(TicketSnapshot.ticket_id))
                .group_by(TicketSnapshot.confidence)
                .order_by(func.count(TicketSnapshot.ticket_id).desc())
            )
        ).all()
        tickets_by_confidence = {r[0] or "unknown": r[1] for r in conf_rows}

        # Tickets by priority (via SLA definition join)
        priority_rows = (
            await db.execute(
                select(SLADefinition.priority, func.count(func.distinct(SLAMetric.ticket_id)))
                .join(SLAMetric, SLAMetric.sla_definition_id == SLADefinition.id)
                .group_by(SLADefinition.priority)
                .order_by(func.count(func.distinct(SLAMetric.ticket_id)).desc())
            )
        ).all()
        tickets_by_priority = {r[0] or "none": r[1] for r in priority_rows}

        # Breach trend (daily last N days)
        breach_trend_rows = (
            await db.execute(
                select(
                    func.date_trunc("day", SLAMetric.computed_at).label("day"),
                    func.count(SLAMetric.id),
                )
                .where(
                    SLAMetric.sla_breached == True,
                    SLAMetric.computed_at >= since,
                )
                .group_by(text("day"))
                .order_by(text("day"))
            )
        ).all()
        breach_trend = [{"date": str(r[0].date()), "count": r[1]} for r in breach_trend_rows]

        # Import trend (daily last N days)
        import_trend_rows = (
            await db.execute(
                select(
                    func.date_trunc("day", ImportSession.created_at).label("day"),
                    func.count(ImportSession.id),
                )
                .where(ImportSession.created_at >= since)
                .group_by(text("day"))
                .order_by(text("day"))
            )
        ).all()
        import_trend = [{"date": str(r[0].date()), "count": r[1]} for r in import_trend_rows]

        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "closed_tickets": closed_tickets,
            "sla_breach_pct": breach_pct,
            "sla_total": sla_total,
            "sla_breached": sla_breached,
            "avg_response_time_seconds": avg_response,
            "avg_resolution_time_seconds": avg_resolution,
            "imports_processed": imports_done,
            "tickets_by_queue": tickets_by_queue,
            "tickets_by_state": tickets_by_state,
            "tickets_by_confidence": tickets_by_confidence,
            "tickets_by_priority": tickets_by_priority,
            "breach_trend": breach_trend,
            "import_trend": import_trend,
        }

    @staticmethod
    async def get_time_series(
        db: AsyncSession,
        metric: str = "tickets_created",
        granularity: str = "day",
        days: int = 30,
    ) -> list:
        now = datetime.utcnow()
        since = now - timedelta(days=days)
        trunc = "day" if granularity == "daily" else ("week" if granularity == "weekly" else "month")

        if metric == "tickets_created":
            rows = (
                await db.execute(
                    select(
                        func.date_trunc(trunc, TicketSnapshot.created_at).label("period"),
                        func.count(TicketSnapshot.ticket_id),
                    )
                    .where(TicketSnapshot.created_at >= since)
                    .group_by(text("period"))
                    .order_by(text("period"))
                )
            ).all()
            return [{"period": str(r[0]), "count": r[1]} for r in rows]

        elif metric == "tickets_closed":
            rows = (
                await db.execute(
                    select(
                        func.date_trunc(trunc, TicketSnapshot.updated_at).label("period"),
                        func.count(TicketSnapshot.ticket_id),
                    )
                    .where(TicketSnapshot.is_closed == True, TicketSnapshot.updated_at >= since)
                    .group_by(text("period"))
                    .order_by(text("period"))
                )
            ).all()
            return [{"period": str(r[0]), "count": r[1]} for r in rows]

        elif metric == "sla_breaches":
            rows = (
                await db.execute(
                    select(
                        func.date_trunc(trunc, SLAMetric.computed_at).label("period"),
                        func.count(SLAMetric.id),
                    )
                    .where(SLAMetric.sla_breached == True, SLAMetric.computed_at >= since)
                    .group_by(text("period"))
                    .order_by(text("period"))
                )
            ).all()
            return [{"period": str(r[0]), "count": r[1]} for r in rows]

        elif metric in ("response_time", "resolution_time"):
            rows = (
                await db.execute(
                    select(
                        func.date_trunc(trunc, SLAMetric.computed_at).label("period"),
                        func.avg(SLAMetric.metric_seconds),
                    )
                    .where(
                        SLAMetric.metric_name == metric,
                        SLAMetric.metric_seconds.isnot(None),
                        SLAMetric.computed_at >= since,
                    )
                    .group_by(text("period"))
                    .order_by(text("period"))
                )
            ).all()
            return [{"period": str(r[0]), "avg_seconds": round(float(r[1]), 2)} for r in rows]

        return []

    @staticmethod
    async def get_teams_analytics(db: AsyncSession, days: int = 90) -> list:
        since = datetime.utcnow() - timedelta(days=days)
        teams = (await db.execute(select(Team).where(Team.is_active == True))).scalars().all()

        # Batched ownership stats per team_prefix
        owner_rows = (
            await db.execute(
                select(
                    OwnershipPeriod.team_prefix,
                    func.count(func.distinct(OwnershipPeriod.ticket_id)).label("tickets_handled"),
                    func.avg(OwnershipPeriod.duration_seconds).label("avg_owner_time"),
                )
                .where(
                    OwnershipPeriod.team_prefix.isnot(None),
                    OwnershipPeriod.start_time >= since,
                )
                .group_by(OwnershipPeriod.team_prefix)
            )
        ).all()
        owner_map = {r[0]: {"tickets_handled": r[1] or 0, "avg_owner_time": r[2] or 0} for r in owner_rows}

        # Batched queue stats per team_prefix
        queue_rows = (
            await db.execute(
                select(
                    QueuePeriod.team_prefix,
                    func.avg(QueuePeriod.duration_seconds).label("avg_queue_time"),
                )
                .where(
                    QueuePeriod.team_prefix.isnot(None),
                    QueuePeriod.duration_seconds.isnot(None),
                    QueuePeriod.entered_at >= since,
                )
                .group_by(QueuePeriod.team_prefix)
            )
        ).all()
        queue_map = {r[0]: r[1] or 0 for r in queue_rows}

        # Batched SLA metrics per team_prefix
        sla_rows = (
            await db.execute(
                select(
                    SLAMetric.team_prefix,
                    func.count(SLAMetric.id).label("sla_total"),
                    func.sum(
                        case((SLAMetric.sla_breached == True, 1), else_=0)
                    ).label("sla_breached"),
                    func.sum(
                        case(
                            (SLAMetric.metric_name.in_(["response_time"]), 1),
                            else_=0,
                        )
                    ).label("resp_total"),
                    func.sum(
                        case(
                            (
                                and_(
                                    SLAMetric.metric_name.in_(["response_time"]),
                                    SLAMetric.sla_breached == True,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("resp_breached"),
                    func.sum(
                        case(
                            (SLAMetric.metric_name.in_(["resolution_time"]), 1),
                            else_=0,
                        )
                    ).label("res_total"),
                    func.sum(
                        case(
                            (
                                and_(
                                    SLAMetric.metric_name.in_(["resolution_time"]),
                                    SLAMetric.sla_breached == True,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("res_breached"),
                )
                .where(
                    SLAMetric.team_prefix.isnot(None),
                    SLAMetric.computed_at >= since,
                )
                .group_by(SLAMetric.team_prefix)
            )
        ).all()
        sla_map = {}
        for r in sla_rows:
            sla_map[r[0]] = {
                "sla_total": r[1] or 0,
                "sla_breached": r[2] or 0,
                "resp_total": r[3] or 0,
                "resp_breached": r[4] or 0,
                "res_total": r[5] or 0,
                "res_breached": r[6] or 0,
            }

        # Batched top queues per team_prefix (all rows, top 5 selected in Python)
        topq_rows = (
            await db.execute(
                select(
                    QueuePeriod.team_prefix,
                    QueuePeriod.queue_name,
                    func.count(func.distinct(QueuePeriod.ticket_id)).label("tickets"),
                )
                .where(
                    QueuePeriod.team_prefix.isnot(None),
                    QueuePeriod.entered_at >= since,
                )
                .group_by(QueuePeriod.team_prefix, QueuePeriod.queue_name)
                .order_by(QueuePeriod.team_prefix, func.count(func.distinct(QueuePeriod.ticket_id)).desc())
            )
        ).all()
        topq_map = {}
        for r in topq_rows:
            topq_map.setdefault(r[0], []).append({"queue": r[1], "tickets": r[2]})

        # Global reassignment count (not team-specific)
        reassignments = (
            await db.execute(
                select(func.count(TicketEvent.id)).where(
                    TicketEvent.event_type == "OwnerUpdate",
                    TicketEvent.new_owner.isnot(None),
                    TicketEvent.old_owner.isnot(None),
                    TicketEvent.new_owner != TicketEvent.old_owner,
                    TicketEvent.event_time >= since,
                )
            )
        ).scalar() or 0

        result = []
        for team in teams:
            prefix = team.queue_prefix
            o = owner_map.get(prefix, {})
            q = queue_map.get(prefix, 0)
            s = sla_map.get(prefix, {})
            tq = topq_map.get(prefix, [])

            tickets_handled = o.get("tickets_handled", 0)
            avg_owner_time = o.get("avg_owner_time", 0)
            avg_queue_time = q
            sla_total = s.get("sla_total", 0)
            sla_breached = s.get("sla_breached", 0)
            resp_total = s.get("resp_total", 0)
            resp_breached = s.get("resp_breached", 0)
            res_total = s.get("res_total", 0)
            res_breached = s.get("res_breached", 0)

            result.append({
                "team_id": team.id,
                "team_name": team.name,
                "queue_prefix": prefix,
                "tickets_handled": tickets_handled,
                "avg_ownership_time_seconds": round(float(avg_owner_time), 2),
                "avg_queue_time_seconds": round(float(avg_queue_time), 2),
                "sla_breach_pct": round(sla_breached / sla_total * 100, 2) if sla_total else 0.0,
                "sla_total": sla_total,
                "sla_breached": sla_breached,
                "response_sla_total": resp_total,
                "response_sla_breached": resp_breached,
                "response_sla_pct": round(resp_breached / resp_total * 100, 2) if resp_total else 0.0,
                "resolution_sla_total": res_total,
                "resolution_sla_breached": res_breached,
                "resolution_sla_pct": round(res_breached / res_total * 100, 2) if res_total else 0.0,
                "reassignments": reassignments,
                "top_queues": tq[:5],
            })

        return result

    @staticmethod
    async def get_ticket_flow(db: AsyncSession, days: int = 90) -> dict:
        since = datetime.utcnow() - timedelta(days=days)

        # Queue-to-queue transitions
        transitions_rows = (
            await db.execute(
                select(
                    TicketEvent.src_queue,
                    TicketEvent.dest_queue,
                    func.count(TicketEvent.id),
                )
                .where(
                    TicketEvent.event_type == "Move",
                    TicketEvent.src_queue.isnot(None),
                    TicketEvent.dest_queue.isnot(None),
                    TicketEvent.event_time >= since,
                )
                .group_by(TicketEvent.src_queue, TicketEvent.dest_queue)
                .order_by(func.count(TicketEvent.id).desc())
                .limit(100)
            )
        ).all()

        transitions = [
            {"source": r[0], "target": r[1], "value": r[2]}
            for r in transitions_rows
        ]

        # Sankey-compatible format
        all_queues = set()
        for t in transitions:
            all_queues.add(t["source"])
            all_queues.add(t["target"])

        nodes = [{"name": q} for q in sorted(all_queues)]
        edges = transitions

        # Reassignment chains (distinct ticket chains)
        reassign_events = (
            await db.execute(
                select(
                    TicketEvent.ticket_id,
                    TicketEvent.event_time,
                    TicketEvent.old_owner,
                    TicketEvent.new_owner,
                )
                .where(
                    TicketEvent.event_type == "OwnerUpdate",
                    TicketEvent.new_owner.isnot(None),
                    TicketEvent.old_owner.isnot(None),
                    TicketEvent.new_owner != TicketEvent.old_owner,
                    TicketEvent.event_time >= since,
                )
                .order_by(TicketEvent.ticket_id, TicketEvent.event_time)
                .limit(1000)
            )
        ).all()

        # Average handoff count per ticket
        handoff_counts = (
            await db.execute(
                select(
                    TicketEvent.ticket_id,
                    func.count(TicketEvent.id),
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

        total_handoffs = sum(r[1] for r in handoff_counts)
        tickets_with_handoffs = len(handoff_counts)
        avg_handoff = round(total_handoffs / tickets_with_handoffs, 2) if tickets_with_handoffs else 0.0

        return {
            "nodes": nodes,
            "edges": edges,
            "average_handoff_count": avg_handoff,
            "total_reassignments": len(reassign_events),
            "tickets_with_reassignments": tickets_with_handoffs,
        }
