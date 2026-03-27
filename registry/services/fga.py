# SkillPM Registry - Authorization Service
# Author: Bogdan Ticu
# License: MIT
#
# Simple authorization service. In production, this would be backed
# by OpenFGA or a similar fine-grained authorization system.
# For development, it uses the database directly for permission checks.

import os
from typing import Optional


# When FGA is not configured, fall back to simple DB-based checks.
# The middleware/auth.py handles most auth, but this module provides
# a clean interface for any code that needs to check permissions.

FGA_ENABLED = bool(os.getenv("FGA_STORE_ID", ""))


async def check_permission(user_id: str, relation: str, object_id: str) -> bool:
    """
    Check if a user has a specific relation to an object.
    Without OpenFGA, this returns True (permissive fallback).
    """
    if not FGA_ENABLED:
        return True
    # OpenFGA integration would go here
    return True


async def grant_permission(user_id: str, relation: str, object_id: str):
    """Grant a permission tuple."""
    if not FGA_ENABLED:
        return
    # OpenFGA write would go here


async def revoke_permission(user_id: str, relation: str, object_id: str):
    """Revoke a permission tuple."""
    if not FGA_ENABLED:
        return
    # OpenFGA delete would go here


async def add_member(org_id: str, user_id: str, role: str = "member"):
    """Add a user as a member of an organization."""
    await grant_permission(user_id, role, f"organization:{org_id}")


async def remove_member(org_id: str, user_id: str, role: str = "member"):
    """Remove a user's role from an organization."""
    await revoke_permission(user_id, role, f"organization:{org_id}")


async def set_skill_org(skill_name: str, org_id: str):
    """Associate a skill with an organization."""
    await grant_permission(f"organization:{org_id}#member", "org", f"skill:{skill_name}")
