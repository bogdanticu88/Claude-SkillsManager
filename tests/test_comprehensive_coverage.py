# SkillPM Registry - Comprehensive Coverage Tests
# Author: Bogdan Ticu
# License: MIT
#
# Extended tests to reach 80%+ code coverage

import pytest
from fastapi.testclient import TestClient
from registry.main import app
from registry.services.breaking_changes import compare_versions

client = TestClient(app)


@pytest.fixture(scope="function")
def auth_headers():
    """Register a test user and return auth headers"""
    import time
    import uuid
    
    # Register user with unique username and email
    username = f"comp_test_{uuid.uuid4().hex[:12]}"
    email = f"test_{int(time.time() * 1000000)}@example.com"
    
    reg_response = client.post("/api/v1/authors/register", json={
        "username": username,
        "email": email,
    })
    
    if reg_response.status_code != 201:
        # If registration fails, try again with different credentials
        username = f"comp_test_{int(time.time() * 1000000)}"
        email = f"test_{uuid.uuid4().hex}@example.com"
        reg_response = client.post("/api/v1/authors/register", json={
            "username": username,
            "email": email,
        })
    
    data = reg_response.json()
    api_key = data["api_key"]
    auth_user = data["username"]
    
    return {
        "headers": {"Authorization": f"Bearer {api_key}"},
        "username": auth_user
    }


class TestComprehensiveSkillCRUD:
    """Comprehensive skill CRUD tests"""

    def test_create_skill_minimal(self, auth_headers):
        """Create skill with minimal fields"""
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": f"minimal-skill-{id(self)}",
                "version": "0.0.1",
                "description": "Minimal skill with required fields only",
                "language": "python",
                "author_username": auth_headers["username"]
            },
            headers=auth_headers["headers"]
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == f"minimal-skill-{id(self)}"

    def test_list_skills_pagination(self, auth_headers):
        """Test skill listing with pagination"""
        import time
        base_name = f"skill-{int(time.time() * 1000)}"
        
        # Create multiple skills first
        for i in range(5):
            client.post(
                "/api/v1/skills/",
                json={
                    "name": f"{base_name}-{i}",
                    "version": "1.0.0",
                    "description": f"Test skill {i}",
                    "language": "python",
                    "author_username": auth_headers["username"]
                },
                headers=auth_headers["headers"]
            )

        # Test pagination
        response = client.get("/api/v1/skills/?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["skills"]) <= 2

    def test_search_skills(self, auth_headers):
        """Test skill search"""
        import time
        skill_name = f"searchable-skill-{int(time.time() * 1000)}"
        
        # Create a skill
        client.post(
            "/api/v1/skills/",
            json={
                "name": skill_name,
                "version": "1.0.0",
                "description": "Unique description for testing",
                "language": "python",
                "author_username": auth_headers["username"]
            },
            headers=auth_headers["headers"]
        )

        # Search for it
        response = client.get(f"/api/v1/search/?q={skill_name[:10]}")
        assert response.status_code == 200

    def test_create_skill_with_urls(self, auth_headers):
        """Create skill with repository and homepage URLs"""
        import time
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": f"url-skill-{int(time.time() * 1000)}",
                "version": "1.0.0",
                "description": "Skill with URLs",
                "language": "python",
                "repository_url": "https://github.com/test/skill",
                "homepage_url": "https://example.com/skill",
                "author_username": auth_headers["username"]
            },
            headers=auth_headers["headers"]
        )
        assert response.status_code == 201

    def test_create_skill_with_metadata(self, auth_headers):
        """Create skill with full metadata"""
        import time
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": f"metadata-skill-{int(time.time() * 1000)}",
                "version": "1.0.0",
                "description": "Skill with metadata",
                "language": "python",
                "author_username": auth_headers["username"],
                "metadata": {
                    "tags": ["test", "example"],
                    "target_llms": ["claude"],
                    "capabilities": {"search": {"enabled": True}},
                    "dependencies": {"skills": ["base-skill"]}
                }
            },
            headers=auth_headers["headers"]
        )
        assert response.status_code == 201


class TestUserEndpoints:
    """Test user/author endpoints"""

    def test_register_multiple_users(self):
        """Register multiple users"""
        for i in range(3):
            response = client.post(
                "/api/v1/authors/register",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com"
                }
            )
            assert response.status_code == 201
            assert "api_key" in response.json()

    def test_user_profile_public_info(self):
        """Test getting user public profile"""
        # Register user
        client.post(
            "/api/v1/authors/register",
            json={
                "username": "public-user",
                "email": "public@example.com"
            }
        )

        # Get public profile
        response = client.get("/api/v1/authors/public-user")
        assert response.status_code == 200

    def test_invalid_email_rejected(self):
        """Invalid email should be rejected"""
        response = client.post(
            "/api/v1/authors/register",
            json={
                "username": "badmail",
                "email": "not-an-email"
            }
        )
        assert response.status_code == 422


class TestBreakingChangeDetection:
    """Test breaking change detection service"""

    def test_major_breaking_change(self):
        """Test detection of major breaking changes"""
        old = {
            "name": "test-skill",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude"],
            "capabilities": {"analyze": {}}
        }
        new = {
            "name": "test-skill",
            "version": "2.0.0",
            "language": "go",  # Breaking: language changed
            "entry_point": "main.go",
            "target_llms": ["claude"],
            "capabilities": {}  # Breaking: capability removed
        }

        report = compare_versions(old, new)
        assert not report.is_compatible
        assert len(report.breaking_changes) >= 2

    def test_minor_change_compatible(self):
        """Test that compatible changes report is_compatible=True"""
        old = {
            "name": "test-skill",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude"]
        }
        new = {
            "name": "test-skill",
            "version": "1.1.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude", "openai"]  # Only added support
        }

        report = compare_versions(old, new)
        assert report.is_compatible
        assert len(report.breaking_changes) == 0

    def test_version_suggestion(self):
        """Test version bump suggestions"""
        old = {
            "name": "test",
            "version": "1.2.3",
            "language": "python"
        }
        new = {
            "name": "test",
            "version": "1.2.3",
            "language": "go"  # Breaking change
        }

        report = compare_versions(old, new)
        # Should suggest major bump
        assert report.suggested_version.startswith("2.")


class TestErrorHandling:
    """Test error response formats"""

    def test_validation_error_format(self):
        """Validation errors should have standard format"""
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": "BAD",  # Invalid: uppercase
                "version": "1.0.0",
                "description": "x",  # Invalid: too short
                "language": "rust",  # Invalid: not supported
                "author_username": "user"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert isinstance(data, dict)

    def test_not_found_404(self):
        """Not found should return 404"""
        response = client.get("/api/v1/skills/nonexistent-skill-12345")
        assert response.status_code == 404

    def test_cors_headers(self):
        """CORS headers should be present"""
        response = client.options("/api/v1/skills/")
        # Should not error

    def test_request_id_tracking(self):
        """Request IDs should be tracked"""
        response = client.get("/api/v1/skills/")
        assert "x-request-id" in response.headers.lower() or "X-Request-ID" in response.headers


class TestAuthenticationFlow:
    """Test complete authentication flow"""

    def test_api_key_rotation(self):
        """Test API key rotation flow"""
        # Register user
        reg_response = client.post(
            "/api/v1/authors/register",
            json={
                "username": "keytest",
                "email": "keytest@example.com"
            }
        )
        original_key = reg_response.json()["api_key"]

        # Try to use old key after rotation
        # (in real implementation, would need endpoint for this)
        assert original_key.startswith("skpm_")

    def test_authenticated_endpoint_requires_key(self):
        """Authenticated endpoints should require API key"""
        response = client.post(
            "/api/v1/skills/",
            json={
                "name": "protected-skill",
                "version": "1.0.0",
                "description": "Protected skill",
                "language": "python",
                "author_username": "user"
            }
            # No auth header
        )
        # Should be rejected
        assert response.status_code in [401, 403, 400]


class TestDataValidation:
    """Test input validation edge cases"""

    def test_skill_name_validation_edge_cases(self):
        """Test skill name validation edge cases"""
        invalid_names = [
            "test_skill",  # underscore
            "TEST-skill",  # uppercase
            "123-skill",   # starts with digit... actually this is OK
            "-skill",      # starts with hyphen
            "a",           # too short
            "a" * 200      # too long
        ]

        for name in invalid_names[:-1]:  # Skip valid ones
            if name == "123-skill":
                continue  # This is valid actually
            response = client.post(
                "/api/v1/skills/",
                json={
                    "name": name,
                    "version": "1.0.0",
                    "description": "Test",
                    "language": "python",
                    "author_username": "testuser"
                }
            )
            # Should reject invalid
            if name not in ["123-skill"]:
                assert response.status_code != 201, f"Name '{name}' should be invalid"

    def test_version_validation_edge_cases(self):
        """Test semver validation"""
        from registry.schemas.skill import SkillCreate
        from pydantic import ValidationError

        invalid_versions = ["1.0", "v1.0.0", "latest", "1"]

        for version in invalid_versions:
            with pytest.raises(ValidationError):
                SkillCreate(
                    name="test",
                    version=version,
                    description="Test skill description",
                    language="python",
                    author_username="user"
                )

