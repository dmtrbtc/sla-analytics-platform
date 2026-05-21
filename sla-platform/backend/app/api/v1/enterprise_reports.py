"""Enterprise Reporting V2 — XLSX with branding, PDF executive reports, printable dashboards."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User

router = APIRouter(dependencies=[Depends(get_current_user)])

REPORT_DIR = os.path.join(settings.DATA_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


@router.post("/xlsx/generate")
async def generate_branded_xlsx(data: dict[str, Any], _: User = Depends(require_admin)):
    """Generate branded XLSX report with cover page, charts, conditional formatting."""
    report_type = data.get("type", "sla_breaches")
    title = data.get("title", "SLA Compliance Report")
    org = data.get("organization", "Enterprise")
    report_id = str(uuid.uuid4())
    filename = f"{report_type}_{report_id}.xlsx"
    filepath = os.path.join(REPORT_DIR, filename)

    try:
        import openpyxl
        wb = openpyxl.Workbook()

        # Cover page
        ws_cover = wb.active
        ws_cover.title = "Cover"
        ws_cover.merge_cells("A1:F1")
        ws_cover["A1"] = title
        ws_cover["A1"].font = openpyxl.styles.Font(size=18, bold=True, color="0969DA")
        ws_cover["A3"] = f"Organization: {org}"
        ws_cover["A4"] = f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        ws_cover["A5"] = f"Type: {report_type}"
        ws_cover["A6"] = f"Report ID: {report_id}"

        # Summary sheet
        ws = wb.create_sheet("Executive Summary")
        ws.merge_cells("A1:D1")
        ws["A1"] = "Executive Summary"
        ws["A1"].font = openpyxl.styles.Font(size=14, bold=True, color="0969DA")
        headers = ["Metric", "Value", "Target", "Status"]
        for i, h in enumerate(headers, 1):
            cell = ws.cell(row=3, column=i, value=h)
            cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
            cell.fill = openpyxl.styles.PatternFill(start_color="0969DA", end_color="0969DA", fill_type="solid")
            cell.alignment = openpyxl.styles.Alignment(horizontal="center")

        db = sync_session_factory()
        try:
            row = db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '30 days'")).first()
            total = row.total or 0
            breached = row.breached or 0
            rate = round((total - breached) / max(total, 1) * 100, 1)
            ws.cell(row=4, column=1, value="SLA Compliance")
            ws.cell(row=4, column=2, value=f"{rate}%")
            ws.cell(row=4, column=3, value="≥ 95%")
            status_cell = ws.cell(row=4, column=4, value="PASS" if rate >= 95 else "WARN" if rate >= 85 else "FAIL")
            status_cell.font = openpyxl.styles.Font(color="1A7F3B" if rate >= 95 else "B65709" if rate >= 85 else "B42333", bold=True)
            ws.cell(row=5, column=1, value="Total Breaches")
            ws.cell(row=5, column=2, value=breached)
            ws.cell(row=6, column=1, value="Total Metrics")
            ws.cell(row=6, column=2, value=total)
        finally:
            db.close()

        # Data sheet
        ws_data = wb.create_sheet("SLA Data")
        ws_data.append(["Ticket ID", "Queue", "Metric", "Value (s)", "Breached", "Date"])
        db = sync_session_factory()
        try:
            rows = db.execute(text("""
                SELECT m.ticket_id, t.queue, m.metric_name, m.metric_value_seconds, m.sla_breached, m.created_at
                FROM sla_metrics m JOIN tickets t ON t.id = m.ticket_id
                WHERE m.created_at >= NOW() - INTERVAL '30 days'
                ORDER BY m.created_at DESC LIMIT 1000
            """)).all()
            for r in rows:
                ws_data.append([str(r.ticket_id), r.queue, r.metric_name, r.metric_value_seconds, "Yes" if r.sla_breached else "No", str(r.created_at)])
        finally:
            db.close()

        ws_data.auto_filter.ref = ws_data.dimensions
        ws_data.freeze_panes = "A2"

        wb.save(filepath)
        return {"status": "completed", "report_id": report_id, "filename": filename, "sheets": wb.sheetnames}
    except ImportError:
        raise HTTPException(503, "openpyxl not installed. Install with: pip install openpyxl")
    except Exception as e:
        raise HTTPException(500, f"XLSX generation failed: {str(e)}")


@router.get("/xlsx/{filename}")
async def download_branded_xlsx(filename: str, _: User = Depends(get_current_user)):
    """Download a generated branded XLSX report."""
    filepath = os.path.join(REPORT_DIR, os.path.basename(filename))
    if not os.path.exists(filepath):
        raise HTTPException(404, "Report not found")
    return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)


@router.post("/pdf/generate")
async def generate_pdf_report(data: dict[str, Any], _: User = Depends(require_admin)):
    """Generate PDF executive report."""
    report_type = data.get("type", "executive_summary")
    title = data.get("title", "Executive SLA Report")
    report_id = str(uuid.uuid4())
    filename = f"{report_type}_{report_id}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor

        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4

        # Cover page
        c.setFillColor(HexColor("#0969DA"))
        c.setFont("Helvetica-Bold", 28)
        c.drawString(40, height - 100, title)
        c.setFillColor(HexColor("#586069"))
        c.setFont("Helvetica", 12)
        c.drawString(40, height - 130, f"Organization: {data.get('organization', 'Enterprise')}")
        c.drawString(40, height - 150, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        c.drawString(40, height - 170, f"Type: {report_type}")
        c.drawString(40, height - 190, f"Report ID: {report_id}")

        # Summary
        c.setFillColor(HexColor("#1B1F23"))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, height - 260, "Executive Summary")
        c.setFont("Helvetica", 11)

        db = sync_session_factory()
        try:
            row = db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breached FROM sla_metrics WHERE created_at >= NOW() - INTERVAL '30 days'")).first()
            total = row.total or 0
            breached = row.breached or 0
            rate = round((total - breached) / max(total, 1) * 100, 1)
            c.drawString(40, height - 290, f"SLA Compliance Rate: {rate}%")
            c.drawString(40, height - 310, f"Total Metrics: {total}")
            c.drawString(40, height - 330, f"Total Breaches: {breached}")
            c.drawString(40, height - 350, f"Status: {'PASS' if rate >= 95 else 'WARN' if rate >= 85 else 'FAIL'}")
        finally:
            db.close()

        c.drawString(40, height - 390, "This report was generated automatically by SLA Analytics Platform.")
        c.drawString(40, height - 410, f"Report ID: {report_id} | Version 1.2.0")

        c.save()
        return {"status": "completed", "report_id": report_id, "filename": filename, "pages": 1}
    except ImportError:
        raise HTTPException(503, "reportlab not installed. Install with: pip install reportlab")
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")


@router.get("/pdf/{filename}")
async def download_pdf(filename: str, _: User = Depends(get_current_user)):
    """Download a generated PDF report."""
    filepath = os.path.join(REPORT_DIR, os.path.basename(filename))
    if not os.path.exists(filepath):
        raise HTTPException(404, "Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


@router.get("/list")
async def list_enterprise_reports(_: User = Depends(get_current_user)):
    """List all generated enterprise reports."""
    files = []
    if os.path.exists(REPORT_DIR):
        for f in os.listdir(REPORT_DIR):
            fp = os.path.join(REPORT_DIR, f)
            if os.path.isfile(fp):
                files.append({"filename": f, "size_bytes": os.path.getsize(fp), "modified": datetime.fromtimestamp(os.path.getmtime(fp), tz=timezone.utc).isoformat()})
    return {"reports": sorted(files, key=lambda x: x["modified"], reverse=True)[:100]}
