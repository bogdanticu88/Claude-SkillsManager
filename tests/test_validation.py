# SkillPM Registry - Validation Tests
# Author: Bogdan Ticu
# License: MIT
#
# Tests for input validation and error handling

import pytest
from pydantic import ValidationError

from registry.schemas.skill import SkillCreate
from registry.schemas.user import UserCreate


class TestSkillValidation:
    """Test skill creation validation"""

    def test_valid_skill(self):
        """Valid skill should pass"""
        skill = SkillCreate(
            name="my-skill",
            version="1.0.0",
            description="A valid skill description here",
            language="python",
            entry_point="skill.py",
            repository_url="https://github.com/user/my-skill",
            author_username="testuser"
        )
        assert skill.name == "my-skill"
        assert skill.version == "1.0.0"

    def test_skill_name_lowercase_only(self):
        """Skill names must be lowercase"""
        with pytest.raises(ValidationError) as exc_info:
            SkillCreate(
                name="MySkill",  # Invalid: uppercase
                version="1.0.0",
                description="A valid skill description here",
                language="python",
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser"
            )
        assert "lowercase" in str(exc_info.value).lower()

    def test_skill_name_no_underscores(self):
        """Skill names must not have underscores (hyphens only)"""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="my_skill",  # Invalid: underscores not allowed
                version="1.0.0",
                description="A valid skill description here",
                language="python",
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser"
            )

    def test_skill_name_too_short(self):
        """Skill names must be at least 3 characters"""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="ab",  # Too short
                version="1.0.0",
                description="A valid skill description here",
                language="python",
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser"
            )

    def test_skill_name_reserved(self):
        """Cannot use reserved names"""
        for reserved_name in ["admin", "api", "root", "system", "registry"]:
            with pytest.raises(ValidationError) as exc_info:
                SkillCreate(
                    name=reserved_name,
                    version="1.0.0",
                    description="A valid skill description here",
                    language="python",
                    entry_point="skill.py",
                    repository_url="https://github.com/user/my-skill",
                    author_username="testuser"
                )
            assert "reserved" in str(exc_info.value).lower()

    def test_skill_version_invalid_format(self):
        """Version must be semver"""
        invalid_versions = ["v1.0.0", "1.0", "1", "latest"]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                SkillCreate(
                    name="my-skill",
                    version=version,  # Invalid
                    description="A valid skill description here",
                    language="python",
                    entry_point="skill.py",
                    repository_url="https://github.com/user/my-skill",
                    author_username="testuser"
                )

    def test_skill_version_semver_prerelease(self):
        """Version can have prerelease suffix"""
        skill = SkillCreate(
            name="my-skill",
            version="1.0.0-beta",
            description="A valid skill description here",
            language="python",
            entry_point="skill.py",
            repository_url="https://github.com/user/my-skill",
            author_username="testuser"
        )
        assert skill.version == "1.0.0-beta"

    def test_skill_description_too_short(self):
        """Description must be at least 10 characters"""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="my-skill",
                version="1.0.0",
                description="short",  # Too short
                language="python",
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser"
            )

    def test_skill_language_invalid(self):
        """Language must be one of allowed languages"""
        with pytest.raises(ValidationError) as exc_info:
            SkillCreate(
                name="my-skill",
                version="1.0.0",
                description="A valid skill description here",
                language="rust",  # Not allowed
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser"
            )
        assert "must be one of" in str(exc_info.value).lower()

    def test_skill_language_case_insensitive(self):
        """Language should be normalized to lowercase"""
        skill = SkillCreate(
            name="my-skill",
            version="1.0.0",
            description="A valid skill description here",
            language="PYTHON",  # Uppercase
            entry_point="skill.py",
            repository_url="https://github.com/user/my-skill",
            author_username="testuser"
        )
        assert skill.language == "python"  # Normalized to lowercase

    def test_skill_url_must_be_valid(self):
        """Repository URL must be valid"""
        with pytest.raises(ValidationError):
            SkillCreate(
                name="my-skill",
                version="1.0.0",
                description="A valid skill description here",
                language="python",
                entry_point="skill.py",
                repository_url="not-a-url",  # Invalid
                author_username="testuser"
            )

    def test_skill_extra_fields_rejected(self):
        """Unknown fields should be rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SkillCreate(
                name="my-skill",
                version="1.0.0",
                description="A valid skill description here",
                language="python",
                entry_point="skill.py",
                repository_url="https://github.com/user/my-skill",
                author_username="testuser",
                unknown_field="should fail"  # Unknown field
            )
        assert "extra" in str(exc_info.value).lower()


class TestUserValidation:
    """Test user registration validation"""

    def test_valid_user(self):
        """Valid user should pass"""
        user = UserCreate(
            username="john-doe",
            email="john@example.com",
            display_name="John Doe"
        )
        assert user.username == "john-doe"
        assert user.email == "john@example.com"

    def test_username_lowercase_only(self):
        """Username must be lowercase"""
        with pytest.raises(ValidationError):
            UserCreate(
                username="JohnDoe",  # Uppercase
                email="john@example.com"
            )

    def test_username_too_short(self):
        """Username must be at least 3 characters"""
        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",  # Too short
                email="john@example.com"
            )

    def test_username_reserved(self):
        """Cannot use reserved usernames"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="admin",
                email="admin@example.com"
            )
        assert "reserved" in str(exc_info.value).lower()

    def test_email_invalid(self):
        """Email must be valid"""
        invalid_emails = ["notanemail", "user@", "@example.com", "user @example.com"]
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    username="john-doe",
                    email=email
                )

    def test_email_normalized(self):
        """Email should be normalized to lowercase"""
        user = UserCreate(
            username="john-doe",
            email="JOHN@EXAMPLE.COM"
        )
        assert user.email == "john@example.com"

    def test_website_must_have_protocol(self):
        """Website must start with http:// or https://"""
        with pytest.raises(ValidationError):
            UserCreate(
                username="john-doe",
                email="john@example.com",
                website="example.com"  # Missing protocol
            )

    def test_website_valid(self):
        """Valid website should pass"""
        user = UserCreate(
            username="john-doe",
            email="john@example.com",
            website="https://example.com"
        )
        assert user.website == "https://example.com"

    def test_extra_fields_rejected(self):
        """Unknown fields should be rejected"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="john-doe",
                email="john@example.com",
                unknown_field="should fail"
            )
        assert "extra" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
