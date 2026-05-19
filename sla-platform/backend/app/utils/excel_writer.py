"""Excel generation utilities using openpyxl with Russian localization."""

import csv
import io
from typing import Any

from openpyxl import Workbook
from openpyxl.chart import PieChart, BarChart, Reference
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, numbers
from openpyxl.utils import get_column_letter


def _sanitize_csv_value(value: Any) -> str:
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(
    start_color="4472C4", end_color="4472C4", fill_type="solid"
)
HEADER_ALIGNMENT = Alignment(
    horizontal="center", vertical="center", wrap_text=True
)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# Branded executive report theme
EXEC_BRAND_COLOR = "1F4E79"
EXEC_ACCENT_COLOR = "2E75B6"
EXEC_HEADER_FILL = PatternFill(start_color=EXEC_BRAND_COLOR, end_color=EXEC_BRAND_COLOR, fill_type="solid")
EXEC_SUBHEADER_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
EXEC_FONT_TITLE = Font(bold=True, color=EXEC_BRAND_COLOR, size=14)
EXEC_FONT_SUBTITLE = Font(bold=True, color="FFFFFF", size=11)
EXEC_FONT_KPI = Font(bold=True, size=16, color=EXEC_BRAND_COLOR)
EXEC_FONT_KPI_LABEL = Font(size=10, color="666666")
EXEC_FILL_GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
EXEC_FILL_RED = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
EXEC_FILL_YELLOW = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
EXEC_FONT_GREEN = Font(color="006100")
EXEC_FONT_RED = Font(color="9C0006")
EXEC_FONT_YELLOW = Font(color="9C6500")

# ── Russian sheet names ──────────────────────────────────────────
RU_SHEET_SLA_METRICS = "Метрики SLA"
RU_SHEET_QUEUES = "Очереди"
RU_SHEET_BREACHES = "Нарушения SLA"
RU_SHEET_SUMMARY = "Сводка"

# ── Russian column headers per report type ───────────────────────
RU_SLA_METRICS_HEADERS = [
    "ID заявки",
    "Номер заявки",
    "Метрика",
    "Время (сек)",
    "Время (мин)",
    "Время (час)",
    "Нарушение SLA",
    "Очередь",
    "Путь по очередям",
    "Время входа в очередь",
    "Время выхода из очереди",
    "Ответственный",
    "Время владения (сек)",
    "Время владения (мин)",
    "Время владения (час)",
    "Достоверность",
    "Создано",
    "Закрыто",
    "Definition ID",
    "Вычислено",
]

RU_QUEUE_PERIOD_HEADERS = [
    "ID заявки",
    "Очередь",
    "Команда",
    "Время входа",
    "Время выхода",
    "Секунды",
    "Минуты",
    "Часы",
    "Ответственных",
]

RU_BREACH_HEADERS = [
    "ID заявки",
    "Номер заявки",
    "Метрика",
    "Время (сек)",
    "Время (мин)",
    "Время (час)",
    "Очередь",
    "Ответственный",
    "Путь по очередям",
    "Создано",
    "Вычислено",
]

RU_SUMMARY_HEADERS = [
    "Показатель",
    "Значение",
]

RU_TEAM_PERFORMANCE_HEADERS = [
    "ID заявки",
    "Ответственный",
    "Очередь",
    "Команда",
    "Начало",
    "Окончание",
    "Секунды",
    "Минуты",
    "Часы",
    "Активен",
]

RU_TICKET_LIFECYCLE_HEADERS = [
    "ID заявки",
    "Номер заявки",
    "Название",
    "Очередь",
    "Состояние",
    "Ответственный",
    "Создано",
    "Обновлено",
    "Первый ответ",
    "Решение",
    "Закрыт",
    "Достоверность",
]

RU_IMPORTS_SUMMARY_HEADERS = [
    "ID сессии",
    "Статус",
    "Файл backlog",
    "Файл history",
    "Строк backlog",
    "Строк history",
    "Создано",
    "Завершено",
    "Ошибок",
    "Статистика",
]


def format_duration(seconds: float | int | None) -> str:
    """Convert seconds to human-readable format.
    < 60 sec -> "X sec"
    < 3600 sec -> "X min"
    >= 3600 sec -> "X h Y min"
    """
    if seconds is None or seconds <= 0:
        return "0 sec"
    secs = float(seconds)
    if secs < 60:
        return f"{round(secs)} sec"
    if secs < 3600:
        return f"{round(secs / 60)} min"
    h = int(secs // 3600)
    m = round((secs % 3600) / 60)
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"


def fmt_time_columns(seconds: float | int | None) -> list:
    """Convert seconds to [сек, мин, час] with 2-decimal rounding."""
    if seconds is None or seconds == "":
        return ["", "", ""]
    secs = round(float(seconds), 2)
    mins = round(secs / 60, 2)
    hours = round(secs / 3600, 2)
    return [secs, mins, hours]


def _write_sheet(ws, headers: list[str], rows: list[list[Any]]):
    """Write header + data rows to an open worksheet with styling."""
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-width
    for col_idx, header in enumerate(headers, 1):
        max_len = len(str(header))
        for row_idx in range(2, min(len(rows) + 2, 50)):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        col_l = get_column_letter(col_idx)
        ws.column_dimensions[col_l].width = min(max_len + 3, 60)


def make_xlsx(
    headers: list[str], rows: list[list[Any]], sheet_name: str = "Sheet1"
) -> io.BytesIO:
    """Create a single-sheet XLSX workbook (backward compatible)."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    _write_sheet(ws, headers, rows)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def make_multi_sheet_xlsx(sheets: list[dict]) -> io.BytesIO:
    """Create a multi-sheet XLSX workbook.

    Each entry in *sheets*::
        {"name": str, "headers": list[str], "rows": list[list]}
    """
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet
    for s in sheets:
        ws = wb.create_sheet(title=s["name"])
        _write_sheet(ws, s["headers"], s["rows"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _apply_conditional_format(ws, min_row: int, max_row: int, min_col: int, max_col: int, thresholds: list[tuple[float, float, PatternFill, Font]]):
    """Apply conditional color fills based on numeric thresholds.
    Each threshold: (lower_bound, upper_bound, fill, font)
    """
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            cell = ws.cell(row=row, column=col)
            val = cell.value
            if isinstance(val, (int, float)):
                for lo, hi, fill, font in thresholds:
                    if lo <= val <= hi:
                        cell.fill = fill
                        cell.font = font
                        break


def make_executive_xlsx(
    kpis: list[dict],
    breaches_by_queue: list[dict],
    breach_trend: list[dict],
    sla_performance: list[list[Any]],
    sla_perf_headers: list[str],
    queue_analysis: list[list[Any]],
    queue_analysis_headers: list[str],
    trend_rows: list[list[Any]],
    trend_headers: list[str],
) -> io.BytesIO:
    """Generate a branded executive XLSX with charts, conditional formatting."""
    wb = Workbook()

    # ═══════════════ Sheet 1: Executive Summary ═══════════════
    ws = wb.active
    ws.title = "Executive Summary"

    # Brand banner
    ws.merge_cells("A1:K1")
    banner_cell = ws["A1"]
    banner_cell.value = "SLA Analytics Platform — Executive Report"
    banner_cell.font = Font(bold=True, color="FFFFFF", size=16)
    banner_cell.fill = EXEC_HEADER_FILL
    banner_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:K2")
    gen_cell = ws["A2"]
    from datetime import datetime
    gen_cell.value = f"Сгенерировано: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    gen_cell.font = Font(size=10, color="666666")
    gen_cell.alignment = Alignment(horizontal="right")

    # KPI cards (row 4-7)
    kpi_start_row = 4
    for i, kpi in enumerate(kpis[:6]):
        col = 2 * i + 1
        cell_val = ws.cell(row=kpi_start_row, column=col, value=kpi.get("label", ""))
        cell_val.font = EXEC_FONT_KPI_LABEL
        cell_val.alignment = Alignment(horizontal="center")
        cell_num = ws.cell(row=kpi_start_row + 1, column=col, value=kpi.get("value", ""))
        cell_num.font = EXEC_FONT_KPI
        cell_num.alignment = Alignment(horizontal="center")
        ws.merge_cells(start_row=kpi_start_row, start_column=col, end_row=kpi_start_row, end_column=col + 1)
        ws.merge_cells(start_row=kpi_start_row + 1, start_column=col, end_row=kpi_start_row + 1, end_column=col + 1)
        if kpi.get("color") == "red":
            cell_num.font = Font(bold=True, size=16, color="CC0000")
        elif kpi.get("color") == "green":
            cell_num.font = Font(bold=True, size=16, color="006100")

    # Pie chart: breaches by queue (using data below)
    chart_data_start = kpi_start_row + 3
    ws.cell(row=chart_data_start, column=1, value="Queue").font = EXEC_FONT_SUBTITLE
    ws.cell(row=chart_data_start, column=1).fill = EXEC_HEADER_FILL
    ws.cell(row=chart_data_start, column=2, value="Breaches").font = EXEC_FONT_SUBTITLE
    ws.cell(row=chart_data_start, column=2).fill = EXEC_HEADER_FILL
    for i, bq in enumerate(breaches_by_queue[:10]):
        ws.cell(row=chart_data_start + 1 + i, column=1, value=bq.get("queue", bq.get("queue_name", "")))
        ws.cell(row=chart_data_start + 1 + i, column=2, value=bq.get("breaches", bq.get("count", 0)))

    pie = PieChart()
    pie.title = "Breaches by Queue"
    pie.style = 10
    pie_data = Reference(ws, min_col=2, min_row=chart_data_start, max_row=chart_data_start + min(len(breaches_by_queue), 10))
    pie_cats = Reference(ws, min_col=1, min_row=chart_data_start + 1, max_row=chart_data_start + min(len(breaches_by_queue), 10))
    pie.add_data(pie_data, titles_from_data=True)
    pie.set_categories(pie_cats)
    pie.width = 16
    pie.height = 12
    ws.add_chart(pie, "D4")

    # Bar chart: breach trend
    trend_chart_start = chart_data_start + 14
    ws.cell(row=trend_chart_start, column=1, value="Date").font = EXEC_FONT_SUBTITLE
    ws.cell(row=trend_chart_start, column=1).fill = EXEC_HEADER_FILL
    ws.cell(row=trend_chart_start, column=2, value="Breaches").font = EXEC_FONT_SUBTITLE
    ws.cell(row=trend_chart_start, column=2).fill = EXEC_HEADER_FILL
    for i, bt in enumerate(breach_trend[:31]):
        ws.cell(row=trend_chart_start + 1 + i, column=1, value=bt.get("date", ""))
        ws.cell(row=trend_chart_start + 1 + i, column=2, value=bt.get("count", bt.get("breaches", 0)))

    bar = BarChart()
    bar.type = "col"
    bar.title = "Daily Breach Trend (Last 30 Days)"
    bar.style = 10
    bar.y_axis.title = "Breaches"
    bar.x_axis.title = "Date"
    bar_data = Reference(ws, min_col=2, min_row=trend_chart_start, max_row=trend_chart_start + min(len(breach_trend), 31))
    bar_cats = Reference(ws, min_col=1, min_row=trend_chart_start + 1, max_row=trend_chart_start + min(len(breach_trend), 31))
    bar.add_data(bar_data, titles_from_data=True)
    bar.set_categories(bar_cats)
    bar.width = 20
    bar.height = 12
    ws.add_chart(bar, "D18")

    # ═══════════════ Sheet 2: SLA Performance ═══════════════
    ws2 = wb.create_sheet("SLA Performance")
    _write_sheet(ws2, sla_perf_headers, sla_performance)
    # Conditional formatting: breach columns (assume column 3 or "Breached" column)
    breach_col_idx = next((i + 1 for i, h in enumerate(sla_perf_headers) if "breach" in h.lower() or "наруш" in h.lower()), None)
    if breach_col_idx:
        for row_idx in range(2, len(sla_performance) + 2):
            cell = ws2.cell(row=row_idx, column=breach_col_idx)
            if cell.value is True or str(cell.value).lower() in ("yes", "да", "true", "1"):
                cell.fill = EXEC_FILL_RED
                cell.font = EXEC_FONT_RED
            elif cell.value is False or str(cell.value).lower() in ("no", "нет", "false", "0"):
                cell.fill = EXEC_FILL_GREEN
                cell.font = EXEC_FONT_GREEN

    # ═══════════════ Sheet 3: Queue Analysis ═══════════════
    ws3 = wb.create_sheet("Queue Analysis")
    _write_sheet(ws3, queue_analysis_headers, queue_analysis)
    # Conditional formatting on breach % column
    pct_col_idx = next((i + 1 for i, h in enumerate(queue_analysis_headers) if "%" in h or "pct" in h.lower()), None)
    if pct_col_idx:
        for row_idx in range(2, len(queue_analysis) + 2):
            cell = ws3.cell(row=row_idx, column=pct_col_idx)
            val = cell.value
            if isinstance(val, (int, float)):
                if val > 80:
                    cell.fill = EXEC_FILL_RED
                    cell.font = EXEC_FONT_RED
                elif val > 50:
                    cell.fill = EXEC_FILL_YELLOW
                    cell.font = EXEC_FONT_YELLOW
                else:
                    cell.fill = EXEC_FILL_GREEN
                    cell.font = EXEC_FONT_GREEN

    # ═══════════════ Sheet 4: Trends ═══════════════
    ws4 = wb.create_sheet("Trends")
    _write_sheet(ws4, trend_headers, trend_rows)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def make_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_sanitize_csv_value(v) for v in row])
    return buf.getvalue()
