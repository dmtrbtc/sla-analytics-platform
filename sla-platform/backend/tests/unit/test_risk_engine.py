"""Tests for the SLA risk engine."""

from app.services.sla.risk_engine import (
    compute_risk_ratio,
    risk_level_from_ratio,
    risk_score_from_ratio,
)


class TestComputeRiskRatio:
    def test_zero_target(self):
        assert compute_risk_ratio(100, 0) == 0.0

    def test_negative_target(self):
        assert compute_risk_ratio(100, -1) == 0.0

    def test_half_ratio(self):
        assert compute_risk_ratio(500, 1000) == 0.5

    def test_exact_target(self):
        assert compute_risk_ratio(3600, 3600) == 1.0

    def test_over_target(self):
        assert compute_risk_ratio(7200, 3600) == 2.0

    def test_no_elapsed(self):
        assert compute_risk_ratio(0, 3600) == 0.0


class TestRiskLevel:
    def test_low(self):
        assert risk_level_from_ratio(0.3) == "low"

    def test_low_boundary_below(self):
        assert risk_level_from_ratio(0.59) == "low"

    def test_medium(self):
        assert risk_level_from_ratio(0.7) == "medium"

    def test_medium_lower_boundary(self):
        assert risk_level_from_ratio(0.6) == "medium"

    def test_high(self):
        assert risk_level_from_ratio(0.85) == "high"

    def test_high_lower_boundary(self):
        assert risk_level_from_ratio(0.8) == "high"

    def test_critical(self):
        assert risk_level_from_ratio(0.97) == "critical"

    def test_critical_lower_boundary(self):
        assert risk_level_from_ratio(0.95) == "critical"

    def test_exact_one(self):
        assert risk_level_from_ratio(1.0) == "critical"

    def test_above_one(self):
        assert risk_level_from_ratio(1.5) == "critical"


class TestRiskScore:
    def test_zero(self):
        assert risk_score_from_ratio(0.0) == 0

    def test_partial(self):
        assert risk_score_from_ratio(0.5) == 50

    def test_high(self):
        assert risk_score_from_ratio(0.85) == 85

    def test_capped_at_100(self):
        assert risk_score_from_ratio(2.0) == 100

    def test_exact_breach(self):
        assert risk_score_from_ratio(1.0) == 100
