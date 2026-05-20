"""Tests for Enterprise Integrations — lightweight, no external calls."""
import uuid
import pytest
from app.services.integrations.webhooks import (
    generate_api_token, validate_api_token, revoke_api_token,
    register_webhook,
)


class TestApiTokens:
    def test_generate_returns_token_dict(self):
        result = generate_api_token(uuid.uuid4(), "Test Token", ["sla:view"])
        assert isinstance(result, dict)

    def test_validate_returns_none_for_bogus_token(self):
        result = validate_api_token("bogus-token-string")
        assert result is None

    def test_revoke_does_not_raise(self):
        revoke_api_token(uuid.uuid4())


class TestWebhooks:
    def test_register_returns_webhook_dict(self):
        result = register_webhook(uuid.uuid4(), "Test Webhook", "https://example.com/hook", ["sla.breach"])
        assert isinstance(result, dict)
