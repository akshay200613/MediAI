"""
Unit tests for core/auth/jwt_handler.py
No external services required – pure logic tests.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from core.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from core.config.settings import settings


# ── hash_password / verify_password ──────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_produces_bcrypt_string(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_correct_password_verifies(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_empty_password_verifies_its_own_hash(self):
        h = hash_password("")
        assert verify_password("", h) is True

    def test_hashes_are_unique_for_same_input(self):
        """bcrypt salts should make each hash unique."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


# ── create_access_token ───────────────────────────────────────────────────────

class TestAccessToken:
    def test_token_contains_expected_claims(self):
        payload = {"sub": "user-1", "email": "user@test.com", "role": "admin"}
        token = create_access_token(payload)
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert decoded["sub"] == "user-1"
        assert decoded["email"] == "user@test.com"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "u1"})
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in decoded

    def test_expiry_is_within_configured_minutes(self):
        token = create_access_token({"sub": "u1"})
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        now = datetime.now(timezone.utc).timestamp()
        expected_exp = now + settings.jwt_access_token_expire_minutes * 60
        # Allow 5 s tolerance
        assert abs(decoded["exp"] - expected_exp) < 5

    def test_token_is_a_string(self):
        token = create_access_token({"sub": "u1"})
        assert isinstance(token, str)
        assert len(token) > 0


# ── create_refresh_token ──────────────────────────────────────────────────────

class TestRefreshToken:
    def test_refresh_token_has_type_refresh(self):
        token = create_refresh_token({"sub": "u1"})
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert decoded["type"] == "refresh"

    def test_refresh_token_expires_in_days(self):
        token = create_refresh_token({"sub": "u1"})
        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        now = datetime.now(timezone.utc).timestamp()
        expected_exp = now + settings.jwt_refresh_token_expire_days * 86400
        assert abs(decoded["exp"] - expected_exp) < 5


# ── decode_token ──────────────────────────────────────────────────────────────

class TestDecodeToken:
    def test_decode_valid_access_token(self):
        payload = {"sub": "u42", "email": "u@test.com", "role": "patient"}
        token = create_access_token(payload)
        decoded = decode_token(token)
        assert decoded["sub"] == "u42"
        assert decoded["email"] == "u@test.com"

    def test_decode_raises_on_tampered_token(self):
        token = create_access_token({"sub": "u1"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(tampered)

    def test_decode_raises_on_expired_token(self):
        expired_data = {
            "sub": "u1",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "type": "access",
        }
        expired_token = jwt.encode(
            expired_data,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(expired_token)

    def test_decode_raises_on_wrong_secret(self):
        import jose.exceptions
        payload = {"sub": "u1", "type": "access"}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(bad_token)


# ── create_token_pair ─────────────────────────────────────────────────────────

class TestTokenPair:
    def test_returns_two_element_tuple(self):
        pair = create_token_pair("uid1", "e@test.com", "admin")
        assert isinstance(pair, tuple)
        assert len(pair) == 2

    def test_first_is_access_second_is_refresh(self):
        access, refresh = create_token_pair("uid1", "e@test.com", "doctor")
        access_payload = decode_token(access)
        assert access_payload["type"] == "access"
        # Manually decode refresh (decode_token validates type=access, so use raw jose)
        refresh_payload = jwt.decode(
            refresh, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert refresh_payload["type"] == "refresh"

    def test_full_name_included_when_provided(self):
        access, _ = create_token_pair("uid1", "e@test.com", "doctor", full_name="Dr. House")
        payload = decode_token(access)
        assert payload["full_name"] == "Dr. House"

    def test_full_name_omitted_when_none(self):
        access, _ = create_token_pair("uid1", "e@test.com", "patient")
        payload = decode_token(access)
        assert "full_name" not in payload
