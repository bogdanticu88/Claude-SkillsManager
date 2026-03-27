# ADR-002: GPG Signing for Skill Verification

Author: Bogdan Ticu
Date: March 27, 2026

## Problem

How do users verify a skill actually came from who it claims? Without signing, attackers could swap skills or publish under fake names.

## Options Considered

1. No signing (Phase 1)
   - Fast
   - Trust on registry only
   - Can be spoofed if registry compromised
   - No author verification

2. GPG signing (chosen)
   - Authors sign manifests
   - CLI verifies signature
   - Cryptographic proof of authorship
   - Works even if registry down

3. X.509 certificates
   - More complex
   - Requires certificate authority
   - Overkill for MVP

## Decision

GPG signing in Phase 1, Week 4.

## Rationale

- Cheap and simple
- Standard in open source (git, npm, etc.)
- Users understand it
- Doesn't require central authority
- Works offline

## Trade-offs

Negative:
- Authors need to set up GPG
- Key management overhead
- Small learning curve

Positive:
- Genuine author proof
- Can't be forged
- Works forever
- Industry standard

## Implementation

Week 4:
```
skillpm auth gen-key --name "Author Name" --email "author@example.com"
skillpm package <skill-dir>
  - Signs manifest
  - Creates skill.yaml.asc
skillpm install <skill>
  - Verifies signature
  - Shows author fingerprint
```

Skill verification adds step but minimal friction.

## Status

Approved. Add GPG signing in week 4.
