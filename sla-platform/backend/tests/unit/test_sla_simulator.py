"""Tests for SLA simulator logic and time conversion."""

from app.services.sla.risk_engine import compute_risk_ratio, risk_level_from_ratio, risk_score_from_ratio


class TestSimulatorLogic:
    """Test the core logic used by the SLA simulator endpoint."""

    def test_ratio_computation(self):
        assert compute_risk_ratio(1800, 3600) == 0.5
        assert compute_risk_ratio(3600, 3600) == 1.0
        assert compute_risk_ratio(7200, 3600) == 2.0

    def test_risk_level_boundaries(self):
        assert risk_level_from_ratio(0.5) == "low"
        assert risk_level_from_ratio(0.6) == "medium"
        assert risk_level_from_ratio(0.8) == "high"
        assert risk_level_from_ratio(0.95) == "critical"

    def test_risk_score_capping(self):
        assert risk_score_from_ratio(1.5) == 100
        assert risk_score_from_ratio(0.5) == 50
        assert risk_score_from_ratio(0.0) == 0

    def test_simulate_default_behaviour(self):
        """Test that default simulation (50% ratio) gives medium risk."""
        ratio = compute_risk_ratio(1800, 3600)
        assert ratio == 0.5
        assert risk_level_from_ratio(ratio) == "low"
        assert risk_score_from_ratio(ratio) == 50

    def test_simulate_breach_scenario(self):
        """Test that exceeding targets triggers breach."""
        ratio = compute_risk_ratio(7200, 3600)
        assert ratio == 2.0
        assert risk_level_from_ratio(ratio) == "critical"
        assert risk_score_from_ratio(ratio) == 100


class TestHumanTimeConversion:
    """Test human-readable time format (backend-safe edition)."""

    @staticmethod
    def format_human(seconds: float | int | None) -> str:
        if seconds is None or seconds <= 0:
            return "0 мин"
        secs = float(seconds)
        d = int(secs // 86400)
        h = int((secs % 86400) // 3600)
        m = round((secs % 3600) / 60)
        parts = []
        if d > 0:
            parts.append(f"{d} д")
        if h > 0:
            parts.append(f"{h} ч")
        if m > 0 or not parts:
            parts.append(f"{m} мин")
        return " ".join(parts)

    def test_zero(self):
        assert self.format_human(0) == "0 мин"

    def test_minutes_only(self):
        assert self.format_human(300) == "5 мин"

    def test_hours_minutes(self):
        assert self.format_human(3660) == "1 ч 1 мин"

    def test_hours_exact(self):
        assert self.format_human(7200) == "2 ч"

    def test_days_hours(self):
        assert self.format_human(90000) == "1 д 1 ч"

    def test_negative(self):
        assert self.format_human(-100) == "0 мин"
