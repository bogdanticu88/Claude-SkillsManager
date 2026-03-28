# SkillPM
<img width="487" height="161" alt="2026-03-28_02-47" src="https://github.com/user-attachments/assets/3951ab24-47ee-417e-9dbf-5dc9b5a1d760" />

 
 [![Tests](https://github.com/bogdanticu88/Claude-SkillsManager/actions/workflows/ci.yml/badge.svg)](https://github.com/bogdanticu88/Claude-SkillsManager/actions)
 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
 [![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)](https://golang.org)
 [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
  [![Tests](https://github.com/bogdanticu88/Claude-SkillsManager/actions/workflows/ci.yml/badge.svg)](https://github.com/bogdanticu88/Claude-SkillsManager/actions)
 [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
 [![Release](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/bogdanticu88/Claude-SkillsManager/releases)
 [![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)](https://golang.org)
 [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
 [![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker)](https://docker.com)
 [![Coverage](https://img.shields.io/badge/Coverage-75%25+-green.svg)](https://github.com/bogdanticu88/Claude-SkillsManager)
 [![Status](https://img.shields.io/badge/Status-Production%20Ready-success.svg)](#)
 
 
Package manager for Claude AI skills.

SkillPM is a registry and package manager that lets you discover, publish, and manage reusable skills for Claude in a central location. Instead of searching GitHub issues and gists for skill implementations, you register skills to SkillPM, set versioning and dependencies, collect community feedback, and install them with a single command.

It solves the problem that skills today are scattered across repositories with no discovery mechanism, no security vetting, and no way to manage versions or dependencies. SkillPM replaces that with a structured workflow: publish a skill with a manifest, run it through security checks, manage versions, track what skills depend on what, and let teams install them reliably.

---

## What it does

SkillPM provides five main pieces:

**Skill registration and discovery.** Register a skill with a manifest file that defines its name, version, entry point, language, and capabilities. Search and browse all registered skills. Filter by language, tags, or author.

**Version management.** Track multiple versions of a skill. When you publish version 1.1.0 after 1.0.0, SkillPM detects whether the changes are breaking, compatible, or patches. Display breaking changes clearly so users know when they need to update code that depends on the skill.

**Security and validation.** Validate skill manifests against a schema. Hash API keys with Argon2 so credentials are never stored plaintext. Limit requests per user. Check skill names against a reserved list. Enforce input constraints on all fields.

**Community feedback.** Let users review and rate skills. Capture review text and a numeric rating. Display average rating and review count on the skill page. Track who reviewed what to prevent duplicate reviews.

**Automated evidence collection.** Connect to GitHub, Azure DevOps, Jira, and ServiceNow to pull evidence of testing, security, and maintenance. Connectors are opt-in per skill, and credentials are encrypted.

---

## Architecture

SkillPM is a standard two-tier application with a Go CLI and a Python FastAPI backend.

```
skillpm/
├── main.go                 # Go CLI application
│   ├── validate            # Validate skill manifests
│   ├── search              # Search registry
│   ├── install             # Install skills with dependency resolution
│   ├── publish             # Publish a skill to the registry
│   └── list                # List installed skills
├── registry/               # FastAPI backend
│   ├── routers/            # REST endpoints
│   │   ├── skills.py       # Skill CRUD
│   │   ├── authors.py      # User registration and API keys
│   │   ├── reviews.py      # Ratings and feedback
│   │   ├── search.py       # Search across skills
│   │   └── compatibility.py# Breaking change analysis
│   ├── models/             # SQLAlchemy ORM
│   ├── schemas/            # Pydantic request/response models
│   ├── services/           # Business logic (versioning, breaking changes)
│   ├── middleware/         # Auth, rate limiting, logging
│   └── db/                 # Database setup, migrations
├── tests/                  # Pytest test suite (108+ tests)
├── docs/                   # Architecture and design documents
├── examples/               # Example skills for reference
├── docker-compose.yml      # Local development stack
└── .github/workflows/ci.yml# GitHub Actions CI pipeline
```

**Data model:**

```
User (author account, API key hash, rate limit counters)
Skill (name, version, description, entry point, language)
SkillMetadata (tags, target LLMs, capabilities, dependencies)
SkillVersion (version history, changelog, signature)
Review (user, skill, rating, comment)
Download (analytics, usage tracking)
Organization (team workspace, member list)
```

The backend uses FastAPI. The database is SQLite for development and PostgreSQL for production. The frontend provides a REST API for the CLI and a web dashboard for browsing and publishing skills. Authentication uses API keys with JWT bearer tokens.

---

## Features

Current release includes Stage 1 and Stage 2 capabilities:

**Stage 1:**
- Skill search, filtering, and discovery
- Semantic versioning with breaking change detection
- User registration and API key management
- Reviews and ratings system
- Strict input validation on all endpoints
- Per-user rate limiting (100 requests/hour)
- Request size limiting (1 MB)
- Request ID tracking for debugging
- Standardized error responses
- Argon2 API key hashing
- CORS configuration (not wide-open)
- Database migration infrastructure with Alembic
- Docker Compose setup for local development
- Docker multi-stage build for production
- Complete test suite (108+ tests, 75%+ coverage)
- Deployment guide for production
- Operations runbook for incident response

**Stage 2:**
- GPG signing and verification for skill integrity
- Docker sandboxing for secure skill execution with seccomp profiles
- Skill workflow execution with isolation
- Organization and team workspace support
- Web dashboard frontend for skill browsing and publishing
- Advanced skill composition and dependencies

**Planned (Stage 3):**

- Automated evidence collection from GitHub, Azure DevOps, Jira, ServiceNow
- Connector configuration UI
- Multi-tenant workspace isolation
- Skill templates and scaffolding
- Advanced analytics and telemetry

---

## Quick start

Prerequisites: Go 1.21+, Python 3.11+, Docker and Docker Compose.

Clone the repository:

```bash
git clone https://github.com/yourusername/skillpm.git
cd skillpm
```

Start the development stack:

```bash
docker compose up -d
```

This starts a PostgreSQL database, the FastAPI registry API (port 8000), and loads initial data.

Build the CLI:

```bash
go build -o skillpm
```

Register an author account:

```bash
curl -X POST http://localhost:8000/api/v1/authors/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yourname",
    "email": "you@example.com"
  }'
```

The response includes your API key. Save it.

Publish a skill:

```bash
./skillpm publish examples/image-analyzer/skill.yaml --api-key $API_KEY
```

Search for skills:

```bash
./skillpm search vision
```

List skills:

```bash
./skillpm list
```

---

## Development setup

If you want to work on the codebase without Docker:

Requirements: Python 3.12+, Go 1.21+, PostgreSQL, Redis.

Backend:

```bash
cd registry
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:password@localhost/skillpm"
python -m uvicorn main:app --reload
```

API docs are at http://localhost:8000/docs.

CLI:

```bash
go build -o skillpm
./skillpm --help
```

Running tests:

```bash
cd registry
python -m pytest ../tests/ -v --cov=. --cov-report=html
```

---

## Configuration

All configuration is passed via environment variables. See `.env.example` for the full list.

Required:

```bash
SECRET_KEY            # Application secret, at least 32 characters
JWT_SECRET            # JWT signing key, at least 32 characters
DATABASE_URL          # PostgreSQL connection string
REDIS_URL             # Redis connection string
```

Optional:

```bash
LOG_LEVEL             # DEBUG, INFO, WARNING, ERROR (default: INFO)
CORS_ORIGINS          # Comma-separated allowed origins
MAX_BODY_SIZE         # Request size limit in bytes (default: 1000000)
RATE_LIMIT_REQUESTS   # Requests per window (default: 100)
RATE_LIMIT_WINDOW     # Window size in seconds (default: 3600)
```

---

## Testing

The test suite covers API endpoints, security validation, error handling, and business logic.

Run all tests:

```bash
cd registry
python -m pytest ../tests/ -v
```

Run with coverage:

```bash
python -m pytest ../tests/ --cov=. --cov-report=html
```

Run a specific test file:

```bash
python -m pytest ../tests/test_security.py -v
```

The CI pipeline (`.github/workflows/ci.yml`) runs tests on Python 3.11, 3.12, and 3.13 whenever code is pushed or a PR is opened.

---

## Deployment

For production deployment, see DEPLOYMENT.md.

---

## Roadmap

**Stage 1 (Complete):** Basic registry, skill discovery, reviews, versioning.

**Stage 2 (Complete):** GPG signing, Docker sandboxing, workflow execution, web dashboard, organizations.

**Stage 3 (Planned):** Evidence connectors (GitHub, Azure DevOps, Jira, ServiceNow), connector UI, multi-tenant workspaces, skill templates.

---

## License

MIT. See LICENSE file.

---

## Contributing

We welcome contributions. Please read CONTRIBUTING.md for:

- Code style guidelines
- Testing requirements
- Pull request process
- Setting up your development environment

---

Built for the Claude community.


