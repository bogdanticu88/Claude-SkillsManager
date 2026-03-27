# SkillPM Phase 1: MVP Implementation Plan (Detailed)
## Weeks 1-4 + Phase 1.5: Weeks 5-6

**Status:** Ready for development kickoff  
**Duration:** 6 weeks (including hardened security phase)  
**Team Size:** 2 engineers + 1 security reviewer  
**Budget:** $0-5k (free infrastructure, optional paid audit)  

---

## Executive Overview

Phase 1 delivers a **working, secure skill package manager** that can be launched publicly with confidence. Unlike the original plan, this iteration includes Docker sandboxing and GPG signing from the beginning, plus a bootstrap strategy to avoid the cold-start problem.

**Phase 1 Outputs:**
- CLI tool (cross-platform binary)
- Registry website (searchable, functional)
- 15 bootstrap skills (high-quality examples)
- Documentation & getting started guide
- Security model in place (manifest + static validation + sandboxed execution)

---

## Pre-Phase 1: Content Seeding (Weeks -2 to 0)

### Why This Matters
Empty registries fail. You need momentum at launch. This 2-week sprint creates 15 killer skills that demonstrate SkillPM's value.

### Week -2: Skill Planning & Recruitment

**Tasks:**
1. **Identify 15 skill concepts** (see recommended list below)
2. **Recruit 5-10 creators** via Twitter/Reddit/email
   - Target: AI enthusiasts with Claude experience
   - Offer: $100-200 each for skill creation
   - Commitment: "You'll be in the first 20 on SkillPM"
3. **Brief creators** on manifest spec (once finalized)
4. **Assign skills** to creators

**Example recruitment message:**
```
"We're launching SkillPM, a skill package manager for Claude. 
We're looking for creators to build the first 15 skills.
You'll receive $150 and get featured on launch day.
Skills you create: [list 3 options]
Interested? Reply with your GitHub."
```

**Bootstrap Skill Ideas (pick best 15):**
- Image analyzer (vision capabilities)
- Code reviewer (security-focused)
- Document summarizer (long-form)
- JSON validator (utility)
- SQL query generator (enterprise)
- Research paper analyzer (academic)
- Meeting transcript analyzer (business)
- Email drafter (productivity)
- API documentation generator (dev)
- Customer support classifier (support)
- Price comparison tool (e-commerce)
- Legal document analyzer (legal)
- Social media post generator (marketing)
- SEO analyzer (web)
- Competitor research tool (business intel)

### Week 0: Skill Implementation & Testing

**Parallel work:**
- Creators build skills (while engineering team works on infrastructure)
- Each skill submitted as GitHub repo
- You review for quality, test with Claude
- Iterate and polish

**Quality bar:**
- Works with Claude (tested)
- Has good README
- Manifest is complete
- Demonstrates a real use case
- Can be used immediately without modification

**By end of Week 0:**
- 12-15 skills ready to publish
- All tested and working
- Ready to add to registry on launch day

---

## Phase 1: Core Development (Weeks 1-4)

### Week 1: Foundation & Design Finalization

**Engineering Task 1: Finalize Manifest Schema**
- Review spec from master plan
- Add any tweaks based on creator feedback
- Write JSON Schema validator (will be used for validation)
- Test with 2-3 bootstrap skills
- **Deliverable:** Final `skill.schema.json`

**Engineering Task 2: Set Up Infrastructure**
- GitHub organization created: `github.com/skillpm-registry/`
- Create template skill repo (copy/paste starter)
- PostgreSQL database created (or SQLite for MVP simplicity)
- Domain name purchased (skillpm.dev or similar)
- GitHub OAuth app created (for login)
- **Deliverable:** Working dev infrastructure

**Engineering Task 3: CLI Tool Scaffold (Go)**
- Create Go project structure
- Implement YAML parser (use `gopkg.in/yaml.v3`)
- Implement HTTP client for registry API
- Basic CLI argument parsing
- **Deliverable:** Bare CLI binary (no functionality yet)

**Security Reviewer Task:**
- Review manifest schema for security implications
- Flag risky capability types
- Suggest additional constraints
- **Deliverable:** Security review of manifest spec

**By end of Week 1:**
- Manifest spec is finalized and approved
- Infrastructure ready
- CLI skeleton compiles
- Team is synchronized

---

### Week 2: CLI Core Features & Registry API

**Engineering Task 1: CLI Implementation - Part A (Basic Commands)**
```bash
skillpm search <query>        # Search registry
skillpm show <skill-name>     # Show skill details
skillpm list                  # List installed skills
skillpm version               # Show version
skillpm --help                # Help text
```

- HTTP client connects to registry API
- JSON parsing for responses
- Terminal output formatting
- Error handling for network failures
- **Deliverable:** These 5 commands working

**Engineering Task 2: Registry API - Part A (Read-only)**
```
GET /api/v1/skills                    # List all skills
GET /api/v1/skills/<name>             # Get skill metadata
GET /api/v1/search?q=<query>&tag=<tag> # Search
GET /api/v1/authors/<username>         # Author profile
```

- PostgreSQL schema designed
- API endpoints implemented (FastAPI or Express)
- Ability to ingest skill metadata from GitHub
- Response validation
- **Deliverable:** API working, readable

**Engineering Task 3: Registry Website - Part A**
- Static site (Jekyll) or simple Next.js
- Homepage with search bar
- Skill detail pages (static generation from API)
- Search results page
- Author profile page
- **Deliverable:** Website deployed to Vercel/Netlify, live

**By end of Week 2:**
- CLI can search and view skills
- API serves skill metadata
- Website is live and searchable
- Registry shows the 15 bootstrap skills

---

### Week 3: CLI Installation & Manifest Validation

**Engineering Task 1: CLI Implementation - Part B (Installation)**
```bash
skillpm install <skill-name>[@version]  # Install skill
skillpm uninstall <skill-name>          # Remove skill
skillpm update [<skill-name>]           # Update skills
skillpm validate <path>                 # Validate skill
```

- Fetch skill from registry
- Download from GitHub
- Extract to local directory (`~/.skillpm/skills/`)
- Validate manifest before installation
- Ask user for permission (interactive prompt)
- **Deliverable:** Install/uninstall working

**Engineering Task 2: Manifest Validation (Static)**
- YAML syntax validation
- Schema validation (check against `skill.schema.json`)
- Semantic checks:
  - Paths don't contain dangerous patterns
  - Capability names are valid
  - Dependencies exist in registry
  - Version format is semver
- File existence checks:
  - skill.yaml exists
  - entry_point file exists
  - README.md exists
- **Code analysis** (basic):
  - Scan for hardcoded credentials (keywords: API_KEY, PASSWORD, SECRET)
  - Warn on subprocess without declaration
  - Warn on wildcard paths
  - Suggest fixes for common issues
- **Deliverable:** `skillpm validate` command works, catches 80% of issues

**Security Reviewer Task:**
- Test validation on 5 intentionally bad skills
- Ensure it catches malicious patterns
- Document what passes validation (and why it's safe)
- **Deliverable:** Validation test suite + documentation

**Engineering Task 3: Registry API - Part B (Publishing)**
```
POST /api/v1/skills/<name>/publish  # Publish new skill (requires auth)
```

- GitHub OAuth login
- Validate published skill
- Add to registry database
- Send email confirmation
- **Deliverable:** API ready for Phase 1.5

**By end of Week 3:**
- CLI can install/validate skills
- Users can search, view, install
- Developers can validate before publishing
- Registry is functional and safe

---

### Week 4: Docker Sandboxing & GPG Signing (Phase 1.5 Early Start)

**Why move this up:** Security is too important to delay. Docker + GPG can be done in 1 week once CLI is working.

**Engineering Task 1: Docker Sandboxing Setup**
- Create Dockerfile template for skills
  - Base: python:3.11-slim or node:18-alpine
  - Install skill dependencies
  - Set up restricted file system mounts
  - Configure network restrictions
- Implement sandbox runner:
  - `skillpm run <skill-name> <function> <args>`
  - Mounts only allowed directories
  - Network limited to declared domains
  - Process timeout (30 seconds default)
  - Logs all access attempts
- **Deliverable:** Skills run in Docker, isolated

**Engineering Task 2: GPG Signing Implementation**
- CLI generates GPG key for author (first run)
- Skill manifest includes author's GPG fingerprint
- On publish: sign skill with GPG key
- On install: verify signature (warn if unsigned)
- Registry stores signature hash
- **Deliverable:** Signed skills, verification working

**Engineering Task 3: Logging & Audit Trail**
- Log all skill executions
- Log all file access (success/failure)
- Log all network access
- Store in `~/.skillpm/logs/`
- `skillpm logs <skill-name>` command to view
- **Deliverable:** Full audit trail available

**Security Reviewer Task:**
- Test sandbox escapes (try to break out)
- Verify file isolation works
- Verify network isolation works
- Check GPG implementation
- **Deliverable:** Sandbox security report

**By end of Week 4:**
- Skills run in Docker containers
- Full isolation and logging
- GPG signing in place
- Ready for public launch

---

## Phase 1.5: Hardening & Polish (Weeks 5-6)

### Week 5: Testing, Documentation, Community Review

**Engineering Task 1: Comprehensive Testing**
- Unit tests for manifest parser
- Integration tests for CLI commands
- API endpoint tests
- Sandbox security tests
- Install/uninstall lifecycle tests
- **Coverage target:** 80%+

**Engineering Task 2: Documentation**
- README.md (root project)
- Getting started guide (5-minute quick start)
- Manifest spec documentation (detailed)
- CLI tool documentation (all commands)
- Security model whitepaper (threats, mitigations)
- Contributing guide (how to create skills)
- FAQ

**Engineering Task 3: Website Polish**
- Add registry stats (total skills, downloads, etc.)
- Add featured skills section
- Add community guidelines
- Add security policy
- Add CoC (Code of Conduct)
- Add contact/support page

**Community Task:**
- Reach out to 20-30 potential users
- Ask for feedback (closed beta)
- Fix issues before launch
- Get testimonials/quotes

**By end of Week 5:**
- Tested, documented, polished
- Community feedback incorporated
- Ready to announce

---

### Week 6: Launch Preparation & Security Audit

**Engineering Task 1: Pre-launch Checklist**
- [ ] All commands tested manually
- [ ] Error messages are helpful
- [ ] No hardcoded secrets in code
- [ ] API rate limiting configured
- [ ] Database backups working
- [ ] Deployment process documented
- [ ] Rollback procedure tested
- [ ] Monitoring/alerting configured

**Engineering Task 2: Security Hardening**
- Enable HTTPS everywhere
- Set security headers (CSP, HSTS, X-Frame-Options)
- Rate limit API (100 requests/min per IP)
- Validate all inputs
- Sanitize all outputs
- Remove debug logs in production
- **Deliverable:** Security checklist passed

**Optional: Professional Security Audit**
- Hire Trail of Bits or similar ($5-10k)
- 1-week audit of code + infrastructure
- Public report of findings
- Massive credibility bump
- **Deliverable:** "Professionally audited" stamp

**Launch Marketing:**
- Write launch announcement blog post
- Prepare Twitter/LinkedIn posts
- Email to bootstrap skill creators
- Post to relevant subreddits (r/ClaudeAI, r/LocalLLM, etc.)
- Prepare press kit

**By end of Week 6:**
- Secure, tested, documented
- Ready for public launch
- Marketing materials ready

---

## Technical Implementation Details

### CLI Tool Architecture (Go)

```
skillpm/
├── main.go              # Entry point
├── cmd/
│   ├── search.go        # Search command
│   ├── install.go       # Install command
│   ├── validate.go      # Validate command
│   └── ...
├── pkg/
│   ├── api/             # Registry API client
│   ├── manifest/        # YAML parsing & validation
│   ├── sandbox/         # Docker runner
│   ├── gpg/             # GPG signing/verification
│   ├── logger/          # Audit logging
│   └── config/          # Config file handling
├── tests/
└── go.mod
```

**Key Dependencies:**
- `github.com/urfave/cli/v2` — CLI argument parsing
- `gopkg.in/yaml.v3` — YAML parsing
- `github.com/ProtonMail/go-crypto` — GPG operations
- `github.com/docker/docker` — Docker API
- Standard library only for others

**No external dependencies for core functionality.** Docker is optional (graceful fallback to no sandboxing).

---

### Registry API Architecture (FastAPI)

```
registry/
├── main.py              # FastAPI app
├── routers/
│   ├── skills.py        # /api/v1/skills/*
│   ├── search.py        # /api/v1/search
│   └── auth.py          # /api/v1/auth
├── models/
│   ├── skill.py         # Skill model
│   └── user.py          # User model
├── db/
│   ├── schema.py        # Database schema
│   └── connection.py     # DB connection
├── services/
│   ├── validation.py     # Manifest validation
│   └── github.py         # GitHub integration
├── tests/
└── requirements.txt
```

**Key Dependencies:**
- `fastapi` — Web framework
- `sqlalchemy` — ORM
- `psycopg2` — PostgreSQL driver
- `pyyaml` — YAML parsing
- `requests` — HTTP client
- `pydantic` — Data validation

---

### Database Schema (PostgreSQL)

```sql
-- Users (GitHub OAuth)
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  github_id INT UNIQUE,
  username VARCHAR(255) UNIQUE,
  email VARCHAR(255),
  verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Skills
CREATE TABLE skills (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE,
  version VARCHAR(20),
  author_id INT REFERENCES users(id),
  description TEXT,
  license VARCHAR(50),
  repository_url VARCHAR(500),
  published_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Skill Metadata (denormalized for search)
CREATE TABLE skill_metadata (
  skill_id INT PRIMARY KEY REFERENCES skills(id),
  tags TEXT[], -- ARRAY
  language VARCHAR(50),
  target_llms TEXT[],
  capabilities JSONB, -- Stored as JSON
  dependencies JSONB
);

-- Downloads (analytics)
CREATE TABLE downloads (
  id SERIAL PRIMARY KEY,
  skill_id INT REFERENCES skills(id),
  downloaded_at TIMESTAMP DEFAULT NOW(),
  ip_hash VARCHAR(64) -- Anonymized IP for analytics
);

-- Audit Log
CREATE TABLE audit_log (
  id SERIAL PRIMARY KEY,
  action VARCHAR(100),
  skill_id INT REFERENCES skills(id),
  user_id INT REFERENCES users(id),
  details JSONB,
  timestamp TIMESTAMP DEFAULT NOW()
);
```

---

## Manifest Schema (Final Version)

```yaml
# Required
name: string                    # lowercase, alphanumeric-dash only
version: semver                 # 1.0.0
author: string                  # GitHub username
description: string             # Short description
license: string                 # MIT, Apache-2.0, etc.

# Implementation
entry_point: string             # Relative path to main file (e.g., skill.py)
language: string                # python, javascript, go
target_llms:
  - claude                      # Phase 1: claude only

# Security & Capabilities
capabilities:
  file_read:
    paths: [string]             # Allow reading from these paths
  file_write:
    paths: [string]             # Allow writing to these paths
  file_delete:
    paths: [string]             # Allow deleting from these paths
  network:
    - domain: string            # e.g., api.example.com
      protocol: [string]        # [http, https]
      ports: [int]              # Optional: [443]
  subprocess:
    allowed_commands: [string]  # Specific commands only
  skill_invoke:
    skills: [string]            # Which skills can be called
  user_data:
    fields: [string]            # User data access (careful!)
  system:
    env_vars: [string]          # Environment variables

# Dependencies
dependencies:
  skills: [string]              # Other skills: ["compression@^1.0"]
  system: [string]              # System packages: ["python3.9+"]

# Metadata
tags: [string]                  # Category tags
repository: string              # Full GitHub repo URL
homepage: string                # Documentation URL
requires:
  min_version: string            # Min skillpm version
author_verified: boolean        # Set by registry
maintenance_status: enum        # active, deprecated, archived
```

---

## Testing Strategy

### Unit Tests
- Manifest parser (valid/invalid YAML)
- Manifest validator (schema validation)
- Capability parser (capability names, paths)
- CLI argument parsing

### Integration Tests
- End-to-end: install → validate → run
- API: publish → search → install
- Sandbox: run skill with restricted file access
- GPG: sign → verify signature

### Security Tests
- Attempt sandbox escape (write outside allowed paths)
- Attempt network access to undeclared domains
- Attempt subprocess execution without declaration
- Invalid manifest with malicious paths
- Oversized inputs (DOS prevention)

### Load Tests
- 100 concurrent CLI installs
- 1000 API requests/minute
- Large file handling (100MB skill download)

---

## Rollout Strategy

### Soft Launch (Day 1)
- Announce to 20-30 beta testers
- Monitor for issues
- Fix critical bugs immediately
- Collect feedback

### Public Launch (Day 3-5)
- Tweet/announce broadly
- Post to subreddits
- Email developer lists
- Announce 15 bootstrap skills
- Share security audit (if done)

### Week 2
- Gather community feedback
- Push updates
- Onboard early creators
- Plan Phase 2

---

## Success Criteria for Phase 1

✅ **Technical:**
- CLI tool works on Linux, macOS, Windows
- API has 99%+ uptime
- No security incidents
- All tests pass

✅ **Community:**
- 50+ CLI downloads in first week
- 10+ community-submitted skills in first month
- 500+ registry views/day

✅ **Trust:**
- No security vulnerabilities found
- Positive community feedback
- Featured in AI newsletters/Reddit

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Sandbox escape | Critical | Test extensively, hire security audit |
| API downtime on launch | High | Load test, deploy on managed service |
| Creator doesn't submit skills | Medium | Prepare backup bootstrap skills |
| Community rejects tool | Medium | Gather early feedback, iterate quickly |
| Competitive store launches | High | Move fast, stay multi-LLM ready |

---

## Phase 1 Team & Timeline

### Recommended Team
- **Engineer 1** (CLI + infrastructure): 40 hrs/week
- **Engineer 2** (API + website): 40 hrs/week
- **Security reviewer**: 10 hrs/week
- **You** (project lead): coordination + community

### Timeline
- **Week -2 to 0:** Content seeding (parallel)
- **Weeks 1-4:** Core development
- **Weeks 5-6:** Hardening & launch
- **Total:** 6 weeks to public launch

### Budget
- **Engineering:** $0 (yourself or contractors)
- **Infrastructure:** $0-50 (free tier for MVP)
- **Domain:** $12/year
- **Optional security audit:** $5-10k
- **Creator incentives:** $2-3k (15 creators × $150)
- **Total: $2-13k** depending on audit

---

## Next Steps

1. **Get buy-in** — Share this plan with your team
2. **Finalize dates** — Lock in week-by-week schedule
3. **Recruit creators** — Start Phase -2 immediately
4. **Start engineering** — Week 1 begins
5. **Daily standups** — Sync every morning (15 min)

**Phase 1 Launch Target: 6 weeks**

---

## Appendix A: Command Reference

```bash
# Search & Discovery
skillpm search <query>
skillpm search --tag nlp
skillpm show <skill-name>
skillpm trending

# Installation & Management
skillpm install <skill-name>[@version]
skillpm uninstall <skill-name>
skillpm list
skillpm update [<skill-name>]

# Development
skillpm validate <path>
skillpm package <path>
skillpm publish <path>

# Configuration
skillpm config set registry <url>
skillpm config set sandbox <docker|none>
skillpm auth login

# System
skillpm version
skillpm --help
skillpm logs <skill-name>
```

---

## Appendix B: Bootstrap Skill List (Tier 1)

| # | Name | Use Case | Creator |
|---|------|----------|---------|
| 1 | Image Analyzer | Vision + metadata extraction | [TBD] |
| 2 | Code Reviewer | Security-focused code review | [TBD] |
| 3 | Doc Summarizer | Long-form document extraction | [TBD] |
| 4 | JSON Validator | JSON schema validation + fixing | [TBD] |
| 5 | SQL Generator | Convert English → SQL | [TBD] |
| 6 | Research Analyzer | Academic paper analysis | [TBD] |
| 7 | Meeting Analyzer | Transcript → summary + action items | [TBD] |
| 8 | Email Drafter | Context-aware email composition | [TBD] |
| 9 | API Doc Generator | Code → OpenAPI documentation | [TBD] |
| 10 | Support Classifier | Customer issue → category + priority | [TBD] |
| 11 | Price Comparator | E-commerce price scraping + analysis | [TBD] |
| 12 | Legal Analyzer | Contract analysis + risk flagging | [TBD] |
| 13 | Social Post Generator | Ideas → optimized social posts | [TBD] |
| 14 | SEO Analyzer | Website → SEO audit + fixes | [TBD] |
| 15 | Competitor Intel | Research → competitive analysis | [TBD] |

---

**Status: Ready to implement**

Phase 1 is achievable in 6 weeks with 2 engineers. The security-first approach (Docker + GPG from day 1) ensures you launch with confidence. The bootstrap skills strategy avoids the cold-start problem.

**Go build it.**
