"""Tests for admin queries, prompt templates, and system prompt with instructions."""

import sys
import os
import sqlite3
from pathlib import Path

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Fixtures — fresh in-memory database for each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temp file so each test gets a clean slate."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_file)

    # Re-import to pick up the monkeypatched DB_PATH
    import importlib
    import db.database
    importlib.reload(db.database)
    db.database.init_db()

    yield db_file


@pytest.fixture
def user_id():
    from db import queries
    return queries.create_user("admin@test.com", "hashedpw", "Admin")


@pytest.fixture
def workspace_id(user_id):
    from db import queries
    return queries.create_workspace("Test Workspace", user_id)


@pytest.fixture
def project_id(workspace_id, user_id):
    from db import queries
    return queries.create_project(workspace_id, user_id, "Test Project", "desc", "Always use blue theme")


# =========================================================================
# Test: Project Instructions
# =========================================================================

class TestProjectInstructions:
    def test_create_project_with_instructions(self, workspace_id, user_id):
        from db import queries
        pid = queries.create_project(workspace_id, user_id, "My Project", "desc", "Use EUR currency")
        project = queries.get_project_by_id(pid, workspace_id)
        assert project is not None
        assert project.instructions == "Use EUR currency"

    def test_create_project_without_instructions(self, workspace_id, user_id):
        from db import queries
        pid = queries.create_project(workspace_id, user_id, "Plain Project")
        project = queries.get_project_by_id(pid, workspace_id)
        assert project.instructions == ""

    def test_update_project_instructions(self, project_id, workspace_id):
        from db import queries
        queries.update_project(project_id, workspace_id, instructions="New instructions")
        project = queries.get_project_by_id(project_id, workspace_id)
        assert project.instructions == "New instructions"

    def test_clear_project_instructions(self, project_id, workspace_id):
        from db import queries
        queries.update_project(project_id, workspace_id, instructions="")
        project = queries.get_project_by_id(project_id, workspace_id)
        assert project.instructions == ""


# =========================================================================
# Test: Prompt Templates
# =========================================================================

class TestPromptTemplates:
    def test_create_template(self, project_id, user_id):
        from db import queries
        tid = queries.create_prompt_template(project_id, user_id, "Revenue Chart", "Show revenue over time")
        template = queries.get_prompt_template_by_id(tid)
        assert template is not None
        assert template.name == "Revenue Chart"
        assert template.prompt_text == "Show revenue over time"
        assert template.usage_count == 0

    def test_list_templates_for_project(self, project_id, user_id):
        from db import queries
        queries.create_prompt_template(project_id, user_id, "Template A", "prompt A")
        queries.create_prompt_template(project_id, user_id, "Template B", "prompt B")
        templates = queries.get_prompt_templates_for_project(project_id)
        assert len(templates) == 2

    def test_increment_template_usage(self, project_id, user_id):
        from db import queries
        tid = queries.create_prompt_template(project_id, user_id, "Test", "prompt")
        queries.increment_template_usage(tid)
        queries.increment_template_usage(tid)
        template = queries.get_prompt_template_by_id(tid)
        assert template.usage_count == 2

    def test_update_template(self, project_id, user_id):
        from db import queries
        tid = queries.create_prompt_template(project_id, user_id, "Old Name", "old prompt")
        queries.update_prompt_template(tid, name="New Name", prompt_text="new prompt")
        template = queries.get_prompt_template_by_id(tid)
        assert template.name == "New Name"
        assert template.prompt_text == "new prompt"

    def test_delete_template(self, project_id, user_id):
        from db import queries
        tid = queries.create_prompt_template(project_id, user_id, "Delete Me", "prompt")
        queries.delete_prompt_template(tid)
        assert queries.get_prompt_template_by_id(tid) is None

    def test_templates_sorted_by_usage(self, project_id, user_id):
        from db import queries
        tid_a = queries.create_prompt_template(project_id, user_id, "A", "prompt A")
        tid_b = queries.create_prompt_template(project_id, user_id, "B", "prompt B")
        queries.increment_template_usage(tid_b)
        queries.increment_template_usage(tid_b)
        queries.increment_template_usage(tid_a)
        templates = queries.get_prompt_templates_for_project(project_id)
        assert templates[0].name == "B"  # Higher usage comes first


# =========================================================================
# Test: System Prompt with Instructions
# =========================================================================

class TestSystemPrompt:
    def test_build_system_prompt_no_instructions(self):
        from prompts.prompt_builder import build_system_prompt
        from prompts.system_prompt import SYSTEM_PROMPT
        result = build_system_prompt()
        assert result == SYSTEM_PROMPT

    def test_build_system_prompt_with_instructions(self):
        from prompts.prompt_builder import build_system_prompt
        result = build_system_prompt(project_instructions="Always use blue charts")
        assert "PROJECT-SPECIFIC INSTRUCTIONS" in result
        assert "Always use blue charts" in result

    def test_build_system_prompt_empty_instructions(self):
        from prompts.prompt_builder import build_system_prompt
        from prompts.system_prompt import SYSTEM_PROMPT
        result = build_system_prompt(project_instructions="")
        assert result == SYSTEM_PROMPT

    def test_build_system_prompt_whitespace_instructions(self):
        from prompts.prompt_builder import build_system_prompt
        from prompts.system_prompt import SYSTEM_PROMPT
        result = build_system_prompt(project_instructions="   ")
        assert result == SYSTEM_PROMPT


# =========================================================================
# Test: Admin — Superadmin
# =========================================================================

class TestSuperadmin:
    def test_user_default_not_superadmin(self, user_id):
        from db import queries
        user = queries.get_user_by_id(user_id)
        assert user.is_superadmin is False

    def test_set_superadmin(self, user_id):
        from db import queries
        queries.set_user_superadmin(user_id, True)
        user = queries.get_user_by_id(user_id)
        assert user.is_superadmin is True

    def test_set_superadmin_by_email(self, user_id):
        from db import queries
        queries.set_superadmin_by_email("admin@test.com")
        user = queries.get_user_by_id(user_id)
        assert user.is_superadmin is True

    def test_set_superadmin_by_email_nonexistent(self):
        from db import queries
        # Should not raise — just affects 0 rows
        queries.set_superadmin_by_email("nobody@test.com")

    def test_revoke_superadmin(self, user_id):
        from db import queries
        queries.set_user_superadmin(user_id, True)
        queries.set_user_superadmin(user_id, False)
        user = queries.get_user_by_id(user_id)
        assert user.is_superadmin is False


# =========================================================================
# Test: Admin Queries
# =========================================================================

class TestAdminQueries:
    def test_count_all_users(self, user_id):
        from db import queries
        assert queries.count_all_users() >= 1

    def test_get_all_users(self, user_id):
        from db import queries
        users = queries.get_all_users()
        assert len(users) >= 1
        assert any(u.id == user_id for u in users)

    def test_count_all_workspaces(self, workspace_id):
        from db import queries
        assert queries.count_all_workspaces() >= 1

    def test_get_all_workspaces(self, workspace_id):
        from db import queries
        workspaces = queries.get_all_workspaces()
        assert len(workspaces) >= 1

    def test_total_credits_consumed_zero(self):
        from db import queries
        assert queries.get_total_credits_consumed() == 0

    def test_total_api_calls_zero(self):
        from db import queries
        assert queries.get_total_api_calls() == 0

    def test_total_revenue_zero(self):
        from db import queries
        assert queries.get_total_revenue_cents() == 0


# =========================================================================
# Test: Audit Log
# =========================================================================

class TestAuditLog:
    def test_create_audit_log(self, user_id):
        from db import queries
        aid = queries.create_audit_log(user_id, "test_action", "user", entity_id=user_id)
        assert aid is not None

    def test_get_audit_log(self, user_id):
        from db import queries
        queries.create_audit_log(user_id, "action1", "user")
        queries.create_audit_log(user_id, "action2", "workspace")
        entries = queries.get_audit_log()
        assert len(entries) == 2

    def test_filter_audit_by_entity(self, user_id):
        from db import queries
        queries.create_audit_log(user_id, "action1", "user")
        queries.create_audit_log(user_id, "action2", "workspace")
        entries = queries.get_audit_log(entity_type="user")
        assert len(entries) == 1
        assert entries[0].entity_type == "user"

    def test_audit_log_details_json(self, user_id):
        from db import queries
        queries.create_audit_log(user_id, "change_tier", "workspace", details={"tier": "pro"})
        entries = queries.get_audit_log()
        assert entries[0].details == {"tier": "pro"}


# =========================================================================
# Test: System Settings
# =========================================================================

class TestSystemSettings:
    def test_get_nonexistent_setting(self):
        from db import queries
        assert queries.get_system_setting("nonexistent") is None

    def test_set_and_get_setting(self, user_id):
        from db import queries
        queries.set_system_setting("test_key", "test_value", user_id)
        assert queries.get_system_setting("test_key") == "test_value"

    def test_upsert_setting(self, user_id):
        from db import queries
        queries.set_system_setting("key1", "value1", user_id)
        queries.set_system_setting("key1", "value2", user_id)
        assert queries.get_system_setting("key1") == "value2"

    def test_get_all_settings(self, user_id):
        from db import queries
        queries.set_system_setting("a", "1", user_id)
        queries.set_system_setting("b", "2", user_id)
        settings = queries.get_all_system_settings()
        assert settings["a"] == "1"
        assert settings["b"] == "2"
