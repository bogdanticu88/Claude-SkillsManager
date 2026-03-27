#!/usr/bin/env python3
# SkillPM Registry - API Tests
# Author: Bogdan Ticu
# License: MIT

import pytest
from fastapi.testclient import TestClient

import sys
import os

# Ensure the registry package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from registry.main import app
from registry.db.connection import init_db

# Initialize DB for tests
init_db()

client = TestClient(app)


# --- Health and Root ---

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "SkillPM Registry"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# --- Author Registration ---

def test_register_user():
    r = client.post("/api/v1/authors/register", json={
        "username": "test_user_1",
        "email": "test1@example.com",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "test_user_1"
    assert "api_key" in data
    return data["api_key"]


def test_register_duplicate_user():
    # First registration
    client.post("/api/v1/authors/register", json={
        "username": "duplicate_user",
    })
    # Second registration should fail
    r = client.post("/api/v1/authors/register", json={
        "username": "duplicate_user",
    })
    assert r.status_code == 409


# --- Skill CRUD ---

def test_create_skill():
    r = client.post("/api/v1/skills/", json={
        "name": "test-skill-1",
        "version": "1.0.0",
        "description": "A test skill",
        "license": "MIT",
        "repository_url": "https://github.com/test/test-skill-1",
        "author_username": "test_author",
        "metadata": {
            "tags": ["test", "example"],
            "language": "python",
            "target_llms": ["claude"],
            "capabilities": {},
            "dependencies": {},
        },
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "test-skill-1"
    assert data["version"] == "1.0.0"


def test_create_duplicate_skill():
    # Create once
    client.post("/api/v1/skills/", json={
        "name": "dup-skill",
        "version": "1.0.0",
        "description": "Duplicate test",
        "license": "MIT",
        "author_username": "test_author",
        "metadata": {
            "tags": [],
            "language": "python",
            "target_llms": [],
            "capabilities": {},
            "dependencies": {},
        },
    })
    # Create again
    r = client.post("/api/v1/skills/", json={
        "name": "dup-skill",
        "version": "1.0.0",
        "description": "Duplicate test 2",
        "license": "MIT",
        "author_username": "test_author",
        "metadata": {
            "tags": [],
            "language": "python",
            "target_llms": [],
            "capabilities": {},
            "dependencies": {},
        },
    })
    assert r.status_code == 409


def test_get_skill():
    # Create a skill first
    client.post("/api/v1/skills/", json={
        "name": "get-test-skill",
        "version": "2.0.0",
        "description": "Get test",
        "license": "MIT",
        "author_username": "test_author",
        "metadata": {
            "tags": ["fetch"],
            "language": "python",
            "target_llms": ["claude"],
            "capabilities": {},
            "dependencies": {},
        },
    })

    r = client.get("/api/v1/skills/get-test-skill")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "get-test-skill"
    assert data["version"] == "2.0.0"


def test_get_nonexistent_skill():
    r = client.get("/api/v1/skills/does-not-exist")
    assert r.status_code == 404


def test_list_skills():
    r = client.get("/api/v1/skills/")
    assert r.status_code == 200
    data = r.json()
    assert "skills" in data
    assert "total" in data


# --- Search ---

def test_search_skills():
    r = client.get("/api/v1/search?q=test")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_with_tag():
    r = client.get("/api/v1/search?tag=test")
    assert r.status_code == 200


def test_autocomplete():
    r = client.get("/api/v1/search/autocomplete?q=test")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_tags():
    r = client.get("/api/v1/search/tags")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- Author Profiles ---

def test_get_author():
    # Create skill to auto-create author
    client.post("/api/v1/skills/", json={
        "name": "author-test-skill",
        "version": "1.0.0",
        "description": "Author test",
        "license": "MIT",
        "author_username": "author_test_user",
        "metadata": {
            "tags": [],
            "language": "python",
            "target_llms": [],
            "capabilities": {},
            "dependencies": {},
        },
    })

    r = client.get("/api/v1/authors/author_test_user")
    assert r.status_code == 200
    assert r.json()["username"] == "author_test_user"


def test_get_author_skills():
    r = client.get("/api/v1/authors/author_test_user/skills")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- Analytics ---

def test_global_analytics():
    r = client.get("/api/v1/analytics/global")
    assert r.status_code == 200
    data = r.json()
    assert "total_skills" in data
    assert "total_authors" in data


def test_skill_analytics():
    r = client.get("/api/v1/analytics/skill/test-skill-1")
    assert r.status_code == 200


# --- Compatibility ---

def test_compare_manifests():
    r = client.post("/api/v1/compatibility/check", json={
        "old_manifest": {
            "name": "my-skill",
            "version": "1.0.0",
            "language": "python",
            "target_llms": ["claude", "gpt-4"],
        },
        "new_manifest": {
            "name": "my-skill",
            "version": "2.0.0",
            "language": "python",
            "target_llms": ["claude"],
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert "breaking_changes" in data
    # gpt-4 was removed, should be flagged
    assert len(data["breaking_changes"]) > 0


def test_compare_no_breaking():
    r = client.post("/api/v1/compatibility/check", json={
        "old_manifest": {
            "name": "my-skill",
            "version": "1.0.0",
            "language": "python",
            "target_llms": ["claude"],
        },
        "new_manifest": {
            "name": "my-skill",
            "version": "1.1.0",
            "language": "python",
            "target_llms": ["claude", "gpt-4"],
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["is_compatible"] is True


# --- Dashboard ---

def test_dashboard_downloads():
    r = client.get("/api/v1/dashboard/downloads-over-time")
    assert r.status_code == 200


def test_dashboard_error_rates():
    r = client.get("/api/v1/dashboard/error-rates")
    assert r.status_code == 200


def test_dashboard_performance():
    r = client.get("/api/v1/dashboard/performance")
    assert r.status_code == 200


def test_dashboard_llm_usage():
    r = client.get("/api/v1/dashboard/llm-usage")
    assert r.status_code == 200


# --- Cache ---

def test_cache_stats():
    r = client.get("/api/v1/cache/stats")
    assert r.status_code == 200
    assert "hits" in r.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
