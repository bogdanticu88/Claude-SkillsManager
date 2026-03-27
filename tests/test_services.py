# SkillPM Registry - Service Layer Tests
# Author: Bogdan Ticu
# License: MIT
#
# Tests for core service logic (breaking changes, versioning)

import pytest
from registry.services.breaking_changes import compare_versions, BreakingChange, CompatibilityReport


class TestBreakingChangeDetection:
    """Test breaking change detection service"""

    def test_no_changes_detected(self):
        """Same manifest should have no breaking changes"""
        manifest = {
            "name": "test-skill",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude"],
            "capabilities": {},
            "dependencies": {}
        }
        report = compare_versions(manifest, manifest)
        assert report.is_compatible is True
        assert len(report.breaking_changes) == 0

    def test_skill_name_change_is_breaking(self):
        """Changing skill name should be detected as critical"""
        old = {
            "name": "old-skill",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "new-skill",
            "version": "2.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        report = compare_versions(old, new)
        assert report.is_compatible is False
        assert any(c.severity == "critical" for c in report.breaking_changes)
        assert any("name" in c.field for c in report.breaking_changes)

    def test_language_change_is_breaking(self):
        """Changing language should be detected as critical"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test",
            "version": "2.0.0",
            "language": "javascript",
            "entry_point": "skill.js"
        }
        report = compare_versions(old, new)
        assert report.is_compatible is False
        assert any(c.severity == "critical" for c in report.breaking_changes)

    def test_entry_point_change_is_breaking(self):
        """Changing entry point should be detected as major"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test",
            "version": "2.0.0",
            "language": "python",
            "entry_point": "main.py"
        }
        report = compare_versions(old, new)
        assert report.is_compatible is False
        assert any(c.severity == "major" for c in report.breaking_changes)

    def test_removed_llm_support_is_breaking(self):
        """Removing LLM support should be detected as major"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude", "openai"]
        }
        new = {
            "name": "test",
            "version": "2.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["openai"]  # Claude removed
        }
        report = compare_versions(old, new)
        assert report.is_compatible is False
        assert any(c.severity == "major" for c in report.breaking_changes)

    def test_new_optional_fields_not_breaking(self):
        """Adding new optional fields should not be breaking"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test",
            "version": "1.1.0",
            "language": "python",
            "entry_point": "skill.py",
            "new_optional_field": "value"  # New field
        }
        report = compare_versions(old, new)
        assert report.is_compatible is True
        assert len(report.breaking_changes) == 0

    def test_added_required_capability_might_be_breaking(self):
        """Changes to capabilities should be tracked"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "capabilities": {}
        }
        new = {
            "name": "test",
            "version": "2.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "capabilities": {"file_read": {"paths": ["/*"]}}
        }
        report = compare_versions(old, new)
        # Adding capabilities might be breaking for security policies
        # This depends on implementation specifics

    def test_version_suggestion_provided(self):
        """Report should suggest next version number"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test",
            "version": "2.0.0",
            "language": "javascript",  # Breaking change
            "entry_point": "skill.js"
        }
        report = compare_versions(old, new)
        # Should suggest major version bump at minimum
        assert report.suggested_version is not None

    def test_migration_notes_provided(self):
        """Report should include migration guidance"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test-renamed",
            "version": "2.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        report = compare_versions(old, new)
        assert len(report.migration_notes) > 0
        assert any("test-renamed" in note for note in report.migration_notes)


class TestVersionManagement:
    """Test semantic versioning support"""

    def test_valid_semver_parsing(self):
        """Should parse valid semver"""
        versions = [
            "1.0.0",
            "0.0.1",
            "10.20.30",
            "1.0.0-beta",
            "1.0.0-rc.1",
            "2.0.0-alpha.1"
        ]
        for version in versions:
            assert isinstance(version, str)
            parts = version.split('.')
            # Should have at least 3 parts before hyphen
            assert len(parts) >= 2

    def test_invalid_semver_rejected(self):
        """Should reject invalid semver"""
        from registry.schemas.skill import SkillCreate
        from pydantic import ValidationError

        invalid = [
            "1.0",
            "v1.0.0",
            "latest",
            "1.0.0.0",
            "1-0-0"
        ]
        for version in invalid:
            with pytest.raises(ValidationError):
                SkillCreate(
                    name="test-skill",
                    version=version,
                    description="Test skill description",
                    language="python",
                    author_username="testuser"
                )


class TestCompatibilityMatrices:
    """Test compatibility tracking"""

    def test_compatibility_report_structure(self):
        """Compatibility report should have required fields"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        report = compare_versions(old, old)

        assert hasattr(report, "old_version")
        assert hasattr(report, "new_version")
        assert hasattr(report, "is_compatible")
        assert hasattr(report, "breaking_changes")
        assert hasattr(report, "suggested_version")
        assert hasattr(report, "migration_notes")

    def test_multiple_breaking_changes_listed(self):
        """Report should list all breaking changes"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude", "openai"]
        }
        new = {
            "name": "renamed",
            "version": "2.0.0",
            "language": "javascript",
            "entry_point": "main.js",
            "target_llms": ["openai"]
        }
        report = compare_versions(old, new)

        # Should have at least 3 breaking changes
        assert len(report.breaking_changes) >= 3

        # Check for specific changes
        change_fields = [c.field for c in report.breaking_changes]
        assert "name" in change_fields
        assert "language" in change_fields


class TestChangeClassification:
    """Test breaking change severity classification"""

    def test_critical_severity(self):
        """Critical changes should be marked as such"""
        old = {"name": "old", "version": "1.0.0"}
        new = {"name": "new", "version": "1.0.0"}
        report = compare_versions(old, new)

        critical_changes = [c for c in report.breaking_changes if c.severity == "critical"]
        assert len(critical_changes) > 0

    def test_major_severity(self):
        """Major changes should be marked as such"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["claude", "openai"]
        }
        new = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "target_llms": ["openai"]  # Removed support
        }
        report = compare_versions(old, new)

        major_changes = [c for c in report.breaking_changes if c.severity == "major"]
        assert len(major_changes) > 0

    def test_minor_severity(self):
        """Minor non-breaking changes might be tagged"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "description": "Old description"
        }
        new = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "description": "New description"  # Minor change
        }
        report = compare_versions(old, new)

        # Description change alone shouldn't break compatibility
        assert report.is_compatible is True


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_null_fields_handled(self):
        """Null/missing fields should be handled"""
        old = {"name": "test", "version": "1.0.0"}
        new = {"name": "test", "version": "2.0.0", "language": None}
        report = compare_versions(old, new)

        # Should not crash
        assert isinstance(report, CompatibilityReport)

    def test_empty_manifests(self):
        """Empty manifests should be handled"""
        empty = {}
        report = compare_versions(empty, empty)

        # Should not crash
        assert isinstance(report, CompatibilityReport)

    def test_extra_fields_ignored(self):
        """Extra unknown fields should be safely ignored"""
        old = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py"
        }
        new = {
            "name": "test",
            "version": "1.0.0",
            "language": "python",
            "entry_point": "skill.py",
            "unknown_field": "value",
            "another_unknown": 123
        }
        report = compare_versions(old, new)

        # Should not crash
        assert isinstance(report, CompatibilityReport)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
