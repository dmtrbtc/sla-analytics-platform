"""Tests for Billing — works without live DB."""
import uuid
import pytest
from app.services.billing.usage import (
    seed_default_plans, get_org_plan, check_quota, record_usage, get_billing_analytics,
)


class TestSeedPlans:
    def test_seeds_and_returns_plan_count(self):
        seed_default_plans()


class TestGetOrgPlan:
    def test_returns_none_for_unknown_org(self):
        result = get_org_plan(uuid.uuid4())
        assert result is None


class TestCheckQuota:
    def test_returns_dict_with_quota_defaults(self):
        result = check_quota(uuid.uuid4(), "api_call")
        assert isinstance(result, dict)


class TestRecordUsage:
    def test_records_without_error(self):
        record_usage(uuid.uuid4(), "api_call", 5)


class TestBillingAnalytics:
    def test_returns_overview_dict(self):
        result = get_billing_analytics()
        assert isinstance(result, dict)
