"""Forensic time-scope helper — v2.1.

Everything operational analytics needs to answer "in the last 24h / 7d /
30d / custom range" — but with PROPER OVERLAP MATH on durational records
(queue_periods, ownership_periods, pause segments), not the naive
`created_at BETWEEN since AND until` filter.

──────────────────────────────────────────────────────────────────────
The overlap rule
──────────────────────────────────────────────────────────────────────
A queue_period segment is `[entered_at, exited_at]`. The window is
`[since, until]`. The amount of time this segment contributes to
analytics inside the window is:

    overlap = max(0, min(exited_at, until) - max(entered_at, since))

If `entered_at > until` (segment starts after window) OR
`exited_at < since` (segment ends before window), the overlap is zero
and the segment must be excluded.

This file produces both the Python-side scope object and the SQL
fragments callers should embed in their CTEs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


_PERIOD_TO_DELTA = {
    "24h":  timedelta(hours=24),
    "1d":   timedelta(days=1),
    "7d":   timedelta(days=7),
    "30d":  timedelta(days=30),
    "90d":  timedelta(days=90),
    "365d": timedelta(days=365),
    "1y":   timedelta(days=365),
}


@dataclass(frozen=True)
class TimeScope:
    """Resolved time window. Naive (UTC, no tzinfo) so they bind cleanly
    against SQLAlchemy's `:since` / `:until` numeric/timestamp params.

    All-time mode is represented as (since=None, until=None) — callers
    treat None as "no filter".
    """
    since: Optional[datetime]
    until: Optional[datetime]
    label: str   # human label for telemetry / logs

    @property
    def is_all_time(self) -> bool:
        return self.since is None and self.until is None

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.since and self.until:
            return int((self.until - self.since).total_seconds())
        return None

    def previous(self) -> "TimeScope":
        """Symmetric previous-period window for delta-vs-previous mode."""
        if self.is_all_time or self.since is None or self.until is None:
            return TimeScope(None, None, "all-time (prev=all-time)")
        d = self.until - self.since
        return TimeScope(self.since - d, self.since, f"prev:{self.label}")

    def to_dict(self) -> dict:
        return {
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "label": self.label,
            "is_all_time": self.is_all_time,
            "duration_seconds": self.duration_seconds,
        }


def _now_utc_naive() -> datetime:
    """Postgres `NOW()` returns timestamptz; SQLAlchemy comparisons need
    matching types. We use UTC naive on the Python side throughout."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_time_scope(
    period: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> TimeScope:
    """Parse the API's time-scope query params into a TimeScope.

    Precedence:
      1. If period is given AND a non-"all" non-empty value, use it.
      2. Else if `since` (and optional `until`) provided, use them.
      3. Else all-time.

    Anything malformed → all-time (caller can still set its own default).
    """
    # Normalise
    p = (period or "").strip().lower() if period else ""
    if p in ("", "all", "all-time", "alltime", "lifetime", "*"):
        p = ""

    now = _now_utc_naive()

    if p:
        d = _PERIOD_TO_DELTA.get(p)
        if d is not None:
            return TimeScope(since=now - d, until=now, label=p)
        # Unknown period — fall through to since/until

    s_dt: Optional[datetime] = None
    u_dt: Optional[datetime] = None
    if since:
        try:
            s_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            if s_dt.tzinfo is not None:
                s_dt = s_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            s_dt = None
    if until:
        try:
            u_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if u_dt.tzinfo is not None:
                u_dt = u_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            u_dt = None

    if s_dt and not u_dt:
        u_dt = now
    if s_dt and u_dt and s_dt < u_dt:
        return TimeScope(since=s_dt, until=u_dt, label=f"custom:{s_dt.date()}..{u_dt.date()}")

    # Final fallback: all-time
    return TimeScope(None, None, "all-time")


# ─── SQL helpers ───────────────────────────────────────────────────


# Stand-alone Postgres expression that computes the overlap (in seconds)
# between a durational record [start_col, end_col_or_now] and the
# named bind params :since / :until.
#
# Usage:
#     SUM({overlap_seconds_sql("op.start_time", "op.end_time")})::bigint
#         AS overlap_sec
#
# When the caller passes a TimeScope that's all-time, the binds should
# be NULL — the expression then degenerates to the full duration.
OVERLAP_TEMPLATE = (
    "GREATEST(0, EXTRACT(EPOCH FROM ("
    "LEAST(COALESCE({end_col}, NOW()), COALESCE(:until, COALESCE({end_col}, NOW()))) "
    "- "
    "GREATEST({start_col}, COALESCE(:since, {start_col}))"
    ")))"
)


def overlap_seconds_sql(start_col: str, end_col: str) -> str:
    """Returns a SQL expression that evaluates to overlap-in-seconds
    between the durational record `[start_col, end_col]` and the bind
    params `:since`, `:until`. Works for queue_periods AND ownership_periods.

    The expression is safe with NULL `end_col` (open segments) — falls
    back to NOW(). The bind params being NULL means "no filter on that
    end" so analysts get all-time when no scope is applied.
    """
    return OVERLAP_TEMPLATE.format(start_col=start_col, end_col=end_col)


def scope_filter_sql(start_col: str, end_col: str) -> str:
    """Returns a WHERE-fragment that EXCLUDES records entirely outside
    the scope window (efficiency — avoids loading rows we'd zero-out).

    Pattern:
        AND ((:since IS NULL) OR COALESCE({end_col}, NOW()) > :since)
        AND ((:until IS NULL) OR {start_col} < :until)
    """
    return (
        f"((:since IS NULL) OR COALESCE({end_col}, NOW()) > :since)"
        f" AND ((:until IS NULL) OR {start_col} < :until)"
    )


def scope_params(scope: TimeScope) -> dict:
    """Standard dict to merge into SQLAlchemy `.execute(text(...), {...})`
    so callers don't have to remember the bind names."""
    return {"since": scope.since, "until": scope.until}
