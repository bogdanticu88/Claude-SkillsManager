# ADR-001: Docker Sandboxing in Phase 1

Author: Bogdan Ticu
Date: March 27, 2026

## Problem

Skills can access files and network. Without sandboxing, a malicious skill could steal data or do harm. Moving Docker to Phase 2 means launching with weak security.

## Options Considered

1. No sandboxing (Phase 1)
   - Fast launch
   - Manual review only
   - Users at risk if review misses malicious code
   - Trust is broken on first incident

2. Docker sandboxing in Phase 1 (chosen)
   - Slower Phase 1
   - Real security
   - Users safe from mistakes
   - Trust is solid at launch

3. Cloud-only sandboxing
   - Requires backend resources
   - Expensive
   - Complicated setup
   - Unnecessary for MVP

## Decision

Docker sandboxing in Phase 1, Week 3.

## Rationale

- Security is core feature, not nice-to-have
- Docker is simple, we can do it fast
- Users won't trust open registry without it
- Better to be late with safety than fast with risk
- Containers are already in skillpm code

## Trade-offs

Negative:
- Takes time in Phase 1
- Adds complexity early
- Docker dependency required

Positive:
- Users safe from day one
- Competitive advantage over loose alternatives
- Trust built into DNA
- Can claim "verified safe" at launch

## Implementation

Week 3:
- seccomp profiles for syscall filtering
- Resource limits (memory, CPU)
- Network policy enforcement
- All tests pass

Manifest declares resources needed:
```yaml
resources:
  memory: 512MB
  cpu: 1
```

## Status

Approved. Build Docker sandboxing in week 3.
