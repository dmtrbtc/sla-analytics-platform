"""Report generation — queue-level SLA breakdown, Russian localization."""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.models import (
    ImportSession,
    OwnershipPeriod,
    QueuePeriod,
    SLAMetric,
    TicketSnapshot,
)
from app.utils.excel_writer import (
    fmt_time_columns,
    make_multi_sheet_xlsx,
    make_executive_xlsx,
    RU_SLA_METRICS_HEADERS,
    RU_QUEUE_PERIOD_HEADERS,
    RU_BREACH_HEADERS,
    RU_SUMMARY_HEADERS,
    RU_TEAM_PERFORMANCE_HEADERS,
    RU_TICKET_LIFECYCLE_HEADERS,
    RU_IMPORTS_SUMMARY_HEADERS,
    RU_SHEET_SLA_METRICS,
    RU_SHEET_QUEUES,
    RU_SHEET_BREACHES,
    RU_SHEET_SUMMARY,
)


EXPORT_DIR = os.path.join(settings.DATA_DIR, "exports")


def _sanitize_csv_value(value: Any) -> str:
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _fmt_ts(val) -> str:
    if val is None:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    return str(val)


class ReportService:

    @staticmethod
    def _ensure_export_dir():
        os.makedirs(EXPORT_DIR, exist_ok=True)

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _load_queue_periods_map(
        db: Session, ticket_ids: list[int]
    ) -> dict[int, list]:
        """Return {ticket_id: [QueuePeriod, ...]} ordered by entered_at."""
        if not ticket_ids:
            return {}
        qps = (
            db.query(QueuePeriod)
            .filter(QueuePeriod.ticket_id.in_(ticket_ids))
            .order_by(QueuePeriod.entered_at)
            .all()
        )
        m: dict[int, list] = defaultdict(list)
        for qp in qps:
            m[qp.ticket_id].append(qp)
        return dict(m)

    @staticmethod
    def _build_queue_path(qperiods: list) -> str:
        return " → ".join(qp.queue_name for qp in qperiods if qp.queue_name)

    @staticmethod
    def _make_bool_label(val: bool) -> str:
        return "Да" if val else "Нет"

    # ── SLA breaches report (multi-sheet, queue breakdown) ────────

    @staticmethod
    def sla_breaches_report(
        db: Session, import_id: Optional[str] = None, fmt: str = "xlsx"
    ) -> dict:
        q = (
            db.query(
                SLAMetric,
                TicketSnapshot.ticket_number,
                TicketSnapshot.created_at,
                TicketSnapshot.resolution_at,
            )
            .join(
                TicketSnapshot,
                SLAMetric.ticket_id == TicketSnapshot.ticket_id,
                isouter=True,
            )
        )
        if import_id:
            q = q.filter(SLAMetric.import_id == import_id)
        rows_raw = q.order_by(SLAMetric.computed_at.desc()).limit(10000).all()

        ticket_ids = list({r[0].ticket_id for r in rows_raw})
        qp_map = ReportService._load_queue_periods_map(db, ticket_ids)

        # Batch load all OwnershipPeriods for the ticket set (avoids N+1)
        owner_qp: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        all_ops = (
            db.query(OwnershipPeriod)
            .filter(OwnershipPeriod.ticket_id.in_(ticket_ids))
            .all()
        )
        for op in all_ops:
            owner_qp[op.ticket_id][op.queue_name or ""] += (
                op.duration_seconds or 0
            )

        enriched = []
        queue_period_rows = []
        breach_rows = []

        for (m, ticket_number, created_at, resolution_at) in rows_raw:
            qperiods = qp_map.get(m.ticket_id, [])
            queue_path = ReportService._build_queue_path(qperiods)

            qp_entered = None
            qp_exited = None
            if m.metric_name == "queue_time":
                for qp in qperiods:
                    if qp.queue_name == m.queue_name:
                        qp_entered = qp.entered_at
                        qp_exited = qp.exited_at
                        break

            owner_time_sec = owner_qp.get(
                m.ticket_id, {}
            ).get(m.queue_name or "", 0)

            metric_sec = (
                m.metric_seconds if m.metric_seconds is not None else None
            )
            time_cols = fmt_time_columns(metric_sec)

            owner_sec = owner_time_sec if owner_time_sec else None
            owner_cols = fmt_time_columns(owner_sec)

            row = [
                m.ticket_id,
                ticket_number or "",
                m.metric_name,
                *time_cols,
                (
                    ReportService._make_bool_label(m.sla_breached)
                    if m.sla_breached is not None
                    else ""
                ),
                m.queue_name or "",
                queue_path,
                _fmt_ts(qp_entered),
                _fmt_ts(qp_exited),
                m.owner or "",
                *owner_cols,
                m.confidence or "",
                _fmt_ts(created_at),
                _fmt_ts(resolution_at),
                str(m.sla_definition_id or ""),
                _fmt_ts(m.computed_at),
            ]
            enriched.append(row)

            if m.sla_breached:
                breach_rows.append([
                    m.ticket_id,
                    ticket_number or "",
                    m.metric_name,
                    *time_cols,
                    m.queue_name or "",
                    m.owner or "",
                    queue_path,
                    _fmt_ts(created_at),
                    _fmt_ts(m.computed_at),
                ])

        for qp_list in qp_map.values():
            for qp in qp_list:
                duration_cols = fmt_time_columns(qp.duration_seconds)
                queue_period_rows.append([
                    qp.ticket_id,
                    qp.queue_name,
                    qp.team_prefix or "",
                    _fmt_ts(qp.entered_at),
                    _fmt_ts(qp.exited_at),
                    *duration_cols,
                    qp.owner_count or 0,
                ])

        total_metrics = len(rows_raw)
        total_breaches = sum(1 for r in rows_raw if r[0].sla_breached)
        total_tickets = len(ticket_ids)
        total_queue_periods = sum(len(v) for v in qp_map.values())
        breach_pct = (
            round(total_breaches / total_metrics * 100, 1)
            if total_metrics
            else 0
        )

        summary_rows = [
            ["Всего тикетов", str(total_tickets)],
            ["Всего метрик SLA", str(total_metrics)],
            ["Нарушений SLA", str(total_breaches)],
            ["Процент нарушений", f"{breach_pct}%"],
            ["Всего периодов в очередях", str(total_queue_periods)],
        ]

        sheets = [
            {"name": RU_SHEET_SLA_METRICS,
             "headers": RU_SLA_METRICS_HEADERS, "rows": enriched},
            {"name": RU_SHEET_QUEUES,
             "headers": RU_QUEUE_PERIOD_HEADERS, "rows": queue_period_rows},
            {"name": RU_SHEET_BREACHES,
             "headers": RU_BREACH_HEADERS, "rows": breach_rows},
            {"name": RU_SHEET_SUMMARY,
             "headers": RU_SUMMARY_HEADERS, "rows": summary_rows},
        ]

        return ReportService._write_report("sla_breaches", sheets, fmt)

    # ── Team performance report ───────────────────────────────────

    @staticmethod
    def team_performance_report(
        db: Session, team_prefix: Optional[str] = None, fmt: str = "xlsx"
    ) -> dict:
        q = db.query(OwnershipPeriod)
        if team_prefix:
            q = q.filter(OwnershipPeriod.team_prefix == team_prefix)
        periods = (
            q.order_by(OwnershipPeriod.start_time.desc()).limit(10000).all()
        )

        rows = [
            [
                p.ticket_id,
                p.owner or "",
                p.queue_name or "",
                p.team_prefix or "",
                _fmt_ts(p.start_time),
                _fmt_ts(p.end_time),
                *fmt_time_columns(p.duration_seconds),
                ReportService._make_bool_label(p.is_active),
            ]
            for p in periods
        ]
        sheets = [
            {"name": "Команды", "headers": RU_TEAM_PERFORMANCE_HEADERS,
             "rows": rows}
        ]
        return ReportService._write_report("team_performance", sheets, fmt)

    # ── Ticket lifecycle report ───────────────────────────────────

    @staticmethod
    def ticket_lifecycle_report(db: Session, fmt: str = "xlsx") -> dict:
        tickets = (
            db.query(TicketSnapshot)
            .order_by(TicketSnapshot.ticket_id)
            .limit(10000).all()
        )
        rows = [
            [
                t.ticket_id,
                t.ticket_number or "",
                t.title or "",
                t.current_queue or "",
                t.current_state or "",
                t.current_owner or "",
                _fmt_ts(t.created_at),
                _fmt_ts(t.updated_at),
                _fmt_ts(t.first_response_at),
                _fmt_ts(t.resolution_at),
                ReportService._make_bool_label(t.is_closed),
                t.confidence or "",
            ]
            for t in tickets
        ]
        sheets = [
            {"name": "Жизненный цикл",
             "headers": RU_TICKET_LIFECYCLE_HEADERS, "rows": rows}
        ]
        return ReportService._write_report("ticket_lifecycle", sheets, fmt)

    # ── Imports summary report ────────────────────────────────────

    @staticmethod
    def imports_summary_report(db: Session, fmt: str = "xlsx") -> dict:
        sessions = (
            db.query(ImportSession)
            .order_by(ImportSession.created_at.desc())
            .limit(500).all()
        )
        rows = [
            [
                str(s.id),
                s.status,
                s.backlog_file or "",
                s.history_file or "",
                s.backlog_rows or 0,
                s.history_rows or 0,
                _fmt_ts(s.created_at),
                _fmt_ts(s.completed_at),
                len(s.error_details or []),
                json.dumps(s.stats or {}, default=str),
            ]
            for s in sessions
        ]
        sheets = [
            {"name": "Импорты", "headers": RU_IMPORTS_SUMMARY_HEADERS,
             "rows": rows}
        ]
        return ReportService._write_report("imports_summary", sheets, fmt)

    # ── Executive report ──────────────────────────────────────────

    @staticmethod
    def executive_report(db: Session, fmt: str = "xlsx") -> dict:
        """Generate branded executive XLSX with charts and conditional formatting."""
        now = datetime.utcnow()
        since = now - timedelta(days=30)

        # KPI data
        open_tickets = (
            db.query(func.count(TicketSnapshot.ticket_id))
            .filter(TicketSnapshot.is_closed == False)
            .scalar() or 0
        )
        total_tickets = db.query(func.count(TicketSnapshot.ticket_id)).scalar() or 0
        sla_total = db.query(func.count(SLAMetric.id)).scalar() or 0
        sla_breached = (
            db.query(func.count(SLAMetric.id))
            .filter(SLAMetric.sla_breached == True)
            .scalar() or 0
        )
        breach_pct = round(sla_breached / sla_total * 100, 1) if sla_total else 0.0
        avg_response = (
            db.query(func.avg(SLAMetric.metric_seconds))
            .filter(SLAMetric.metric_name.in_(["first_response_time", "response_time"]), SLAMetric.metric_seconds.isnot(None))
            .scalar() or 0
        )
        avg_resolution = (
            db.query(func.avg(SLAMetric.metric_seconds))
            .filter(SLAMetric.metric_name == "resolution_time", SLAMetric.metric_seconds.isnot(None))
            .scalar() or 0
        )
        tickets_at_risk = (
            db.query(func.count(SLAMetric.id))
            .filter(SLAMetric.risk_level.in_(["high", "critical"]))
            .scalar() or 0
        )
        overloaded_queues = (
            db.query(func.count(func.distinct(SLAMetric.queue_name)))
            .filter(SLAMetric.sla_breached == True, SLAMetric.queue_name.isnot(None))
            .scalar() or 0
        )

        kpis = [
            {"label": "Открыто тикетов", "value": open_tickets, "color": "blue"},
            {"label": "Нарушений SLA %", "value": f"{breach_pct}%", "color": "red" if breach_pct > 20 else "green"},
            {"label": "Средний отклик", "value": f"{round(avg_response / 60, 1)} мин" if avg_response else "0 мин", "color": "blue"},
            {"label": "Среднее решение", "value": f"{round(avg_resolution / 3600, 1)} ч" if avg_resolution else "0 ч", "color": "blue"},
            {"label": "Тикетов под риском", "value": tickets_at_risk, "color": "red" if tickets_at_risk > 50 else "green"},
            {"label": "Очередей с нарушениями", "value": overloaded_queues, "color": "red" if overloaded_queues > 5 else "green"},
        ]

        # Breaches by queue
        bq_rows = (
            db.query(
                SLAMetric.queue_name,
                func.count(SLAMetric.id).label("breaches"),
            )
            .filter(SLAMetric.sla_breached == True, SLAMetric.queue_name.isnot(None))
            .group_by(SLAMetric.queue_name)
            .order_by(func.count(SLAMetric.id).desc())
            .limit(10)
            .all()
        )
        breaches_by_queue = [{"queue": r[0], "breaches": r[1]} for r in bq_rows]

        # Breach trend (daily, last 30 days)
        trend_rows_raw = (
            db.query(
                func.date_trunc("day", SLAMetric.computed_at).label("day"),
                func.count(SLAMetric.id).label("count"),
            )
            .filter(SLAMetric.sla_breached == True, SLAMetric.computed_at >= since)
            .group_by(text("day"))
            .order_by(text("day"))
            .all()
        )
        breach_trend = [{"date": str(r[0].date()), "count": r[1]} for r in trend_rows_raw]

        # SLA performance detail
        perf_raw = (
            db.query(
                SLAMetric.ticket_id,
                SLAMetric.metric_name,
                SLAMetric.metric_seconds,
                SLAMetric.sla_breached,
                SLAMetric.queue_name,
                SLAMetric.owner,
                SLAMetric.risk_level,
                SLAMetric.confidence,
            )
            .order_by(SLAMetric.computed_at.desc())
            .limit(5000)
            .all()
        )
        sla_perf_headers = [
            "ID тикета", "Метрика", "Секунды", "Минуты",
            "Нарушение", "Очередь", "Ответственный", "Риск", "Достоверность",
        ]
        sla_performance = []
        for r in perf_raw:
            secs = r[2] if r[2] else 0
            sla_performance.append([
                r[0], r[1], secs, round(secs / 60, 1),
                "Да" if r[3] else "Нет", r[4] or "", r[5] or "",
                r[6] or "", r[7] or "",
            ])

        # Queue analysis
        qa_rows = (
            db.query(
                SLAMetric.queue_name,
                func.count(SLAMetric.id).label("total"),
                func.sum(SLAMetric.sla_breached.cast(type(1))).label("breached"),
                func.avg(SLAMetric.metric_seconds).label("avg_secs"),
            )
            .filter(SLAMetric.queue_name.isnot(None), SLAMetric.computed_at >= since)
            .group_by(SLAMetric.queue_name)
            .order_by(func.count(SLAMetric.id).desc())
            .all()
        )
        queue_analysis_headers = [
            "Очередь", "Всего метрик", "Нарушений", "% нарушений",
            "Среднее (сек)", "Среднее (мин)",
        ]
        queue_analysis = []
        for r in qa_rows:
            total = r[1] or 0
            breached = r[2] or 0
            pct = round(breached / total * 100, 1) if total else 0.0
            avg_s = round(r[3], 1) if r[3] else 0.0
            queue_analysis.append([
                r[0], total, breached, pct, avg_s, round(avg_s / 60, 1),
            ])

        # Trend data for raw sheet
        trend_headers = ["Дата", "Нарушений"]
        trend_data = [[t["date"], t["count"]] for t in breach_trend]

        if fmt != "xlsx":
            return ReportService._write_report("executive", [{"name": "Executive Summary", "headers": sla_perf_headers, "rows": sla_performance}], fmt)

        ReportService._ensure_export_dir()
        ts = now.strftime("%Y%m%d_%H%M%S")
        filename = f"executive_{ts}.{fmt}"
        filepath = os.path.join(EXPORT_DIR, filename)

        buf = make_executive_xlsx(
            kpis=kpis,
            breaches_by_queue=breaches_by_queue,
            breach_trend=breach_trend,
            sla_performance=sla_performance,
            sla_perf_headers=sla_perf_headers,
            queue_analysis=queue_analysis,
            queue_analysis_headers=queue_analysis_headers,
            trend_rows=trend_data,
            trend_headers=trend_headers,
        )
        with open(filepath, "wb") as f:
            f.write(buf.read())

        total_rows = len(sla_performance) + len(queue_analysis) + len(trend_data)
        return {
            "filename": filename,
            "filepath": filepath,
            "rows": total_rows,
            "format": fmt,
        }

    # ── Writer ────────────────────────────────────────────────────

    @staticmethod
    def _write_report(name: str, sheets: list[dict], fmt: str) -> dict:
        ReportService._ensure_export_dir()
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.{fmt}"
        filepath = os.path.join(EXPORT_DIR, filename)

        total_rows = sum(len(s["rows"]) for s in sheets)

        if fmt == "xlsx":
            buf = make_multi_sheet_xlsx(sheets)
            with open(filepath, "wb") as f:
                f.write(buf.read())
        elif fmt == "csv":
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(sheets[0]["headers"])
                writer.writerows(
                    [[_sanitize_csv_value(v) for v in row]
                     for row in sheets[0]["rows"]]
                )
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return {
            "filename": filename,
            "filepath": filepath,
            "rows": total_rows,
            "format": fmt,
        }
