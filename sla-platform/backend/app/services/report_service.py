"""Report generation service — XLSX/CSV export for SLA breaches, team perf, ticket lifecycle, imports."""

import csv
import io
import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.models import (
    ImportSession,
    OwnershipPeriod,
    QueuePeriod,
    SLAMetric,
    SLADefinition,
    TicketEvent,
    TicketSnapshot,
)
from app.utils.excel_writer import make_xlsx


EXPORT_DIR = os.path.join(settings.DATA_DIR, "exports")


class ReportService:

    @staticmethod
    def _ensure_export_dir():
        os.makedirs(EXPORT_DIR, exist_ok=True)

    @staticmethod
    def sla_breaches_report(db: Session, import_id: Optional[str] = None, fmt: str = "xlsx") -> dict:
        q = db.query(SLAMetric).join(
            TicketSnapshot, SLAMetric.ticket_id == TicketSnapshot.ticket_id, isouter=True
        ).filter(SLAMetric.sla_breached == True)
        if import_id:
            q = q.filter(SLAMetric.import_id == import_id)
        metrics = q.order_by(SLAMetric.computed_at.desc()).limit(10000).all()

        headers = [
            "Ticket ID", "Ticket Number", "Metric", "Seconds", "Breached",
            "Queue", "Owner", "Definition ID", "Confidence", "Computed At",
        ]
        rows = []
        for m in metrics:
            ticket = db.get(TicketSnapshot, m.ticket_id)
            rows.append([
                m.ticket_id,
                ticket.ticket_number if ticket else "",
                m.metric_name,
                m.metric_seconds,
                "Yes" if m.sla_breached else "No",
                m.queue_name or "",
                m.owner or "",
                m.sla_definition_id or "",
                m.confidence or "",
                str(m.computed_at) if m.computed_at else "",
            ])

        return ReportService._write_report("sla_breaches", headers, rows, fmt)

    @staticmethod
    def team_performance_report(db: Session, team_prefix: Optional[str] = None, fmt: str = "xlsx") -> dict:
        q = db.query(OwnershipPeriod)
        if team_prefix:
            q = q.filter(OwnershipPeriod.team_prefix == team_prefix)
        periods = q.order_by(OwnershipPeriod.start_time.desc()).limit(10000).all()

        headers = [
            "Ticket ID", "Owner", "Queue", "Team Prefix",
            "Start Time", "End Time", "Duration (s)", "Is Active",
        ]
        rows = [
            [
                p.ticket_id, p.owner or "", p.queue_name or "", p.team_prefix or "",
                str(p.start_time), str(p.end_time or ""), p.duration_seconds or 0,
                "Yes" if p.is_active else "No",
            ]
            for p in periods
        ]
        return ReportService._write_report("team_performance", headers, rows, fmt)

    @staticmethod
    def ticket_lifecycle_report(db: Session, fmt: str = "xlsx") -> dict:
        tickets = db.query(TicketSnapshot).order_by(TicketSnapshot.ticket_id).limit(10000).all()
        headers = [
            "Ticket ID", "Ticket Number", "Title", "Queue", "State",
            "Owner", "Created At", "Updated At", "First Response At",
            "Resolution At", "Is Closed", "Confidence",
        ]
        rows = [
            [
                t.ticket_id, t.ticket_number or "", t.title or "",
                t.current_queue or "", t.current_state or "",
                t.current_owner or "", str(t.created_at) if t.created_at else "",
                str(t.updated_at) if t.updated_at else "",
                str(t.first_response_at) if t.first_response_at else "",
                str(t.resolution_at) if t.resolution_at else "",
                "Yes" if t.is_closed else "No", t.confidence or "",
            ]
            for t in tickets
        ]
        return ReportService._write_report("ticket_lifecycle", headers, rows, fmt)

    @staticmethod
    def imports_summary_report(db: Session, fmt: str = "xlsx") -> dict:
        sessions = db.query(ImportSession).order_by(ImportSession.created_at.desc()).limit(500).all()
        headers = [
            "Session ID", "Status", "Backlog File", "History File",
            "Backlog Rows", "History Rows", "Created At", "Completed At",
            "Errors", "Stats",
        ]
        rows = [
            [
                str(s.id), s.status, s.backlog_file or "", s.history_file or "",
                s.backlog_rows or 0, s.history_rows or 0,
                str(s.created_at) if s.created_at else "",
                str(s.completed_at) if s.completed_at else "",
                len(s.error_details or []),
                json.dumps(s.stats or {}, default=str),
            ]
            for s in sessions
        ]
        return ReportService._write_report("imports_summary", headers, rows, fmt)

    @staticmethod
    def _write_report(name: str, headers: list[str], rows: list[list], fmt: str) -> dict:
        ReportService._ensure_export_dir()
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.{fmt}"
        filepath = os.path.join(EXPORT_DIR, filename)

        if fmt == "xlsx":
            buf = make_xlsx(headers, rows, sheet_name=name)
            with open(filepath, "wb") as f:
                f.write(buf.read())
        elif fmt == "csv":
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return {
            "filename": filename,
            "filepath": filepath,
            "rows": len(rows),
            "format": fmt,
        }
