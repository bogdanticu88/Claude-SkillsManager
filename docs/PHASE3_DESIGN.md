# SkillPM Phase 3 Design Summary
Author: Bogdan Ticu
License: MIT

## Status

Phase 3 is an ongoing/evolutionary phase. The foundational implementations
are in place. This document describes what has been built and what comes next.

## What Is Implemented

### Multi-LLM Support

All four LLM adapters are fully implemented in `pkg/adapters/`:

- **Claude** (`claude.go`) - Full Anthropic API integration with messages,
  vision, streaming, and tool use. Uses the Messages API v2023-06-01.

- **OpenAI/GPT-4** (`openai.go`) - Full OpenAI Chat Completions API
  integration with vision, function calling, and streaming support.

- **Gemini** (`gemini.go`) - Full Google Generative AI API integration
  with multimodal input, function declarations, and streaming.

- **Local LLM** (`local.go`) - OpenAI-compatible API adapter for Ollama,
  LocalAI, or any server that implements the /v1/chat/completions endpoint.

Every adapter implements the unified `LLMAdapter` interface:
- `Completion(prompt)` - basic text completion
- `CompletionWithSystem(system, prompt)` - completion with system message
- `Vision(prompt, imagePath)` - multimodal image+text
- `StreamCompletion(prompt, callback)` - streaming token output
- `ToolUse(prompt, tools)` - function/tool calling
- `MaxTokens()` - context window size
- `SupportsVision()` / `SupportsTools()` - capability queries

Usage in CLI: `skillpm run my-skill --llm gemini`

### Team Management

Full team management API implemented in `registry/routers/teams.py`:

- Team CRUD operations
- Role-based membership: owner, admin, developer, viewer
- Member management with role hierarchy enforcement
- Skill transfer between teams
- Permission checks at every level

### Governance

Governance infrastructure built into the registry:

- Moderation and reporting system (reports, resolution workflow)
- Admin-only endpoints for report resolution
- Skill deprecation and yanking
- Rate limiting to prevent abuse
- Audit logging for sandbox executions

## What Comes Next

### Advanced Workflows

Current workflow engine supports sequential, parallel, conditional execution
with error handling (retry, skip, fail). Future enhancements:

- **Data piping between steps** - pass structured output from one skill
  to the next skill's stdin
- **Workflow variables** - define variables at workflow level that steps
  can reference
- **Sub-workflows** - nest workflows inside workflows for reuse
- **Event triggers** - run workflows based on file changes, git hooks,
  or cron schedules
- **Workflow marketplace** - share and discover workflow templates

### Marketplace Features

- **Paid skills** - optional payment integration for premium skills
- **Skill bundles** - curated collections of related skills
- **Recommended skills** - recommendation engine based on usage patterns
- **Skill dependencies graph** - visual dependency explorer
- **Changelog feed** - RSS/webhook notifications for skill updates

### Security Enhancements

- **Reproducible builds** - verify that published skills match their source
- **Supply chain security** - dependency graph scanning for vulnerabilities
- **Namespace squatting protection** - reserve namespaces for verified orgs
- **Two-factor auth** - TOTP-based 2FA for author accounts
- **Signed commits** - verify git commit signatures match author keys

### Performance at Scale

- **Redis caching** - replace in-memory cache for multi-instance deployments
- **PostgreSQL** - production database with full-text search
- **CDN integration** - serve skill packages from edge locations
- **Background jobs** - async processing for analytics aggregation
- **Horizontal scaling** - stateless API servers behind load balancer

### Integration Points

- **GitHub Actions** - publish skills from CI/CD pipelines
- **VS Code extension** - browse and install skills from the editor
- **Slack/Discord bots** - run skills from chat
- **Webhook notifications** - notify on new versions, breaking changes
- **API SDK generation** - auto-generate client libraries for Python, JS, etc.
