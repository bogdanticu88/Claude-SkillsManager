#!/usr/bin/env python3
# SkillPM Registry - Version Resolver Tests
# Author: Bogdan Ticu
# License: MIT

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from registry.services.version_resolver import (
    parse_version, parse_constraint, version_matches,
    DependencyResolver,
)
from registry.services.breaking_changes import compare_versions


# --- Version parsing ---

def test_parse_version():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("0.0.1") == (0, 0, 1)
    assert parse_version("10.20.30") == (10, 20, 30)
    assert parse_version("invalid") == (0, 0, 0)


# --- Constraint matching ---

def test_exact_match():
    c = parse_constraint("1.2.3")
    assert version_matches("1.2.3", c) is True
    assert version_matches("1.2.4", c) is False


def test_gte_match():
    c = parse_constraint(">=1.0.0")
    assert version_matches("1.0.0", c) is True
    assert version_matches("1.0.1", c) is True
    assert version_matches("2.0.0", c) is True
    assert version_matches("0.9.9", c) is False


def test_lte_match():
    c = parse_constraint("<=2.0.0")
    assert version_matches("1.0.0", c) is True
    assert version_matches("2.0.0", c) is True
    assert version_matches("2.0.1", c) is False


def test_caret_match():
    c = parse_constraint("^1.2.3")
    assert version_matches("1.2.3", c) is True
    assert version_matches("1.9.0", c) is True
    assert version_matches("2.0.0", c) is False
    assert version_matches("1.2.2", c) is False


def test_caret_zero_major():
    c = parse_constraint("^0.2.3")
    assert version_matches("0.2.3", c) is True
    assert version_matches("0.2.9", c) is True
    assert version_matches("0.3.0", c) is False


def test_tilde_match():
    c = parse_constraint("~1.2.3")
    assert version_matches("1.2.3", c) is True
    assert version_matches("1.2.9", c) is True
    assert version_matches("1.3.0", c) is False


def test_any_match():
    c = parse_constraint("*")
    assert version_matches("1.0.0", c) is True
    assert version_matches("99.99.99", c) is True


# --- Dependency resolution ---

def test_simple_resolve():
    available = {
        "skill-a": ["1.0.0", "1.1.0", "2.0.0"],
        "skill-b": ["1.0.0"],
    }
    resolver = DependencyResolver(available)
    result = resolver.resolve({"skill-a": "^1.0.0", "skill-b": "*"})
    assert result.success is True
    assert result.resolved["skill-a"] == "1.1.0"  # newest matching ^1.0.0
    assert result.resolved["skill-b"] == "1.0.0"


def test_resolve_not_found():
    available = {"skill-a": ["1.0.0"]}
    resolver = DependencyResolver(available)
    result = resolver.resolve({"nonexistent": "*"})
    assert result.success is False
    assert len(result.conflicts) > 0


def test_resolve_no_match():
    available = {"skill-a": ["1.0.0", "1.1.0"]}
    resolver = DependencyResolver(available)
    result = resolver.resolve({"skill-a": ">=2.0.0"})
    assert result.success is False


# --- Breaking change detection ---

def test_no_breaking_changes():
    report = compare_versions(
        {"name": "test", "version": "1.0.0", "language": "python", "target_llms": ["claude"]},
        {"name": "test", "version": "1.1.0", "language": "python", "target_llms": ["claude", "gpt-4"]},
    )
    assert report.is_compatible is True
    assert len(report.breaking_changes) == 0


def test_name_change_breaking():
    report = compare_versions(
        {"name": "old-name", "version": "1.0.0"},
        {"name": "new-name", "version": "2.0.0"},
    )
    assert report.is_compatible is False
    assert any(c.severity == "critical" for c in report.breaking_changes)


def test_language_change_breaking():
    report = compare_versions(
        {"name": "test", "version": "1.0.0", "language": "python"},
        {"name": "test", "version": "2.0.0", "language": "javascript"},
    )
    assert report.is_compatible is False


def test_removed_llm_breaking():
    report = compare_versions(
        {"name": "test", "version": "1.0.0", "target_llms": ["claude", "gpt-4"]},
        {"name": "test", "version": "2.0.0", "target_llms": ["claude"]},
    )
    assert len(report.breaking_changes) > 0
    assert any("gpt-4" in c.description for c in report.breaking_changes)


def test_suggested_version_bump():
    report = compare_versions(
        {"name": "test", "version": "1.2.3", "language": "python"},
        {"name": "test", "version": "1.2.3", "language": "javascript"},
    )
    assert report.suggested_version == "2.0.0"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
