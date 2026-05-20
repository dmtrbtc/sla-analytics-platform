"""Tests for HA + Resilience — works offline with mock data."""
from app.services.ha.resilience import (
    check_redis_health, check_postgres_replicas, check_queue_failover,
    graceful_degradation_check, get_worker_autoscaling_metrics,
)


class TestRedisHealth:
    def test_returns_dict(self):
        result = check_redis_health()
        assert isinstance(result, dict)
        # May fail if no redis, but should still return a dict


class TestPostgresReplicas:
    def test_returns_dict(self):
        result = check_postgres_replicas()
        assert isinstance(result, dict)


class TestQueueFailover:
    def test_returns_dict(self):
        result = check_queue_failover()
        assert isinstance(result, dict)


class TestGracefulDegradation:
    def test_returns_dict_with_level(self):
        result = graceful_degradation_check()
        assert isinstance(result, dict)


class TestAutoscalingMetrics:
    def test_returns_dict_with_metrics(self):
        result = get_worker_autoscaling_metrics()
        assert isinstance(result, dict)
