"""Tests for AI Copilot V2 — lightweight, no external dependencies."""
from app.services.ai.copilot_v2 import (
    conversational_query, generate_ai_dashboard, clear_conversation_history,
)


class TestConversationalQuery:
    def test_returns_response_for_general_question(self):
        result = conversational_query("test-session", "How is my SLA compliance doing?")
        assert isinstance(result, dict)

    def test_returns_response_for_anomaly_question(self):
        result = conversational_query("test-session", "Why did SLA drop last week?")
        assert isinstance(result, dict)

    def test_returns_response_for_staffing_question(self):
        result = conversational_query("test-session", "How many agents do I need next week?")
        assert isinstance(result, dict)

    def test_clears_conversation(self):
        conversational_query("test-clear-session", "Hello")
        clear_conversation_history("test-clear-session")
        result = conversational_query("test-clear-session", "Hello again")
        assert isinstance(result, dict)


class TestGenerateAIDashboard:
    def test_returns_dashboard_config_for_general(self):
        result = generate_ai_dashboard(focus="general")
        assert isinstance(result, dict)

    def test_returns_dashboard_config_for_operations(self):
        result = generate_ai_dashboard(focus="operations")
        assert isinstance(result, dict)

    def test_returns_dashboard_config_for_analytics(self):
        result = generate_ai_dashboard(focus="analytics")
        assert isinstance(result, dict)
