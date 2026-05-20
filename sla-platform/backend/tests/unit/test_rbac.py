"""Tests for Advanced RBAC — matches actual permission matrix format."""
import pytest
from app.services.rbac.permissions import (
    has_permission, get_user_permissions, get_role_permissions,
    PERMISSION_MATRIX, ACCESS_GROUPS,
)


class MockUser:
    def __init__(self, role="viewer"):
        self.role = role
        self.id = "test-id"


class TestPermissionMatrix:
    def test_has_required_permissions(self):
        for perm in ["sla:view", "ticket:view", "dashboard:view", "report:view", "import:view"]:
            assert perm in PERMISSION_MATRIX

    def test_has_access_groups(self):
        for g in ["admin_full", "analyst_standard", "team_lead_limited", "viewer_readonly"]:
            assert g in ACCESS_GROUPS


class TestHasPermission:
    def test_admin_has_any(self):
        user = MockUser(role="admin")
        for perm in ["dashboard:view", "sla:config", "org:admin", "billing:admin"]:
            assert has_permission(user, perm)

    def test_viewer_has_view_only(self):
        user = MockUser(role="viewer")
        assert has_permission(user, "sla:view")
        assert has_permission(user, "dashboard:view")
        assert not has_permission(user, "sla:config")
        assert not has_permission(user, "org:admin")

    def test_unknown_role_returns_false(self):
        user = MockUser(role="unknown")
        assert not has_permission(user, "sla:view")

    def test_unknown_permission_returns_false(self):
        user = MockUser(role="admin")
        assert not has_permission(user, "nonexistent:perm")


class TestGetUserPermissions:
    def test_returns_list_for_admin(self):
        user = MockUser(role="admin")
        perms = get_user_permissions(user)
        assert len(perms) > 0
        assert len(perms) == len(PERMISSION_MATRIX)

    def test_viewer_has_limited_perms(self):
        user = MockUser(role="viewer")
        perms = get_user_permissions(user)
        assert len(perms) < len(PERMISSION_MATRIX)


class TestGetRolePermissions:
    def test_returns_all_for_admin(self):
        perms = get_role_permissions("admin")
        assert len(perms) == len(PERMISSION_MATRIX)

    def test_returns_limited_for_viewer(self):
        perms = get_role_permissions("viewer")
        assert len(perms) <= len(PERMISSION_MATRIX)

    def test_unknown_role_returns_viewer_default(self):
        perms = get_role_permissions("nonexistent")
        assert isinstance(perms, list)
