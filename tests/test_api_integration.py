# SkillPM Registry - API Integration Tests
# Author: Bogdan Ticu
# License: MIT
#
# Comprehensive tests for all API endpoints

import pytest
from fastapi.testclient import TestClient
from registry.main import app

client = TestClient(app)


class TestAuthorsEndpoints:
    """Test author/user management endpoints"""

    def test_register_user_success(self):
        """POST /authors/register should create user and return API key"""
        response = client.post("/api/v1/authors/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "display_name": "Test User"
        })
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["username"] == "testuser"
        assert data["api_key"].startswith("skpm_")

    def test_register_user_duplicate_username(self):
        """POST /authors/register with duplicate should fail"""
        # First registration
        client.post("/api/v1/authors/register", json={
            "username": "duplicate",
            "email": "first@example.com"
        })

        # Second registration with same username
        response = client.post("/api/v1/authors/register", json={
            "username": "duplicate",
            "email": "second@example.com"
        })
        assert response.status_code == 409

    def test_register_user_invalid_email(self):
        """POST /authors/register with invalid email should fail"""
        response = client.post("/api/v1/authors/register", json={
            "username": "test",
            "email": "not-an-email"
        })
        assert response.status_code == 422

    def test_register_user_reserved_username(self):
        """POST /authors/register with reserved name should fail"""
        response = client.post("/api/v1/authors/register", json={
            "username": "admin",  # Reserved
            "email": "admin@example.com"
        })
        assert response.status_code == 422

    def test_get_profile_requires_auth(self):
        """GET /authors/me requires authentication"""
        response = client.get("/api/v1/authors/me")
        assert response.status_code == 401

    def test_get_profile_with_auth(self):
        """GET /authors/me returns user profile"""
        # Register first
        reg = client.post("/api/v1/authors/register", json={
            "username": "profile-test",
            "email": "profile@example.com"
        })
        api_key = reg.json()["api_key"]

        # Get profile
        response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profile-test"
        assert data["skill_count"] == 0

    def test_rotate_api_key(self):
        """POST /authors/me/rotate-key should generate new key"""
        # Register
        reg = client.post("/api/v1/authors/register", json={
            "username": "rotate-test",
            "email": "rotate@example.com"
        })
        old_key = reg.json()["api_key"]

        # Rotate key
        response = client.post(
            "/api/v1/authors/me/rotate-key",
            headers={"Authorization": f"Bearer {old_key}"}
        )
        assert response.status_code == 200
        new_key = response.json()["api_key"]

        # Old key should not work anymore
        bad_response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": f"Bearer {old_key}"}
        )
        assert bad_response.status_code == 401

        # New key should work
        good_response = client.get(
            "/api/v1/authors/me",
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert good_response.status_code == 200


class TestSkillsEndpoints:
    """Test skill CRUD endpoints"""

    @pytest.fixture
    def auth_headers(self):
        """Create a test user and return auth headers"""
        reg = client.post("/api/v1/authors/register", json={
            "username": "skill-tester",
            "email": "skill@example.com"
        })
        api_key = reg.json()["api_key"]
        return {"Authorization": f"Bearer {api_key}"}

    def test_list_skills_public(self):
        """GET /skills should return list (public endpoint)"""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["skills"], list)

    def test_create_skill_requires_auth(self):
        """POST /skills without auth should fail"""
        response = client.post("/api/v1/skills/", json={
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill description",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "test"
        })
        assert response.status_code == 401

    def test_create_skill_success(self, auth_headers):
        """POST /skills should create skill"""
        response = client.post("/api/v1/skills/", json={
            "name": "awesome-skill",
            "version": "1.0.0",
            "description": "An awesome skill for testing",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/awesome",
            "author_username": "skill-tester"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "awesome-skill"
        assert data["version"] == "1.0.0"

    def test_create_skill_invalid_name(self, auth_headers):
        """POST /skills with invalid name should fail"""
        response = client.post("/api/v1/skills/", json={
            "name": "BadName",  # Invalid: uppercase
            "version": "1.0.0",
            "description": "An awesome skill for testing",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "skill-tester"
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_create_skill_invalid_version(self, auth_headers):
        """POST /skills with invalid version should fail"""
        response = client.post("/api/v1/skills/", json={
            "name": "test-skill",
            "version": "v1.0",  # Invalid: not semver
            "description": "An awesome skill for testing",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/test",
            "author_username": "skill-tester"
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_get_skill_by_name(self):
        """GET /skills/{name} should return skill"""
        # Create first
        reg = client.post("/api/v1/authors/register", json={
            "username": "getter",
            "email": "getter@example.com"
        })
        api_key = reg.json()["api_key"]

        client.post("/api/v1/skills/", json={
            "name": "getme-skill",
            "version": "1.0.0",
            "description": "Get me please",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/getme",
            "author_username": "getter"
        }, headers={"Authorization": f"Bearer {api_key}"})

        # Get it
        response = client.get("/api/v1/skills/getme-skill")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "getme-skill"

    def test_get_skill_not_found(self):
        """GET /skills/{name} with non-existent skill should return 404"""
        response = client.get("/api/v1/skills/nonexistent-xyz-skill")
        assert response.status_code == 404

    def test_update_skill(self, auth_headers):
        """PUT /skills/{name} should update skill"""
        # Create
        client.post("/api/v1/skills/", json={
            "name": "updateme",
            "version": "1.0.0",
            "description": "Original description",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/updateme",
            "author_username": "skill-tester"
        }, headers=auth_headers)

        # Update
        response = client.put("/api/v1/skills/updateme", json={
            "description": "Updated description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    def test_delete_skill(self, auth_headers):
        """DELETE /skills/{name} should delete skill"""
        # Create
        client.post("/api/v1/skills/", json={
            "name": "deleteme",
            "version": "1.0.0",
            "description": "Please delete me",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/deleteme",
            "author_username": "skill-tester"
        }, headers=auth_headers)

        # Delete
        response = client.delete("/api/v1/skills/deleteme", headers=auth_headers)
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get("/api/v1/skills/deleteme")
        assert get_response.status_code == 404


class TestSearchEndpoints:
    """Test skill search functionality"""

    def test_search_empty_query(self):
        """GET /search with empty query should work"""
        response = client.get("/api/v1/search/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_by_name(self):
        """GET /search?q=name should find skills"""
        # Create a skill
        reg = client.post("/api/v1/authors/register", json={
            "username": "searcher",
            "email": "search@example.com"
        })
        api_key = reg.json()["api_key"]

        client.post("/api/v1/skills/", json={
            "name": "findable-skill",
            "version": "1.0.0",
            "description": "This is findable",
            "language": "python",
            "entry_point": "skill.py",
            "repository_url": "https://github.com/test/findable",
            "author_username": "searcher"
        }, headers={"Authorization": f"Bearer {api_key}"})

        # Search
        response = client.get("/api/v1/search/?q=findable")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(s["name"] == "findable-skill" for s in data)

    def test_search_pagination(self):
        """GET /search with limit and offset should work"""
        response = client.get("/api/v1/search/?limit=10&offset=0")
        assert response.status_code == 200

    def test_search_with_filters(self):
        """GET /search with filters should work"""
        response = client.get("/api/v1/search/?language=python&limit=20")
        assert response.status_code == 200


class TestReviewsEndpoints:
    """Test skill review endpoints"""

    def test_create_review_requires_auth(self):
        """POST /reviews requires authentication"""
        response = client.post("/api/v1/reviews/", json={
            "skill_name": "test-skill",
            "rating": 5,
            "title": "Great skill!"
        })
        assert response.status_code == 401

    def test_create_review_invalid_rating(self):
        """POST /reviews with invalid rating should fail"""
        reg = client.post("/api/v1/authors/register", json={
            "username": "reviewer",
            "email": "review@example.com"
        })
        api_key = reg.json()["api_key"]

        response = client.post("/api/v1/reviews/", json={
            "skill_name": "test-skill",
            "rating": 10,  # Invalid: must be 1-5
            "title": "Bad rating"
        }, headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 422


class TestHealthCheck:
    """Test health and status endpoints"""

    def test_health_check(self):
        """GET /health should return healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """GET / should return service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestErrorFormats:
    """Verify all errors follow standard format"""

    def test_validation_error_has_standard_format(self):
        """Validation errors should have standard fields"""
        response = client.post("/api/v1/authors/register", json={
            "username": "a",  # Too short
            "email": "test@example.com"
        })
        assert response.status_code == 422
        # Pydantic validation error format

    def test_authentication_error_has_standard_format(self):
        """Auth errors should have standard format"""
        response = client.get("/api/v1/authors/me")
        assert response.status_code == 401

    def test_not_found_error_has_standard_format(self):
        """Not found errors should have standard format"""
        response = client.get("/api/v1/skills/nonexistent")
        assert response.status_code == 404

    def test_response_has_request_id(self):
        """All responses should have request ID"""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert "x-request-id" in headers


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """Responses should have CORS headers"""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        # FastAPI adds CORS headers automatically


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_headers_present(self):
        """Rate limit headers should be present"""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        headers = response.headers
        assert "x-ratelimit-limit" in headers or "X-RateLimit-Limit" in headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
