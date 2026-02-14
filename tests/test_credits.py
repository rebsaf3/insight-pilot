"""Tests for the credit system — balance tracking, deductions, tier limits."""

import pytest
from db.database import init_db
from db import queries
from services import credit_service
from auth.authenticator import register_user


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Set up a fresh test database."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("db.database.DB_PATH", db_path)
    init_db()
    yield


@pytest.fixture
def user_and_workspace():
    """Create a user with a workspace and initial credits."""
    _, uid = register_user("credit@test.com", "password123", "Credit Tester")
    ws_id = queries.create_workspace("Test WS", uid, tier="pro")
    queries.create_subscription(ws_id, "pro", monthly_credit_allowance=500)
    # Add initial credits
    queries.add_credit_entry(ws_id, uid, 500, 500, "Initial credits")
    return uid, ws_id


class TestCreditBalance:
    def test_initial_balance(self, user_and_workspace):
        uid, ws_id = user_and_workspace
        balance = credit_service.get_balance(ws_id)
        assert balance == 500

    def test_deduct_credits(self, user_and_workspace):
        uid, ws_id = user_and_workspace
        credit_service.deduct_credits(ws_id, uid, 5, "Analysis")
        balance = credit_service.get_balance(ws_id)
        assert balance == 495

    def test_multiple_deductions(self, user_and_workspace):
        uid, ws_id = user_and_workspace
        credit_service.deduct_credits(ws_id, uid, 10, "Analysis 1")
        credit_service.deduct_credits(ws_id, uid, 20, "Analysis 2")
        credit_service.deduct_credits(ws_id, uid, 5, "Analysis 3")
        balance = credit_service.get_balance(ws_id)
        assert balance == 465

    def test_check_sufficient_credits(self, user_and_workspace):
        uid, ws_id = user_and_workspace
        has_enough, balance = credit_service.check_sufficient_credits(ws_id, 100)
        assert has_enough
        assert balance == 500

    def test_check_insufficient_credits(self, user_and_workspace):
        uid, ws_id = user_and_workspace
        has_enough, balance = credit_service.check_sufficient_credits(ws_id, 1000)
        assert not has_enough


class TestCreditCostCalculation:
    def test_minimum_one_credit(self):
        cost = credit_service.calculate_credit_cost(100)
        assert cost == 1

    def test_exact_thousand_tokens(self):
        cost = credit_service.calculate_credit_cost(1000)
        assert cost == 1

    def test_over_thousand_tokens(self):
        cost = credit_service.calculate_credit_cost(1500)
        assert cost == 2

    def test_large_token_count(self):
        cost = credit_service.calculate_credit_cost(5000)
        assert cost == 5

    def test_zero_tokens(self):
        cost = credit_service.calculate_credit_cost(0)
        assert cost == 1  # Minimum 1 credit


class TestTierLimits:
    def test_free_tier_upload_limit(self, tmp_path, monkeypatch):
        db_path = tmp_path / "limit_test.db"
        monkeypatch.setattr("config.settings.DB_PATH", db_path)
        monkeypatch.setattr("db.database.DB_PATH", db_path)
        init_db()

        _, uid = register_user("free@test.com", "password123", "Free User")
        ws_id = queries.create_workspace("Free WS", uid, tier="free")
        queries.create_subscription(ws_id, "free", monthly_credit_allowance=50)

        # First upload should be allowed
        allowed, msg = credit_service.check_upload_allowed(uid, ws_id)
        assert allowed

    def test_free_tier_file_size(self, tmp_path, monkeypatch):
        db_path = tmp_path / "size_test.db"
        monkeypatch.setattr("config.settings.DB_PATH", db_path)
        monkeypatch.setattr("db.database.DB_PATH", db_path)
        init_db()

        _, uid = register_user("freesize@test.com", "password123", "Free User")
        ws_id = queries.create_workspace("Free WS", uid, tier="free")

        # 10 MB limit for free tier
        size_ok, msg = credit_service.check_file_size_allowed(ws_id, 5 * 1024 * 1024)  # 5 MB
        assert size_ok

        size_ok, msg = credit_service.check_file_size_allowed(ws_id, 15 * 1024 * 1024)  # 15 MB
        assert not size_ok

    def test_pro_tier_export_allowed(self):
        from config.settings import TIERS
        assert TIERS["pro"]["export_enabled"] is True
        assert TIERS["free"]["export_enabled"] is False

    def test_free_tier_no_revisions(self):
        from config.settings import TIERS
        assert TIERS["free"]["max_revisions_per_report"] == 0
        assert TIERS["pro"]["max_revisions_per_report"] == -1  # unlimited
