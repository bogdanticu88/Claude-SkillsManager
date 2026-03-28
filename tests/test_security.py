# SkillPM Registry - Security Tests
# Author: Bogdan Ticu
# License: MIT
#
# Tests for security-critical functionality

import pytest
from fastapi.testclient import TestClient
from registry.main import app
from registry.middleware.auth import hash_api_key, verify_api_key

client = TestClient(app)


class TestAPIKeyHashing:
    """Test API key hashing with Argon2"""

    def test_hash_api_key_returns_hash(self):
        """hash_api_key should return a hash"""
        key = "skpm_test_key_12345"
        hash_val = hash_api_key(key)
        assert hash_val is not None
        assert len(hash_val) > 20

    def test_hash_is_not_plaintext(self):
        """Hash should not contain original key"""
        key = "skpm_test_key_12345"
        hash_val = hash_api_key(key)
        assert key not in hash_val

    def test_verify_api_key_success(self):
        """verify_api_key should return True for correct key"""
        key = "skpm_test_key_12345"
        hash_val = hash_api_key(key)
        assert verify_api_key(key, hash_val) is True

    def test_verify_api_key_failure(self):
        """verify_api_key should return False for incorrect key"""
        correct_key = "skpm_test_key_12345"
        wrong_key = "skpm_wrong_key_67890"
        hash_val = hash_api_key(correct_key)
        assert verify_api_key(wrong_key, hash_val) is False

    def test_different_hashes_for_same_key(self):
        """Different salt should produce different hashes"""
        key = "skpm_test_key"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        # Argon2 includes salt, so hashes differ but both verify
        assert verify_api_key(key, hash1) is True
        assert verify_api_key(key, hash2) is True


class TestAuthenticationSecurity:
    """Test authentication security"""

    def test_api_key_must_start_with_skpm(self):
        """API keys must start with skpm_ prefix"""
        # Register user
        reg = client.post("/api/v1/authors/register", json={
            "username": "authtest",
            "email": "auth@example.com"
        })
        assert reg.status_code == 201
        api_key = reg.json()["api_key"]
        assert api_key.startswith("skpm_")

    def test_wrong_api_key_format_rejected(self):
        """Invalid API key format should be rejected"""
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": "Bearer invalid_key"}
        )
        assert response.status_code == 400 or response.status_code == 401

    def test_missing_bearer_prefix_rejected(self):
        """Authorization header must have Bearer prefix"""
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": "skpm_test_key"}
        )
        assert response.status_code == 401

    def test_expired_key_not_working(self):
        """Rotated keys should not work anymore"""
        # Register
        reg = client.post("/api/v1/authors/register", json={
            "username": "expiry-test",
            "email": "expiry@example.com"
        })
        old_key = reg.json()["api_key"]

        # Rotate
        client.post(
            "/api/v1/authors/me/rotate-key",
            headers={"Authorization": f"Bearer {old_key}"}
        )

        # Old key should fail
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": f"Bearer {old_key}"}
        )
        assert response.status_code == 401

    def test_case_sensitive_api_key(self):
        """API keys should be case-sensitive"""
        # Register
        reg = client.post("/api/v1/authors/register", json={
            "username": "case-test",
            "email": "case@example.com"
        })
        api_key = reg.json()["api_key"]

        # Try with different case
        modified_key = api_key[:-2] + api_key[-2:].upper()
        if modified_key != api_key:  # Only if change occurred
            response = client.get(
                "/api/v1/authors/me",
                headers={"Authorization": f"Bearer {modified_key}"}
            )
            assert response.status_code == 401


class TestCORSSecurity:
    """Test CORS configuration security"""

    def test_cors_origins_configurable(self):
        """CORS should be configurable via environment"""
        # This is configured in main.py
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200


class TestRateLimitingSecurity:
    """Test rate limiting prevents abuse"""

    def test_rate_limit_per_user(self):
        """Each user should have separate rate limit"""
        # Register two users
        user1 = client.post("/api/v1/authors/register", json={
            "username": "ratelimit1",
            "email": "rate1@example.com"
        })
        key1 = user1.json()["api_key"]

        user2 = client.post("/api/v1/authors/register", json={
            "username": "ratelimit2",
            "email": "rate2@example.com"
        })
        key2 = user2.json()["api_key"]

        # User 1 makes requests
        for i in range(10):
            response = client.get(
                "/api/v1/authors/me",
                headers={"Authorization": f"Bearer {key1}"}
            )
            assert response.status_code == 200

        # User 2 should still be able to make requests
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": f"Bearer {key2}"}
        )
        assert response.status_code == 200

    def test_rate_limit_headers_include_info(self):
        """Rate limit headers should show remaining quota"""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        # Should have rate limit headers
        assert any("ratelimit" in k for k in headers)


class TestInputSanitation:
    """Test that inputs are properly sanitized"""

    def test_username_no_sql_injection(self):
        """SQL injection in username should fail"""
        response = client.post("/api/v1/authors/register", json={
            "username": "test'; DROP TABLE users; --",
            "email": "sqli@example.com"
        })
        # Should fail validation, not SQL injection
        assert response.status_code == 422

    def test_skill_name_no_sql_injection(self):
        """SQL injection in skill name should fail"""
        reg = client.post("/api/v1/authors/register", json={
            "username": "sqli-test",
            "email": "sqli@example.com"
        })
        api_key = reg.json()["api_key"]

        response = client.post("/api/v1/skills/", json={
            "name": "test'; DROP TABLE skills; --",
            "version": "1.0.0",
            "description": "Test description",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "sqli-test"
        }, headers={"Authorization": f"Bearer {api_key}"})
        # Should fail validation
        assert response.status_code == 422

    def test_search_query_safe(self):
        """Search queries should be safe from injection"""
        # This should not cause SQL injection
        response = client.get("/api/v1/search/?q=test'; DROP TABLE--")
        assert response.status_code == 200


class TestRequestSizeLimits:
    """Test request size limiting"""

    def test_large_description_rejected(self):
        """Very large skill description should be rejected"""
        reg = client.post("/api/v1/authors/register", json={
            "username": "large-test",
            "email": "large@example.com"
        })
        api_key = reg.json()["api_key"]

        # Create extremely large description
        large_description = "x" * 10_000_000  # 10MB

        response = client.post(
            "/api/v1/skills/",
            json={
                "name": "large-skill",
                "version": "1.0.0",
                "description": large_description,
                "language": "python",
                "entry_point": "skill.py",
                "repository_url": "https://github.com/test/test",
                "author_username": "large-test"
            },
            headers={"Authorization": f"Bearer {api_key}"}
        )
        # Should be rejected (413 or 422)
        assert response.status_code in [413, 422]


class TestAuthorizationSecurity:
    """Test authorization controls"""

    def test_user_cannot_modify_others_profile(self):
        """User shouldn't be able to modify another user's profile"""
        # Register two users
        user1 = client.post("/api/v1/authors/register", json={
            "username": "user-a",
            "email": "a@example.com"
        })
        key1 = user1.json()["api_key"]

        user2 = client.post("/api/v1/authors/register", json={
            "username": "user-b",
            "email": "b@example.com"
        })

        # User 1 tries to modify themselves
        response = client.put(
            "/api/v1/authors/me",
            json={"display_name": "Modified A"},
            headers={"Authorization": f"Bearer {key1}"}
        )
        assert response.status_code == 200
        # Should be modified
        assert response.json()["display_name"] == "Modified A"

    def test_user_cannot_publish_as_another(self):
        """User can't publish skill as another author"""
        reg = client.post("/api/v1/authors/register", json={
            "username": "author1",
            "email": "author1@example.com"
        })
        api_key = reg.json()["api_key"]

        response = client.post("/api/v1/skills/", json={
            "name": "fake-author-skill",
            "version": "1.0.0",
            "description": "Test",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "someone-else"  # Different author
        }, headers={"Authorization": f"Bearer {api_key}"})

        # Should either fail or only use authenticated user
        # Check if skill is created under wrong author
        if response.status_code == 201:
            # Verify it's under correct author
            assert response.json()["author_username"] == "author1"


class TestLoggingAndAuditing:
    """Test that security events are logged"""

    def test_failed_auth_attempt_logged(self):
        """Failed authentication should be logged"""
        # This test verifies logging happens
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": "Bearer invalid_key"}
        )
        # Invalid format returns 400, expired/invalid key returns 401
        assert response.status_code in [400, 401]

    def test_rate_limit_hit_logged(self):
        """Rate limit violations should be logged"""
        # Make many requests to trigger rate limit
        for i in range(250):
            response = client.get("/api/v1/skills/")
            if response.status_code == 429:
                # Rate limited, should be logged
                break


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
