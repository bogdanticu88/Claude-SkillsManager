#!/usr/bin/env python3
# SkillPM Registry - Database Seeder
# Author: Bogdan Ticu
# License: MIT
#
# Seeds the registry database with the 30 bootstrap skills
# and test users for development.

import sys
import os

# Add parent to path so we can import the registry package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry.db.connection import SessionLocal, init_db
from registry.db.models import User, Skill, SkillMetadata, SkillVersion, Review
from registry.middleware.auth import hash_api_key

# Initialize tables
init_db()

db = SessionLocal()

# --- Create test users ---

test_users = [
    {
        "username": "bogdan",
        "email": "bogdan@skillpm.dev",
        "display_name": "Bogdan Ticu",
        "bio": "SkillPM creator and maintainer",
        "verified": True,
        "is_admin": True,
        "api_key": "skpm_test_admin_key_123",
    },
    {
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice Developer",
        "bio": "Full-stack developer and AI enthusiast",
        "verified": True,
        "api_key": "skpm_test_alice_key_456",
    },
    {
        "username": "bob",
        "email": "bob@example.com",
        "display_name": "Bob Builder",
        "bio": "DevOps engineer",
        "verified": False,
        "api_key": "skpm_test_bob_key_789",
    },
]

user_map = {}
for u in test_users:
    existing = db.query(User).filter(User.username == u["username"]).first()
    if existing:
        user_map[u["username"]] = existing
        continue

    api_key = u.pop("api_key")
    user = User(**u, api_key_hash=hash_api_key(api_key))
    db.add(user)
    db.commit()
    db.refresh(user)
    user_map[u["username"]] = user
    print(f"Created user: {u['username']} (API key: {api_key})")

# --- Create bootstrap skills ---

bootstrap_skills = [
    {
        "name": "code-reviewer",
        "version": "1.0.0",
        "description": "Automated code review with security analysis and style checking",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["code-review", "security", "linting"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/code-reviewer",
    },
    {
        "name": "test-generator",
        "version": "1.0.0",
        "description": "Generate unit tests from source code automatically",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["testing", "automation", "unit-tests"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/test-generator",
    },
    {
        "name": "doc-writer",
        "version": "1.0.0",
        "description": "Generate documentation from code with docstrings and README files",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["documentation", "readme", "docstrings"],
        "target_llms": ["claude", "gpt-4", "gemini"],
        "repository_url": "https://github.com/skillpm/doc-writer",
    },
    {
        "name": "api-scaffolder",
        "version": "1.0.0",
        "description": "Generate REST API boilerplate from OpenAPI specs",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["api", "scaffolding", "openapi", "rest"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/api-scaffolder",
    },
    {
        "name": "db-migrator",
        "version": "1.0.0",
        "description": "Generate database migration scripts from schema changes",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["database", "migration", "schema"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/db-migrator",
    },
    {
        "name": "security-scanner",
        "version": "1.0.0",
        "description": "Scan code for common security vulnerabilities and OWASP issues",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["security", "vulnerability", "owasp", "scanning"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/security-scanner",
    },
    {
        "name": "git-changelog",
        "version": "1.0.0",
        "description": "Generate changelogs from git commit history",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["git", "changelog", "release-notes"],
        "target_llms": ["claude", "gpt-4", "gemini"],
        "repository_url": "https://github.com/skillpm/git-changelog",
    },
    {
        "name": "refactor-assistant",
        "version": "1.0.0",
        "description": "Suggest and apply code refactoring patterns",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["refactoring", "code-quality", "patterns"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/refactor-assistant",
    },
    {
        "name": "performance-profiler",
        "version": "1.0.0",
        "description": "Analyze code for performance bottlenecks and suggest optimizations",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["performance", "profiling", "optimization"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/performance-profiler",
    },
    {
        "name": "error-explainer",
        "version": "1.0.0",
        "description": "Parse and explain error messages and stack traces",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["errors", "debugging", "stack-traces"],
        "target_llms": ["claude", "gpt-4", "gemini", "local-llm"],
        "repository_url": "https://github.com/skillpm/error-explainer",
    },
    {
        "name": "dependency-auditor",
        "version": "1.0.0",
        "description": "Audit project dependencies for vulnerabilities and license issues",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["dependencies", "security", "license", "audit"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/dependency-auditor",
    },
    {
        "name": "image-analyzer",
        "version": "1.0.0",
        "description": "Analyze images using vision-capable LLMs",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["vision", "image", "analysis", "multimodal"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/image-analyzer",
    },
    {
        "name": "pr-reviewer",
        "version": "1.0.0",
        "description": "Review pull requests with inline comments and suggestions",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["pull-request", "code-review", "github"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/pr-reviewer",
    },
    {
        "name": "commit-message-writer",
        "version": "1.0.0",
        "description": "Generate conventional commit messages from staged changes",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["git", "commits", "conventional-commits"],
        "target_llms": ["claude", "gpt-4", "local-llm"],
        "repository_url": "https://github.com/skillpm/commit-message-writer",
    },
    {
        "name": "env-validator",
        "version": "1.0.0",
        "description": "Validate environment configuration and .env files",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["environment", "configuration", "validation"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/env-validator",
    },
    {
        "name": "regex-builder",
        "version": "1.0.0",
        "description": "Build and test regular expressions from natural language descriptions",
        "license": "MIT",
        "language": "javascript",
        "author": "bogdan",
        "tags": ["regex", "text-processing", "patterns"],
        "target_llms": ["claude", "gpt-4", "gemini"],
        "repository_url": "https://github.com/skillpm/regex-builder",
    },
    {
        "name": "sql-optimizer",
        "version": "1.0.0",
        "description": "Analyze and optimize SQL queries for better performance",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["sql", "database", "optimization", "performance"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/sql-optimizer",
    },
    {
        "name": "dockerfile-generator",
        "version": "1.0.0",
        "description": "Generate optimized Dockerfiles for any project",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["docker", "containerization", "devops"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/dockerfile-generator",
    },
    {
        "name": "type-annotator",
        "version": "1.0.0",
        "description": "Add type annotations to Python code automatically",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["typing", "python", "type-hints", "annotations"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/type-annotator",
    },
    {
        "name": "readme-generator",
        "version": "1.0.0",
        "description": "Generate comprehensive README files from project structure",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["readme", "documentation", "markdown"],
        "target_llms": ["claude", "gpt-4", "gemini"],
        "repository_url": "https://github.com/skillpm/readme-generator",
    },
    {
        "name": "data-faker",
        "version": "1.0.0",
        "description": "Generate realistic fake data for testing and development",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["testing", "fake-data", "mock", "fixtures"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/data-faker",
    },
    {
        "name": "cron-builder",
        "version": "1.0.0",
        "description": "Build cron expressions from natural language scheduling descriptions",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["cron", "scheduling", "automation"],
        "target_llms": ["claude", "gpt-4", "local-llm"],
        "repository_url": "https://github.com/skillpm/cron-builder",
    },
    {
        "name": "config-converter",
        "version": "1.0.0",
        "description": "Convert between JSON, YAML, TOML, and INI configuration formats",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["configuration", "json", "yaml", "toml", "conversion"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/config-converter",
    },
    {
        "name": "api-mocker",
        "version": "1.0.0",
        "description": "Generate mock API servers from OpenAPI specifications",
        "license": "MIT",
        "language": "javascript",
        "author": "bob",
        "tags": ["api", "mock", "testing", "openapi"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/api-mocker",
    },
    {
        "name": "i18n-translator",
        "version": "1.0.0",
        "description": "Translate i18n message files between languages",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["i18n", "translation", "localization"],
        "target_llms": ["claude", "gpt-4", "gemini"],
        "repository_url": "https://github.com/skillpm/i18n-translator",
    },
    {
        "name": "shell-explainer",
        "version": "1.0.0",
        "description": "Explain complex shell commands and scripts in plain English",
        "license": "MIT",
        "language": "python",
        "author": "alice",
        "tags": ["shell", "bash", "cli", "explanation"],
        "target_llms": ["claude", "gpt-4", "gemini", "local-llm"],
        "repository_url": "https://github.com/skillpm/shell-explainer",
    },
    {
        "name": "graphql-scaffolder",
        "version": "1.0.0",
        "description": "Generate GraphQL schemas and resolvers from data models",
        "license": "MIT",
        "language": "javascript",
        "author": "bob",
        "tags": ["graphql", "api", "scaffolding", "schema"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/graphql-scaffolder",
    },
    {
        "name": "log-analyzer",
        "version": "1.0.0",
        "description": "Analyze log files to find patterns, errors, and anomalies",
        "license": "MIT",
        "language": "python",
        "author": "bogdan",
        "tags": ["logs", "analysis", "debugging", "monitoring"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/log-analyzer",
    },
    {
        "name": "css-generator",
        "version": "1.0.0",
        "description": "Generate CSS styles from natural language descriptions",
        "license": "MIT",
        "language": "javascript",
        "author": "alice",
        "tags": ["css", "styling", "frontend", "design"],
        "target_llms": ["claude", "gpt-4"],
        "repository_url": "https://github.com/skillpm/css-generator",
    },
    {
        "name": "git-bisect-helper",
        "version": "1.0.0",
        "description": "Automate git bisect with intelligent test generation",
        "license": "MIT",
        "language": "python",
        "author": "bob",
        "tags": ["git", "debugging", "bisect", "automation"],
        "target_llms": ["claude"],
        "repository_url": "https://github.com/skillpm/git-bisect-helper",
    },
]

for s in bootstrap_skills:
    existing = db.query(Skill).filter(Skill.name == s["name"]).first()
    if existing:
        print(f"Skill already exists: {s['name']}")
        continue

    author = user_map.get(s["author"])
    if not author:
        print(f"Author not found: {s['author']}, skipping {s['name']}")
        continue

    skill = Skill(
        name=s["name"],
        version=s["version"],
        description=s["description"],
        license=s["license"],
        language=s["language"],
        repository_url=s["repository_url"],
        author_id=author.id,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    metadata = SkillMetadata(
        skill_id=skill.id,
        tags=s["tags"],
        language=s["language"],
        target_llms=s["target_llms"],
        capabilities={},
        dependencies={},
    )
    db.add(metadata)

    version = SkillVersion(
        skill_id=skill.id,
        version=s["version"],
        changelog="Initial release",
    )
    db.add(version)

    db.commit()
    print(f"Created skill: {s['name']}")

# --- Add some sample reviews ---

sample_reviews = [
    ("code-reviewer", "alice", 5, "Excellent tool", "Catches issues I would miss. Great for PR reviews."),
    ("code-reviewer", "bob", 4, "Very useful", "Good but could use more language support."),
    ("test-generator", "alice", 4, "Saves hours", "Generated tests cover edge cases well."),
    ("doc-writer", "bob", 5, "Best doc tool", "Generates clean documentation every time."),
    ("error-explainer", "alice", 5, "Must have", "Explains cryptic errors in plain English."),
    ("security-scanner", "bob", 4, "Solid scanner", "Found real vulnerabilities in my code."),
    ("image-analyzer", "bob", 5, "Amazing", "Vision analysis is spot on."),
    ("regex-builder", "alice", 4, "Handy", "No more guessing regex syntax."),
]

for skill_name, username, rating, title, body in sample_reviews:
    skill = db.query(Skill).filter(Skill.name == skill_name).first()
    user = db.query(User).filter(User.username == username).first()
    if not skill or not user:
        continue

    existing = db.query(Review).filter(
        Review.skill_id == skill.id,
        Review.user_id == user.id,
    ).first()
    if existing:
        continue

    review = Review(
        skill_id=skill.id,
        user_id=user.id,
        rating=rating,
        title=title,
        body=body,
    )
    db.add(review)

db.commit()
print("\nSeeding complete.")
print(f"Users: {db.query(User).count()}")
print(f"Skills: {db.query(Skill).count()}")
print(f"Reviews: {db.query(Review).count()}")

db.close()
