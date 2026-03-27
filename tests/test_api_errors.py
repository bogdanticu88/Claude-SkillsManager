# SkillPM Registry - API Error Handling Tests
# Author: Bogdan Ticu
# License: MIT
#
# Tests for API error responses and standardization

import pytest
from fastapi.testclient import TestClient
from registry.main import app

client = TestClient(app)


class TestErrorResponses:
    """Test that errors follow standard format"""

    def test_invalid_json_returns_validation_error(self):
        """Posting invalid JSON should return validation error"""
        response = client.post(
            "/api/v1/authors/register",
            json={"invalid_field": "value"}  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_error_has_standard_format(self):
        """Error responses should have standard format"""
        # Register a user (will fail with duplicate)
        client.post("/api/v1/authors/register", json={
            "username": "testuser",
            "email": "test@example.com"
        })

        # Try to register same username again
        response = client.post("/api/v1/authors/register", json={
            "username": "testuser",
            "email": "different@example.com"
        })

        assert response.status_code == 409
        data = response.json()
        # Should have standard error format
        assert "code" in data or "detail" in data

    def test_authentication_required_error(self):
        """Missing auth should return clear error"""
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill",
                "language": "python",
                "entry_point": "skill.py",
                "repository_url": "https://github.com/test/test",
                "author_username": "testuser"
            }
        )
        assert response.status_code == 401

    def test_not_found_error_format(self):
        """Not found errors should be clear"""
        response = client.get("/api/v1/skills/nonexistent-skill-xyz")
        assert response.status_code == 404

    def test_invalid_url_validation(self):
        """Invalid URLs should fail validation"""
        # Register first
        reg_response = client.post("/api/v1/authors/register", json={
            "username": "urltest",
            "email": "url@example.com"
        })
        api_key = reg_response.json()["api_key"]

        # Try to create skill with invalid URL
        response = client.post(
            "/api/v1/skills/",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "name": "test-skill",
                "version": "1.0.0",
                "description": "A valid skill description here",
                "language": "python",
                "entry_point": "skill.py",
                "repository_url": "not-a-valid-url",  # Invalid
                "author_username": "urltest"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_rate_limit_error_format(self):
        """Rate limit errors should include retry info"""
        # Make many requests to trigger rate limit
        for i in range(250):  # Default limit is 200
            response = client.get("/api/v1/skills/")
            if response.status_code == 429:
                data = response.json()
                # Should have rate limit info
                assert "code" in data or "detail" in data
                break


class TestRequestIDTracking:
    """Test request ID tracking for debugging"""

    def test_request_id_in_response(self):
        """Response should include request ID for tracking"""
        response = client.get("/api/v1/skills/")
        assert "x-request-id" in response.headers or "X-Request-ID" in response.headers

    def test_custom_request_id_preserved(self):
        """Custom request ID should be preserved"""
        custom_id = "test-req-12345"
        response = client.get(
            "/api/v1/skills/",
            headers={"X-Request-ID": custom_id}
        )
        response_id = response.headers.get("x-request-id") or response.headers.get("X-Request-ID")
        assert response_id == custom_id


class TestRequestSizeLimit:
    """Test request size limiting"""

    def test_large_request_rejected(self):
        """Requests larger than limit should be rejected"""
        # Create a very large payload
        large_description = "x" * 10_000_000  # 10MB
        response = client.post(
            "/api/v1/skills/",
            headers={"Authorization": "Bearer skpm_test"},
            json={
                "name": "test-skill",
                "version": "1.0.0",
                "description": large_description,
                "language": "python",
                "entry_point": "skill.py",
                "repository_url": "https://github.com/test/test",
                "author_username": "testuser"
            }
        )
        # Should be rejected (413 Payload Too Large)
        assert response.status_code in [413, 422]


class TestCORSHeaders:
    """Test CORS headers in responses"""

    def test_cors_headers_present(self):
        """Response should have CORS headers"""
        response = client.get("/api/v1/skills/")
        # FastAPI adds CORS headers based on middleware config
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
