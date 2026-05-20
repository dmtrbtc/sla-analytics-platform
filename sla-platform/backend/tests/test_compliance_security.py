"""Tests for Security + Compliance V2 — lightweight, no live DB dependency."""
import pytest
from unittest.mock import MagicMock
from app.services.compliance.security_v2 import (
    generate_saml_metadata, validate_session_security,
    encrypt_export_data, decrypt_export_data,
    get_audit_retention_status, apply_audit_retention_policy,
    get_compliance_dashboard,
)


class TestSAMLMetaData:
    def test_generates_dict_with_entity_id(self):
        result = generate_saml_metadata("https://app.example.com", "https://app.example.com/acs", "https://app.example.com")
        assert isinstance(result, dict)
        assert "entity_id" in result
        assert "acs_url" in result


class TestSessionSecurity:
    def test_returns_dict_for_mock_db(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 0
        mock_db.execute.return_value.first.return_value = None
        mock_db.execute.return_value.all.return_value = []
        result = validate_session_security(mock_db, "test-user-id", "192.168.1.1", "Mozilla/5.0")
        assert isinstance(result, dict)
        assert "score" in result or "risk" in result or "valid" in result


class TestExportEncryption:
    def test_encrypts_and_decrypts_roundtrip(self):
        data = "test-sensitive-export-data-123"
        encrypted = encrypt_export_data(data)
        assert isinstance(encrypted, dict)

        enc_val = encrypted.get("data") or encrypted.get("encrypted", "")
        decrypted = decrypt_export_data(enc_val)
        dec_val = decrypted.get("data") or decrypted.get("decrypted", "")
        assert dec_val == data

    def test_decrypt_invalid_handles_gracefully(self):
        result = decrypt_export_data("invalid-encrypted-data!")
        assert isinstance(result, dict)


class TestAuditRetention:
    def test_returns_status_dict(self):
        result = get_audit_retention_status()
        assert isinstance(result, dict)

    def test_apply_policy_returns_result(self):
        result = apply_audit_retention_policy(retention_days=90)
        assert isinstance(result, dict)


class TestComplianceDashboard:
    def test_returns_scored_dashboard(self):
        result = get_compliance_dashboard()
        assert isinstance(result, dict)
