"""Excel generation utilities using openpyxl with Russian localization."""

import csv
import io
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
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


def make_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_sanitize_csv_value(v) for v in row])
    return buf.getvalue()
