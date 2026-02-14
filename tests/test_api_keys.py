"""Tests for API key service — creation, verification, revocation."""

import pytest
from db.database import init_db
from db import queries
from auth.authenticator import register_user
from services.api_key_service import (
    generate_api_key, create_api_key, verify_api_key,
    revoke_api_key, list_api_keys, API_KEY_PREFIX,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("db.database.DB_PATH", db_path)
    init_db()
    yield


@pytest.fixture
def workspace():
    _, uid = register_user("api@test.com", "password123", "API Tester")
    ws_id = queries.create_workspace("API WS", uid, tier="pro")
    return uid, ws_id


class TestKeyGeneration:
    def test_key_has_prefix(self):
        full_key, key_hash, key_prefix = generate_api_key()
        assert full_key.startswith(API_KEY_PREFIX)

    def test_key_prefix_length(self):
        full_key, key_hash, key_prefix = generate_api_key()
        assert len(key_prefix) == 12

    def test_unique_keys(self):
        keys = {generate_api_key()[0] for _ in range(100)}
        assert len(keys) == 100  # All unique


class TestKeyCreation:
    def test_create_key(self, workspace):
        uid, ws_id = workspace
        full_key, key_id = create_api_key(ws_id, uid, "Test Key")
        assert full_key.startswith(API_KEY_PREFIX)
        assert len(key_id) > 0

    def test_default_permissions(self, workspace):
        uid, ws_id = workspace
        full_key, key_id = create_api_key(ws_id, uid, "Default Perms")
        key = verify_api_key(full_key)
        assert key is not None
        assert key.permissions == {"read": True, "write": True, "analyze": True}

    def test_custom_permissions(self, workspace):
        uid, ws_id = workspace
        perms = {"read": True, "write": False, "analyze": False}
        full_key, key_id = create_api_key(ws_id, uid, "Read Only", perms)
        key = verify_api_key(full_key)
        assert key.permissions["read"] is True
        assert key.permissions["write"] is False


class TestKeyVerification:
    def test_valid_key(self, workspace):
        uid, ws_id = workspace
        full_key, _ = create_api_key(ws_id, uid, "Valid Key")
        key = verify_api_key(full_key)
        assert key is not None
        assert key.workspace_id == ws_id

    def test_invalid_key(self):
        key = verify_api_key("ip_invalid_key_that_doesnt_exist")
        assert key is None

    def test_no_prefix(self):
        key = verify_api_key("not_an_api_key")
        assert key is None

    def test_empty_key(self):
        key = verify_api_key("")
        assert key is None

    def test_none_key(self):
        key = verify_api_key(None)
        assert key is None


class TestKeyRevocation:
    def test_revoke_key(self, workspace):
        uid, ws_id = workspace
        full_key, key_id = create_api_key(ws_id, uid, "Revocable")

        # Key works before revocation
        assert verify_api_key(full_key) is not None

        # Revoke
        revoke_api_key(key_id)

        # Key should no longer work
        assert verify_api_key(full_key) is None

    def test_list_excludes_revoked(self, workspace):
        uid, ws_id = workspace
        _, key_id1 = create_api_key(ws_id, uid, "Active")
        _, key_id2 = create_api_key(ws_id, uid, "To Revoke")

        revoke_api_key(key_id2)

        active_keys = list_api_keys(ws_id)
        assert len(active_keys) == 1
        assert active_keys[0].name == "Active"


class TestRateLimiter:
    def test_token_bucket_allows_requests(self):
        from api.rate_limiter import TokenBucket
        bucket = TokenBucket(rate=10, period=60)
        for _ in range(10):
            assert bucket.allow("test_key")

    def test_token_bucket_blocks_excess(self):
        from api.rate_limiter import TokenBucket
        bucket = TokenBucket(rate=5, period=60)
        for _ in range(5):
            bucket.allow("test_key")
        assert not bucket.allow("test_key")

    def test_different_keys_independent(self):
        from api.rate_limiter import TokenBucket
        bucket = TokenBucket(rate=3, period=60)
        for _ in range(3):
            bucket.allow("key_a")
        # key_a is exhausted
        assert not bucket.allow("key_a")
        # key_b should still work
        assert bucket.allow("key_b")
