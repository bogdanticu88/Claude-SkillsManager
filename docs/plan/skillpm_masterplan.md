# SkillPM: Package Manager for LLM Skills
## Master Plan & Technical Specification

**Document Version:** 1.0  
**Date:** March 27, 2026  
**Status:** Design Phase - Ready for Implementation  

---

## Executive Summary

SkillPM is a decentralized package manager for AI assistant skills (initially Claude, extensible to other LLMs). It solves the gap between static skill repositories and dynamic, discoverable, secure skill distribution. The system emphasizes fine-grained access control, runtime sandboxing, and transparent capability declaration.

**Core Problem:** Skills are valuable but scattered. No centralized registry, no discovery mechanism, no security model.

**Core Solution:** GitHub-backed skills + capability-based security + CLI package manager + searchable registry.

---

## Phase Architecture

### Phase 1: MVP (Weeks 1-4)
- Basic capability declaration (manifest)
- GitHub organization structure
- Simple CLI tool (install, search, list, validate)
- Static registry website
- Manual security review process
- Works with Claude only

### Phase 2: Production (Weeks 5-8)
- Sandboxing layer (Docker)
- Automated capability validation
- User consent/approval workflow
- Logging and audit trail
- Community contribution process
- Signed releases (author verification)

### Phase 3: Enterprise (Weeks 9+)
- OpenFGA integration for fine-grained authorization
- Multi-LLM support (GPT, Gemini, open-source)
- Advanced versioning and dependency resolution
- Monetization layer (optional)
- Governance formalization

---

## 1. Capability Ontology & Security Model

### 1.1 Core Capabilities

All skills must declare what they access. Reserved capability names:

```
FILE_READ       - Read files from specific paths
FILE_WRITE      - Write files to specific paths
FILE_DELETE     - Delete files from specific paths
NETWORK_HTTP    - Make HTTP requests to specific domains
NETWORK_HTTPS   - Make HTTPS requests to specific domains
SUBPROCESS      - Execute system subprocesses/shell commands
SKILL_INVOKE    - Call other skills by name
USER_DATA_READ  - Read user data fields (email, name, etc.)
SYSTEM_ENV      - Read/write environment variables
```

### 1.2 Principle: Least Privilege

Each skill declares exactly what it needs. Runtime enforces declarations. Violations are fatal (kill process).

### 1.3 Three-Layer Security Model

**Layer 1: Manifest Declaration**
- Skill declares capabilities in YAML manifest
- Example: `capabilities: [FILE_READ:[/tmp/uploads], NETWORK_HTTPS:[api.example.com]]`

**Layer 2: Static Validation**
- Automated checks on skill code to verify declared capabilities match actual usage
- Flag risky patterns (wildcard paths, subprocess with user input, etc.)
- Human review for high-risk skills

**Layer 3: Runtime Enforcement**
- Skill runs in sandboxed environment (Docker container with seccomp rules)
- OS-level access control prevents unauthorized file/network access
- All access attempts logged
- Violations trigger immediate process termination

---

## 2. Manifest Specification (YAML Schema)

### 2.1 Required Fields

```yaml
# Metadata
name: string                          # lowercase, alphanumeric-dash only
version: semver                       # 1.0.0 format
author: string                        # GitHub username or email
license: string                       # MIT, Apache-2.0, GPL-3.0, etc.
description: string                  # One-line description
repository: url                       # GitHub repo URL
homepage: url                         # Optional: external documentation

# Core
entry_point: string                   # Path to main skill file (e.g., skill.py)
language: string                      # python, javascript, go, rust
target_llms: [string]                 # ["claude"] for Phase 1

# Dependencies
dependencies:
  skills: [string]                    # Other skills, with versions: ["compression@^1.0", "metadata@>=2.0"]
  system: [string]                    # System packages: ["python3.9+", "ffmpeg"]

# Security & Capabilities
capabilities:
  file_read:
    paths: [string]                   # Exact paths or patterns: ["/tmp/uploads/*", "/home/user/docs"]
    
  file_write:
    paths: [string]                   # Where can it write?
    
  file_delete:
    paths: [string]                   # Where can it delete?
    
  network:
    - domain: string                  # e.g., "api.example.com"
      protocol: [string]              # ["http", "https"]
      ports: [int]                    # Optional: [443, 8443]
      
  subprocess:
    allowed_commands: [string]        # Specific commands only: ["ffmpeg", "imagemagick"]
    
  skill_invoke:
    skills: [string]                  # Which skills can it call?
    
  user_data:
    fields: [string]                  # ["email", "name"] — careful with this
    
  system:
    env_vars: [string]                # Which env vars can it read?

# Validation & Versioning
requires:
  min_version: semver                 # Minimum skill package manager version
  
tags: [string]                        # Category tags: ["image-processing", "nlp", "web"]

# Author/Trust
author_verified: boolean              # Set by registry after author verification
maintenance_status: enum              # active, deprecated, archived
```

### 2.2 Example Manifest

```yaml
name: image-analyzer
version: 1.2.3
author: alice-dev
license: MIT
description: "Analyzes images and extracts metadata using Claude vision"
repository: "https://github.com/skills/image-analyzer"
homepage: "https://docs.example.com/skills/image-analyzer"

entry_point: skill.py
language: python
target_llms: ["claude"]

dependencies:
  skills:
    - image-compression@^1.0.0
    - metadata-extractor@>=2.1.0
  system:
    - python3.9+
    - pillow

capabilities:
  file_read:
    paths:
      - /tmp/uploads/*
      - /home/user/images/*
      - /var/cache/skill-images/*
      
  file_write:
    paths:
      - /tmp/outputs/*
      
  network:
    - domain: api.anthropic.com
      protocol: [https]
      ports: [443]
      
  subprocess:
    allowed_commands:
      - identify
      - convert
      
  skill_invoke:
    skills:
      - image-compression
      - metadata-extractor
      
  user_data:
    fields: []  # This skill doesn't access user data

requires:
  min_version: 1.0.0

tags: ["image-processing", "vision", "metadata"]

author_verified: true
maintenance_status: active
```

---

## 3. Repository Structure

### 3.1 GitHub Organization

```
github.com/skillpm-registry/
├── image-analyzer/           # One repo per skill
│   ├── skill.py
│   ├── skill.yaml           # Manifest (required)
│   ├── README.md
│   ├── requirements.txt
│   ├── tests/
│   ├── docs/
│   └── .github/workflows/   # CI/CD for validation
├── compression-tool/
├── metadata-extractor/
└── ...
```

### 3.2 Individual Skill Repository

```
image-analyzer/
├── skill.yaml              # MANIFEST (required)
├── skill.py                # Entry point (required)
├── README.md               # Usage docs (required)
├── LICENSE                 # License file (required)
├── requirements.txt        # Python dependencies
├── tests/
│   ├── test_skill.py
│   └── fixtures/
├── docs/
│   ├── API.md
│   └── examples.md
├── .github/
│   └── workflows/
│       ├── validate.yml    # Runs capability validation
│       └── lint.yml        # Code quality checks
└── .gitignore
```

---

## 4. CLI Tool Specification

### 4.1 Core Commands

**Installation & Management:**
```bash
skillpm install <skill-name>[@version]
  # Fetches from registry, validates, sandboxes, asks for permission
  # Example: skillpm install image-analyzer@1.2.3

skillpm uninstall <skill-name>
  # Removes skill and cleans up

skillpm list
  # Shows installed skills and their versions

skillpm update [<skill-name>]
  # Updates all skills or specific skill to latest version

skillpm show <skill-name>
  # Shows metadata, capabilities, dependencies
```

**Discovery & Search:**
```bash
skillpm search <query>
  # Searches registry by name, description, tags
  # Example: skillpm search image

skillpm search --tag nlp
  # Filter by tags

skillpm trending
  # Most downloaded/rated skills
```

**Development & Validation:**
```bash
skillpm validate <path>
  # Validates skill manifest and code
  # Checks: YAML syntax, capability declarations match code, required files exist
  # Returns: pass/fail with detailed errors

skillpm package <path>
  # Creates distributable package (tarball)

skillpm test <path>
  # Runs skill tests (if test framework configured)

skillpm publish <path>
  # Publishes to registry (requires auth token)
```

**Configuration:**
```bash
skillpm config set registry <url>
  # Switch registry source

skillpm config set sandbox <docker|none>
  # Sandbox strategy (Phase 2+)

skillpm auth login
  # Authenticate with GitHub for publishing
```

### 4.2 CLI Implementation

**Technology:** Go or Rust (single binary, cross-platform, distributable via GitHub Releases)

**Core functionality:**
- Manifest parsing (YAML unmarshaling)
- HTTP client for registry API
- Local file system operations
- Git operations (clone skills from GitHub)
- Docker interaction (Phase 2+)
- Terminal UI (colored output, progress bars)

**Error Handling:**
- Network failures → clear error message + retry suggestion
- Invalid manifest → detailed validation error with line numbers
- Dependency conflicts → suggest resolution
- Permission errors → suggest running with sudo or fixing permissions

---

## 5. Registry Website Specification

### 5.1 Core Pages

**Homepage:**
- Search bar (prominent)
- Featured skills (curated)
- Statistics (total skills, downloads, contributors)
- Quick start guide link

**Skill Detail Page:**
- Manifest metadata (name, version, author, license)
- Description and documentation
- Installation command
- Capabilities (human-readable list)
- Dependencies (with links)
- Author profile
- Reviews/ratings (Phase 2+)
- Version history
- GitHub link

**Search Results:**
- Filterable by tag, author, language
- Sortable by downloads, rating, recency
- Pagination

**Author Profile:**
- Skills published
- Verification badge (if verified)
- Contact information

### 5.2 Registry Backend API

**Endpoints:**

```
GET /api/v1/skills                      # List all skills (paginated)
GET /api/v1/skills/<name>               # Get skill metadata
GET /api/v1/skills/<name>/<version>     # Get specific version
GET /api/v1/search?q=<query>&tag=<tag>  # Search/filter
POST /api/v1/skills/<name>/publish      # Publish new skill (requires auth)
GET /api/v1/authors/<username>          # Author profile
```

**Data stored:**
- Skill metadata (from manifest)
- Versions and release history
- Download counts
- User reviews/ratings (Phase 2+)
- Author information

**Technology:** PostgreSQL + FastAPI (Python) or Node.js/Express

### 5.3 Registry Website Stack

**Frontend:** Next.js or static site (Jekyll)
**Hosting:** Vercel or Netlify (free tier sufficient for MVP)
**CMS:** None (data driven from API)

---

## 6. Validation & Security Review Process

### 6.1 Automated Validation (Phase 1)

**Manifest Check:**
```
✓ YAML is valid
✓ All required fields present
✓ Semantic version is valid
✓ Capability names are from allowed set
✓ File paths don't have dangerous patterns (no / alone, no .., etc.)
```

**Code Analysis (Static):**
```
✓ Entry point file exists
✓ Required functions/exports present
✓ No hardcoded credentials detected
✓ No suspicious imports (subprocess without declaration, etc.)
✓ Dependencies match declared versions
```

**Warnings (not blockers):**
```
⚠ Skill has many capabilities (high privilege)
⚠ Skill depends on unverified author
⚠ Skill hasn't been updated in 6+ months
```

### 6.2 Human Review (Phase 1)

**Before registry approval:**
- One reviewer (can be community volunteer initially)
- Checklist:
  - [ ] Capabilities match actual code behavior
  - [ ] No hidden malicious code
  - [ ] Documentation is clear
  - [ ] Author is legitimate (GitHub history check)
- Review time: ~15-30 minutes per skill
- Approval or request for changes

**Phase 2+:** 
- Graduated reviews (less scrutiny for verified authors)
- Community voting on skill quality

### 6.3 Runtime Enforcement (Phase 2)

When skill is invoked:
1. Load sandbox environment with declared capabilities only
2. Block any file access outside declared paths
3. Block any network access to undeclared domains
4. Log all access attempts
5. Kill process if violation detected

---

## 7. Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)

**Week 1:**
- [ ] Design finalized (this document)
- [ ] Manifest schema written and validated
- [ ] GitHub organization created
- [ ] Example skills created (2-3 for testing)

**Week 2:**
- [ ] CLI tool scaffold (Go/Rust)
- [ ] Manifest parser implemented
- [ ] Basic validation logic
- [ ] Search/list functionality

**Week 3:**
- [ ] Registry backend API (CRUD for skills)
- [ ] PostgreSQL schema designed and created
- [ ] CLI install/uninstall functionality
- [ ] Tests written

**Week 4:**
- [ ] Registry website (static or simple dynamic)
- [ ] Documentation (README, getting started guide)
- [ ] Security review process documented
- [ ] First public beta release

**MVP Deliverables:**
- CLI tool (binary + installation script)
- Registry website (searchable, readable)
- 5-10 example skills (real, working)
- Documentation

---

### Phase 2: Production (Weeks 5-8)

**Week 5:**
- [ ] Docker sandboxing for skill execution
- [ ] Capability enforcement at runtime
- [ ] Logging and audit trail
- [ ] User consent workflow (CLI prompts)

**Week 6:**
- [ ] Signed releases (GPG/cryptography)
- [ ] Author verification process
- [ ] Community review workflow
- [ ] Dependency resolver (handle version conflicts)

**Week 7:**
- [ ] Rating/review system on website
- [ ] Advanced search (facets, sorting)
- [ ] Automated tests for skills (CI/CD)
- [ ] Stability testing and bug fixes

**Week 8:**
- [ ] Production deployment
- [ ] Performance optimization
- [ ] Security audit (external review)
- [ ] Release announcement

**Phase 2 Deliverables:**
- Hardened CLI with sandboxing
- Community trust model
- Governance documentation
- 50+ skills in registry

---

### Phase 3: Enterprise (Weeks 9+)

**Features:**
- [ ] OpenFGA integration (fine-grained authorization)
- [ ] Multi-LLM support (GPT-4, Gemini, open-source)
- [ ] Advanced versioning (breaking change detection)
- [ ] Skill monetization layer (optional)
- [ ] Organizational/team features
- [ ] Skill bundling (collections)
- [ ] Analytics dashboard for authors

---

## 8. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Malicious skill uploaded | High | Automated validation + human review before registry approval |
| Skill escapes sandbox | High | Defense in depth: seccomp + Docker + capability enforcement |
| Author identity spoofing | Medium | GPG signature verification + GitHub identity linking |
| Registry downtime | Medium | Mirror on community servers, fallback to direct GitHub |
| Supply chain attack (dependency) | Medium | Lock dependency versions, scan for known vulnerabilities |
| Community friction (bad reviews) | Low | Clear CoC, neutral moderation policy |

---

## 9. Success Metrics

**Phase 1:**
- 5+ skills published
- 50+ CLI downloads
- 0 security incidents

**Phase 2:**
- 50+ skills in registry
- 500+ CLI downloads
- Active community (10+ contributors)
- 0 sandbox escapes

**Phase 3:**
- 200+ skills
- 5,000+ CLI downloads
- Multi-LLM support live
- Sustainable governance model

---

## 10. Governance & Community

### 10.1 Code of Conduct
- Respectful collaboration
- No harassment, discrimination
- Security first
- Clear escalation path

### 10.2 Contribution Process
1. Fork skill repository
2. Make changes
3. Submit PR with tests
4. Review and approval
5. Merge and auto-publish to registry

### 10.3 Dispute Resolution
- Technical issues: GitHub issues
- Code review disagreements: maintainer decides
- CoC violations: Review committee
- Escalation: Neutral third party (if needed)

---

## 11. Technical Dependencies

### CLI Tool Requirements
- Language: Go or Rust
- Dependencies: Minimal (YAML parser, HTTP client, Git)
- Binaries: Available for Linux, macOS, Windows
- Distribution: GitHub Releases, Homebrew (optional)

### Registry Backend
- Database: PostgreSQL 13+
- Language: Python (FastAPI) or Node.js (Express)
- Caching: Redis (optional, for performance)
- Authentication: GitHub OAuth

### Registry Website
- Framework: Next.js or Jekyll
- Hosting: Vercel or Netlify
- CDN: CloudFlare (free tier ok)

### Sandboxing (Phase 2)
- Docker (required)
- Seccomp rules
- AppArmor or SELinux (Linux)

---

## 12. Budget & Resource Estimate

### Development Time
- **Phase 1 (MVP):** 160-200 hours
- **Phase 2 (Production):** 120-160 hours
- **Phase 3 (Enterprise):** 80+ hours ongoing

### Infrastructure (minimal)
- **Phase 1:** Free (GitHub + Vercel/Netlify free tiers)
- **Phase 2:** $50-100/month (PostgreSQL hosting, Docker registry)
- **Phase 3:** $200-500/month (scale)

### Team
- **Ideal:** 2 full-stack engineers + 1 security reviewer
- **Minimum:** 1 engineer (part-time possible for MVP)

---

## 13. Alternative Approaches Considered & Rejected

| Approach | Why Rejected |
|----------|-------------|
| Centralized skill hosting | Too much operational burden, single point of failure |
| No security model | Dangerous, skills need least-privilege execution |
| Cloud-only sandboxing | Expensive, slow, unnecessary for MVP |
| Blockchain-based registry | Overkill, adds complexity, slow |
| Only works with Claude | Limits market, future-proof for multi-LLM now |

---

## 14. Open Questions & Future Decisions

- [ ] Monetization model (free forever, or enterprise tier?)
- [ ] Should skills be open-source only, or allow closed-source?
- [ ] How to handle skill deprecation/removal?
- [ ] Community moderation: volunteers or paid team?
- [ ] Should skills be runnable standalone, or only via package manager?

---

## Appendices

### A. Example Skill Implementation (Python)

```python
# skill.py
"""
Image analyzer skill for Claude.
Analyzes images and extracts metadata.
"""

import json
from pathlib import Path

def analyze(image_path: str) -> dict:
    """
    Analyze image and return metadata.
    
    Args:
        image_path: Full path to image file
        
    Returns:
        Dictionary with analysis results
    """
    # Verify path is in allowed range (security)
    path = Path(image_path).resolve()
    allowed_dirs = ["/tmp/uploads", "/home/user/images"]
    
    if not any(str(path).startswith(d) for d in allowed_dirs):
        raise PermissionError(f"Path {image_path} not allowed")
    
    # Read image metadata
    with open(path, 'rb') as f:
        image_data = f.read()
    
    # Parse and return results
    return {
        "file": str(path),
        "size_bytes": len(image_data),
        "format": path.suffix.lower(),
        "status": "analyzed"
    }

# Export for CLI/registry discovery
SKILL_EXPORTS = {
    "analyze": analyze
}
```

### B. Example Registry API Response

```json
GET /api/v1/skills/image-analyzer/1.2.3

{
  "name": "image-analyzer",
  "version": "1.2.3",
  "author": "alice-dev",
  "description": "Analyzes images and extracts metadata",
  "license": "MIT",
  "repository": "https://github.com/skillpm-registry/image-analyzer",
  "downloads_total": 1245,
  "downloads_month": 342,
  "rating": 4.7,
  "reviews_count": 23,
  "capabilities": [
    "FILE_READ:/tmp/uploads/*",
    "FILE_READ:/home/user/images/*",
    "SKILL_INVOKE:image-compression",
    "NETWORK_HTTPS:api.anthropic.com"
  ],
  "dependencies": {
    "skills": ["image-compression@^1.0.0"],
    "system": ["python3.9+"]
  },
  "author_verified": true,
  "maintenance_status": "active",
  "install_command": "skillpm install image-analyzer@1.2.3",
  "tags": ["image-processing", "vision", "metadata"],
  "release_date": "2026-03-15",
  "updated_at": "2026-03-25"
}
```

---

## Final Notes

This master plan is comprehensive but not final. Implementation will surface questions and edge cases. Treat this as a living document:

1. Update as decisions are made
2. Track decisions and rationale
3. Adjust timelines as needed
4. Gather community feedback at each phase

**Next Step:** Present this to engineering team, gather feedback, finalize Phase 1 sprints.

---

**Document prepared for:** Implementation team / Partner LLM (Gemini, etc.)
**Date prepared:** March 27, 2026
**Status:** Ready for development kickoff
