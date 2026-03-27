# ADR-003: Open Source MIT License, No Monetization

Author: Bogdan Ticu
Date: March 27, 2026

## Problem

How should SkillPM be funded and licensed? Commercial or open source?

## Options Considered

1. Closed source with monetization (Phase 3)
   - Monthly subscriptions
   - Premium features
   - Pays for infrastructure
   - Problem: Users distrust closed registries

2. Open source, freemium model
   - Core free, premium analytics
   - Premium author dashboard
   - Problem: Conflicts with community values

3. MIT License, open source, completely free (chosen)
   - No monetization ever
   - Community contributions only
   - Sponsored by users who benefit
   - Problem: Need to sustain without revenue

## Decision

MIT License from day one. No monetization.

## Rationale

For a package manager, open source matters more than revenue:

- Users trust open source registries more
- Community can fork if needed
- Competitors can't kill it
- Lower barrier for contributors
- Aligns with Claude/AI community values

Sustainability comes from:
- Community contributions
- GitHub Sponsors (optional)
- Employer sponsorship (companies using it)
- Infrastructure donations

## Trade-offs

Negative:
- No revenue stream
- Relying on goodwill
- Infrastructure costs not covered directly

Positive:
- Zero conflicts of interest
- Maximum trust
- Aligned with community
- Stronger network effects
- More contributors

## Implementation

- License: MIT
- All code in GitHub, public
- No paywalls
- Authors can't restrict
- Anyone can fork and run registry

## Status

Approved. MIT, open source, free forever.
