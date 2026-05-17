"""Report generation — queue-level SLA breakdown, Russian localization."""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

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
    make_multi_sheet_xlsx,
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

        owner_qp: dict[int, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for qp_list in qp_map.values():
            for qp in qp_list:
                op_rows = (
                    db.query(OwnershipPeriod)
                    .filter(OwnershipPeriod.ticket_id == qp.ticket_id)
                    .filter(OwnershipPeriod.queue_name == qp.queue_name)
                    .all()
                )
                for op in op_rows:
                    owner_qp[qp.ticket_id][qp.queue_name] += (
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

            row = [
                m.ticket_id,
                ticket_number or "",
                m.metric_name,
                m.metric_seconds if m.metric_seconds is not None else "",
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
                owner_time_sec if owner_time_sec else "",
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
                    m.metric_seconds if m.metric_seconds is not None else "",
                    m.queue_name or "",
                    m.owner or "",
                    queue_path,
                    _fmt_ts(created_at),
                    _fmt_ts(m.computed_at),
                ])

        for qp_list in qp_map.values():
            for qp in qp_list:
                queue_period_rows.append([
                    qp.ticket_id,
                    qp.queue_name,
                    qp.team_prefix or "",
                    _fmt_ts(qp.entered_at),
                    _fmt_ts(qp.exited_at),
                    qp.duration_seconds or 0,
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
                p.duration_seconds or 0,
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
