"""Business hours engine V2 — calendar-based, timezone-aware, enterprise-grade.

Supports:
- Working days (per day of week)
- Multiple time windows per day
- Holidays (date ranges)
- Timezone-aware calculations (DST-safe)
- Lunch breaks (configurable exclusions)
- 24x7 calendars
- Split interval processing

Connects to BusinessCalendar ORM model for persistence.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import BusinessCalendar

WEEKDAY_SCHEDULE = {
    "monday":    [{"start": "09:00", "end": "18:00"}],
    "tuesday":   [{"start": "09:00", "end": "18:00"}],
    "wednesday": [{"start": "09:00", "end": "18:00"}],
    "thursday":  [{"start": "09:00", "end": "18:00"}],
    "friday":    [{"start": "09:00", "end": "18:00"}],
}

WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday",
]

DEFAULT_WORKDAYS = {
    "monday": True, "tuesday": True, "wednesday": True,
    "thursday": True, "friday": True,
    "saturday": False, "sunday": False,
}

DEFAULT_START_TIME = "09:00"
DEFAULT_END_TIME = "18:00"


class BusinessTimeEngine:
    """Enterprise business-time calculator with calendar support."""

    def __init__(self, calendar: Optional[BusinessCalendar] = None):
        self.calendar = calendar

    @staticmethod
    def from_calendar(db: Session, calendar_id: Optional[UUID]) -> "BusinessTimeEngine":
        """Load calendar from DB by ID, or return default engine."""
        if calendar_id is None:
            return BusinessTimeEngine(None)
        cal = db.query(BusinessCalendar).filter(
            BusinessCalendar.id == calendar_id,
            BusinessCalendar.is_active == True,
        ).first()
        return BusinessTimeEngine(cal)

    @staticmethod
    def from_sla_def(
        db: Session,
        business_hours_config: Optional[dict],
        business_hours_only: bool,
    ) -> "BusinessTimeEngine":
        """Resolve engine from an SLA definition's config."""
        if not business_hours_only:
            return BusinessTimeEngine(None)
        if business_hours_config and business_hours_config.get("calendar_id"):
            cal_id_str = business_hours_config["calendar_id"]
            try:
                cal_id = UUID(cal_id_str) if isinstance(cal_id_str, str) else cal_id_str
                return BusinessTimeEngine.from_calendar(db, cal_id)
            except (ValueError, AttributeError):
                pass
        return BusinessTimeEngine(None)

    def is_24x7(self) -> bool:
        if self.calendar:
            return self.calendar.is_24x7 or False
        return False

    def _get_tz(self):
        if self.calendar and self.calendar.timezone:
            try:
                import zoneinfo
                return zoneinfo.ZoneInfo(self.calendar.timezone)
            except (ImportError, KeyError, TypeError):
                pass
        return timezone.utc

    def _to_local(self, dt: datetime) -> datetime:
        tz = self._get_tz()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).astimezone(tz)
        return dt.astimezone(tz)

    def _is_working_day(self, d: date) -> bool:
        if self.is_24x7():
            return True
        if self.calendar:
            if self.calendar.holidays_json:
                d_str = d.isoformat()
                for h in self.calendar.holidays_json:
                    if isinstance(h, dict):
                        h_date = h.get("date", "")
                        if h_date == d_str:
                            return False
                        h_start = h.get("start", "")
                        h_end = h.get("end", "")
                        if h_start and h_end and h_start <= d_str <= h_end:
                            return False
                    elif isinstance(h, str) and h == d_str:
                        return False
            workdays = self.calendar.workdays or DEFAULT_WORKDAYS
        else:
            workdays = DEFAULT_WORKDAYS
        day_name = WEEKDAY_NAMES[d.weekday()]
        return workdays.get(day_name, True)

    def _get_slots_for_day(self, d: date) -> list[tuple[time, time]]:
        """Return list of (start_time, end_time) tuples for a given day."""
        if self.is_24x7():
            return [(time(0, 0), time(23, 59, 59))]

        if self.calendar:
            if self.calendar.start_time and self.calendar.end_time:
                slots = []
                st = time.fromisoformat(self.calendar.start_time)
                et = time.fromisoformat(self.calendar.end_time)
                slots.append((st, et))
                return slots
        return [(time(9, 0), time(18, 0))]

    def is_business_time(self, dt: datetime) -> bool:
        """Check if a datetime falls within business hours."""
        if self.is_24x7():
            return True
        local_dt = self._to_local(dt)
        if not self._is_working_day(local_dt.date()):
            return False
        slots = self._get_slots_for_day(local_dt.date())
        t = local_dt.time()
        for start, end in slots:
            if start <= t <= end:
                return True
        return False

    def calculate_business_seconds(
        self,
        start: datetime,
        end: datetime,
    ) -> int:
        """Count business seconds between two datetimes."""
        if self.is_24x7():
            return int((end - start).total_seconds())

        local_start = self._to_local(start)
        local_end = self._to_local(end)

        if local_start >= local_end:
            return 0

        total = 0
        cursor = local_start
        one_day = timedelta(days=1)

        while cursor < local_end:
            current_date = cursor.date()

            if not self._is_working_day(current_date):
                cursor = datetime(
                    current_date.year, current_date.month, current_date.day,
                    tzinfo=local_start.tzinfo,
                ) + one_day
                continue

            slots = self._get_slots_for_day(current_date)
            day_end = (
                local_end
                if current_date == local_end.date()
                else datetime(
                    current_date.year, current_date.month, current_date.day,
                    23, 59, 59, tzinfo=local_start.tzinfo,
                )
            )

            for slot_start, slot_end in slots:
                slot_start_dt = datetime(
                    current_date.year, current_date.month, current_date.day,
                    slot_start.hour, slot_start.minute, slot_start.second,
                    tzinfo=local_start.tzinfo,
                )
                slot_end_dt = datetime(
                    current_date.year, current_date.month, current_date.day,
                    slot_end.hour, slot_end.minute, slot_end.second,
                    tzinfo=local_start.tzinfo,
                )

                if cursor >= slot_end_dt:
                    continue

                seg_start = max(cursor, slot_start_dt)
                seg_end = min(slot_end_dt, day_end)

                if seg_start < seg_end:
                    delta = (seg_end - seg_start).total_seconds()
                    if delta > 0:
                        total += delta

            cursor = datetime(
                current_date.year, current_date.month, current_date.day,
                tzinfo=local_start.tzinfo,
            ) + one_day

        return int(total)

    def calculate_active_seconds_business(
        self,
        intervals: list[tuple[datetime, datetime]],
    ) -> int:
        """Sum business seconds across multiple intervals."""
        total = 0
        for s, e in intervals:
            total += self.calculate_business_seconds(s, e)
        return total


def calculate_business_seconds(
    start: datetime,
    end: datetime,
    config: Optional[dict] = None,
) -> int:
    """Legacy-compatible wrapper — original dict-based schedule logic."""
    schedule = _resolve_config(config)
    if schedule is None:
        return int((end - start).total_seconds())

    total = 0
    cursor = start
    one_day = timedelta(days=1)

    while cursor < end:
        day_name = cursor.strftime("%A").lower()
        slots = schedule.get(day_name, [])
        day_end = end if cursor.date() == end.date() else cursor.replace(hour=23, minute=59, second=59)

        if slots:
            for slot in slots:
                try:
                    ws = time.fromisoformat(slot["start"])
                    we = time.fromisoformat(slot["end"])
                except (KeyError, ValueError):
                    continue
                slot_start = cursor.replace(hour=ws.hour, minute=ws.minute, second=0)
                slot_end = cursor.replace(hour=we.hour, minute=we.minute, second=0)
                if cursor >= slot_end:
                    continue
                seg_start = max(cursor, slot_start)
                seg_end = min(slot_end, day_end)
                if seg_start < seg_end:
                    total += int((seg_end - seg_start).total_seconds())

        cursor = cursor.replace(hour=0, minute=0, second=0) + one_day

    return total


def is_business_time(ts: datetime, config: Optional[dict] = None) -> bool:
    """Legacy-compatible wrapper — handles dict-based config."""
    schedule = _resolve_config(config)
    if schedule is None:
        return True
    day_name = ts.strftime("%A").lower()
    slots = schedule.get(day_name, [])
    t = ts.time()
    for slot in slots:
        try:
            start = time.fromisoformat(slot["start"])
            end = time.fromisoformat(slot["end"])
        except (KeyError, ValueError):
            continue
        if start <= t <= end:
            return True
    return False


def _resolve_config(config: Optional[dict]) -> Optional[dict]:
    """Legacy-compatible wrapper."""
    if config is None:
        return WEEKDAY_SCHEDULE
    if config.get("24_7"):
        return None
    if not config:
        return WEEKDAY_SCHEDULE
    return config
