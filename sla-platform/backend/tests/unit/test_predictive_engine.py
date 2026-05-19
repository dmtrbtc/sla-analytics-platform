"""Tests for predictive_engine.py — breach ETA, queue overload."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.sla.predictive_engine import (
    compute_breach_eta,
)


class TestComputeBreachEta:
    def test_target_zero(self):
        assert compute_breach_eta(100, 0) is None

    def test_already_breached(self):
        result = compute_breach_eta(100, 80)
        assert result["status"] == "breached"
        assert result["remaining_seconds"] == 0
        assert result["breach_probability"] == 100

    def test_critical(self):
        result = compute_breach_eta(95, 100)
        assert result["breach_probability"] == 95
        assert result["status"] == "active"
        assert result["remaining_seconds"] == 5

    def test_high(self):
        result = compute_breach_eta(85, 100)
        assert result["breach_probability"] == 75
        assert result["status"] == "active"

    def test_medium(self):
        result = compute_breach_eta(70, 100)
        assert result["breach_probability"] == 40
        assert result["status"] == "active"

    def test_low(self):
        result = compute_breach_eta(30, 100)
        assert result["breach_probability"] == 15
        assert result["status"] == "active"

    def test_safe(self):
        result = compute_breach_eta(10, 100)
        assert result["breach_probability"] == 5
        assert result["status"] == "active"

    def test_elapsed_ratio(self):
        result = compute_breach_eta(25, 100)
        assert result["elapsed_ratio"] == 0.25
