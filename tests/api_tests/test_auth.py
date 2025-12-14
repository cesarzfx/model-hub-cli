"""Tests for authentication endpoints and helpers."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.auth import (
    User,
    UserAuthenticationInfo,
    AuthenticationRequest,
    _hash_password,
    _verify_password,
    _generate_token,
    is_token_valid,
    consume_token,
    issued_tokens,
    _DEFAULT_ADMIN_PASSWORD_HASH,
    DEFAULT_ADMIN_USERNAME,
)

client = TestClient(app)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_hex_string(self):
        """Test that password hashing returns a hex string."""
        password = "testpassword123"
        hashed = _hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 32 bytes = 64 hex chars
        # Verify it's valid hex
        int(hashed, 16)

    def test_hash_password_is_deterministic(self):
        """Test that same password produces same hash."""
        password = "testpassword123"
        hash1 = _hash_password(password)
        hash2 = _hash_password(password)

        assert hash1 == hash2

    def test_hash_password_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = _hash_password("password1")
        hash2 = _hash_password("password2")

        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test password verification with correct password."""
        password = "correctpassword"
        hashed = _hash_password(password)

        assert _verify_password(hashed, password) is True

    def test_verify_password_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "correctpassword"
        hashed = _hash_password(password)

        assert _verify_password(hashed, "wrongpassword") is False

    def test_verify_password_default_admin(self):
        """Test that default admin password hash verifies correctly."""
        correct_password = (
            "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
        )

        assert _verify_password(_DEFAULT_ADMIN_PASSWORD_HASH, correct_password) is True

    def test_verify_password_default_admin_wrong(self):
        """Test that wrong password fails for default admin."""
        wrong_password = "wrongpassword"

        assert _verify_password(_DEFAULT_ADMIN_PASSWORD_HASH, wrong_password) is False


class TestTokenGeneration:
    """Tests for token generation."""

    def test_generate_token_returns_string(self):
        """Test that token generation returns a string."""
        token = _generate_token()
        assert isinstance(token, str)

    def test_generate_token_has_bearer_prefix(self):
        """Test that generated tokens start with 'bearer '."""
        token = _generate_token()
        assert token.startswith("bearer ")

    def test_generate_token_is_unique(self):
        """Test that generated tokens are unique."""
        token1 = _generate_token()
        token2 = _generate_token()
        assert token1 != token2


class TestTokenValidation:
    """Tests for token validation functions."""

    def setup_method(self):
        """Clear tokens before each test."""
        issued_tokens.clear()

    def test_is_token_valid_nonexistent_token(self):
        """Test that nonexistent token is invalid."""
        assert is_token_valid("bearer nonexistent") is False

    def test_is_token_valid_valid_token(self):
        """Test that a valid token is recognized."""
        token = "bearer testtoken123"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 9999999999.0,  # Far future
            "remaining_uses": 100,
        }

        assert is_token_valid(token) is True

    def test_is_token_valid_expired_token(self):
        """Test that expired token is invalid."""
        token = "bearer expiredtoken"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 0.0,  # Past
            "remaining_uses": 100,
        }

        assert is_token_valid(token) is False

    def test_is_token_valid_exhausted_token(self):
        """Test that exhausted token is invalid."""
        token = "bearer exhaustedtoken"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 9999999999.0,
            "remaining_uses": 0,
        }

        assert is_token_valid(token) is False

    def test_consume_token_valid(self):
        """Test consuming a valid token."""
        token = "bearer validtoken"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 9999999999.0,
            "remaining_uses": 100,
        }

        returned_user = consume_token(token)

        assert returned_user.name == user.name
        assert returned_user.is_admin == user.is_admin
        assert issued_tokens[token]["remaining_uses"] == 99

    def test_consume_token_invalid_raises_401(self):
        """Test that consuming invalid token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            consume_token("bearer invalidtoken")

        assert exc_info.value.status_code == 401
        assert "Invalid or missing token" in exc_info.value.detail

    def test_consume_token_expired_raises_401(self):
        """Test that consuming expired token raises 401."""
        token = "bearer expiredtoken"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 0.0,
            "remaining_uses": 100,
        }

        with pytest.raises(HTTPException) as exc_info:
            consume_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
        assert token not in issued_tokens  # Should be cleaned up

    def test_consume_token_exhausted_raises_401(self):
        """Test that consuming exhausted token raises 401."""
        token = "bearer exhaustedtoken"
        user = User(name="testuser", is_admin=False)

        issued_tokens[token] = {
            "user": user,
            "expires_at": 9999999999.0,
            "remaining_uses": 0,
        }

        with pytest.raises(HTTPException) as exc_info:
            consume_token(token)

        assert exc_info.value.status_code == 401
        assert "usage limit" in exc_info.value.detail.lower()
        assert token not in issued_tokens  # Should be cleaned up


class TestModels:
    """Tests for Pydantic models."""

    def test_user_model_creation(self):
        """Test User model creation."""
        user = User(name="testuser", is_admin=True)
        assert user.name == "testuser"
        assert user.is_admin is True

    def test_user_authentication_info_creation(self):
        """Test UserAuthenticationInfo model creation."""
        auth_info = UserAuthenticationInfo(password="secret123")
        assert auth_info.password == "secret123"

    def test_authentication_request_creation(self):
        """Test AuthenticationRequest model creation."""
        user = User(name="testuser", is_admin=False)
        secret = UserAuthenticationInfo(password="secret123")
        auth_req = AuthenticationRequest(user=user, secret=secret)

        assert auth_req.user.name == "testuser"
        assert auth_req.secret.password == "secret123"


class TestAuthenticateEndpoint:
    """Tests for /authenticate endpoint."""

    def test_authenticate_success_default_admin(self):
        """Test successful authentication with default admin."""
        response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )

        assert response.status_code == 200
        token = response.json()
        assert isinstance(token, str)
        assert token.startswith("bearer ")

    def test_authenticate_invalid_password(self):
        """Test authentication with wrong password."""
        response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {"password": "wrongpassword"},
            },
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_authenticate_invalid_username(self):
        """Test authentication with non-existent username."""
        response = client.put(
            "/authenticate",
            json={
                "user": {"name": "nonexistentuser", "is_admin": False},
                "secret": {"password": "anypassword"},
            },
        )

        assert response.status_code == 401

    def test_authenticate_admin_without_admin_flag(self):
        """Test admin account requires is_admin=True."""
        response = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": False},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )

        assert response.status_code == 401

    def test_authenticate_returns_unique_tokens(self):
        """Test that multiple authentications return unique tokens."""
        response1 = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )
        response2 = client.put(
            "/authenticate",
            json={
                "user": {"name": "ece30861defaultadminuser", "is_admin": True},
                "secret": {
                    "password": "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"
                },
            },
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() != response2.json()
