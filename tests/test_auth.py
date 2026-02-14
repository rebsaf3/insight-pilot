"""Tests for authentication, registration, and session management."""

import pytest
from db.database import init_db, get_db
from auth.authenticator import register_user, authenticate, hash_password, verify_password
from db import queries


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Set up a fresh in-memory test database for each test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("db.database.DB_PATH", db_path)
    init_db()
    yield


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secure_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt should generate different salts each time."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_successful_registration(self):
        success, result = register_user("test@example.com", "password123", "Test User")
        assert success
        assert len(result) > 0  # user_id

    def test_duplicate_email(self):
        register_user("dup@example.com", "password123", "User 1")
        success, result = register_user("dup@example.com", "password456", "User 2")
        assert not success
        assert "exists" in result.lower()

    def test_short_password(self):
        success, result = register_user("test2@example.com", "short", "Test")
        assert not success
        assert "8 characters" in result.lower()

    def test_empty_email(self):
        success, result = register_user("", "password123", "Test")
        assert not success

    def test_email_normalized_to_lowercase(self):
        register_user("TEST@EXAMPLE.COM", "password123", "Test")
        user = queries.get_user_by_email("test@example.com")
        assert user is not None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_successful_login(self):
        register_user("login@example.com", "password123", "Login Test")
        success, user, error = authenticate("login@example.com", "password123")
        assert success
        assert user is not None
        assert user.email == "login@example.com"

    def test_wrong_password(self):
        register_user("wrong@example.com", "password123", "Test")
        success, user, error = authenticate("wrong@example.com", "wrongpassword")
        assert not success
        assert user is None
        assert "invalid" in error.lower()

    def test_nonexistent_user(self):
        success, user, error = authenticate("nobody@example.com", "password123")
        assert not success
        assert user is None

    def test_sso_user_no_password(self):
        """SSO users should not be able to login with password."""
        uid = queries.create_user("sso@example.com", "", "SSO User")
        queries.update_user(uid, sso_provider="google", sso_provider_id="123")
        success, user, error = authenticate("sso@example.com", "anypassword")
        assert not success
        assert "sso" in error.lower()


# ---------------------------------------------------------------------------
# Multi-tenancy
# ---------------------------------------------------------------------------

class TestMultiTenancy:
    def test_workspace_isolation(self):
        """Projects in workspace A should not be visible in workspace B."""
        # Create two users with workspaces
        _, uid1 = register_user("user1@test.com", "password123", "User 1")
        _, uid2 = register_user("user2@test.com", "password123", "User 2")

        ws1 = queries.create_workspace("Workspace 1", uid1)
        ws2 = queries.create_workspace("Workspace 2", uid2)

        # Create projects in each
        p1 = queries.create_project(ws1, uid1, "Project A")
        p2 = queries.create_project(ws2, uid2, "Project B")

        # Query should only return projects for the correct workspace
        ws1_projects = queries.get_projects_for_workspace(ws1)
        ws2_projects = queries.get_projects_for_workspace(ws2)

        assert len(ws1_projects) == 1
        assert ws1_projects[0].name == "Project A"
        assert len(ws2_projects) == 1
        assert ws2_projects[0].name == "Project B"

    def test_project_scoped_by_workspace(self):
        """get_project_by_id should enforce workspace scope."""
        _, uid = register_user("scoped@test.com", "password123", "Test")
        ws1 = queries.create_workspace("WS1", uid)
        ws2 = queries.create_workspace("WS2", uid)

        pid = queries.create_project(ws1, uid, "Secret Project")

        # Should find in correct workspace
        assert queries.get_project_by_id(pid, ws1) is not None
        # Should NOT find in different workspace
        assert queries.get_project_by_id(pid, ws2) is None


# ---------------------------------------------------------------------------
# Roles & Permissions
# ---------------------------------------------------------------------------

class TestRoles:
    def test_owner_has_all_permissions(self):
        from config.settings import ROLE_PERMISSIONS
        owner_perms = ROLE_PERMISSIONS["owner"]
        assert "manage_billing" in owner_perms
        assert "delete_workspace" in owner_perms
        assert "manage_sso" in owner_perms
        assert "manage_api_keys" in owner_perms

    def test_viewer_limited_permissions(self):
        from config.settings import ROLE_PERMISSIONS
        viewer_perms = ROLE_PERMISSIONS["viewer"]
        assert "view_dashboards" in viewer_perms
        assert "upload_data" not in viewer_perms
        assert "run_analysis" not in viewer_perms
        assert "manage_billing" not in viewer_perms

    def test_member_role_assignment(self):
        _, uid1 = register_user("owner@test.com", "password123", "Owner")
        _, uid2 = register_user("member@test.com", "password123", "Member")

        ws_id = queries.create_workspace("Test WS", uid1)
        queries.add_workspace_member(ws_id, uid2, "viewer")

        role = queries.get_member_role(ws_id, uid2)
        assert role == "viewer"

        # Update role
        queries.update_member_role(ws_id, uid2, "admin")
        role = queries.get_member_role(ws_id, uid2)
        assert role == "admin"
