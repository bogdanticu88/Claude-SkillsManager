# SkillPM Registry - Breaking Change Detection Service (Phase 2)
# Author: Bogdan Ticu
# License: MIT
#
# Compares two versions of a skill manifest to detect breaking changes.
# A breaking change is any modification that could cause existing users
# of the skill to experience failures when upgrading.
#
# Breaking changes include:
# - Removing capabilities that downstream skills depend on
# - Changing entry point
# - Changing language
# - Removing tags (may break discovery)
# - Removing supported LLMs
# - Removing dependency skills
# - Changing the skill name

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import re


class BreakingChange(BaseModel):
    severity: str  # critical, major, minor
    field: str
    description: str
    old_value: Any = None
    new_value: Any = None


class CompatibilityReport(BaseModel):
    old_version: str
    new_version: str
    is_compatible: bool
    breaking_changes: List[BreakingChange]
    warnings: List[str]
    suggested_version: str
    migration_notes: List[str]


def compare_versions(old_manifest: Dict, new_manifest: Dict) -> CompatibilityReport:
    """
    Compare two manifest dicts and return a compatibility report.
    old_manifest and new_manifest are dicts from the YAML manifests
    or from the stored manifest_snapshot on a SkillVersion.
    """
    changes: List[BreakingChange] = []
    warnings: List[str] = []
    migration_notes: List[str] = []

    old_ver = old_manifest.get("version", "0.0.0")
    new_ver = new_manifest.get("version", "0.0.0")

    # --- Critical: name change ---
    if old_manifest.get("name") != new_manifest.get("name"):
        changes.append(BreakingChange(
            severity="critical",
            field="name",
            description="Skill name changed. All references by name will break.",
            old_value=old_manifest.get("name"),
            new_value=new_manifest.get("name"),
        ))
        migration_notes.append(
            f"Update all references from '{old_manifest.get('name')}' to '{new_manifest.get('name')}'"
        )

    # --- Critical: language change ---
    if old_manifest.get("language") != new_manifest.get("language"):
        old_lang = old_manifest.get("language", "unknown")
        new_lang = new_manifest.get("language", "unknown")
        if old_lang != "unknown" and new_lang != "unknown":
            changes.append(BreakingChange(
                severity="critical",
                field="language",
                description="Runtime language changed. Execution environment will differ.",
                old_value=old_lang,
                new_value=new_lang,
            ))
            migration_notes.append(
                f"Language changed from {old_lang} to {new_lang}. "
                f"Update your Docker images and runtime dependencies."
            )

    # --- Major: entry point change ---
    if old_manifest.get("entry_point") != new_manifest.get("entry_point"):
        old_ep = old_manifest.get("entry_point")
        new_ep = new_manifest.get("entry_point")
        if old_ep and new_ep and old_ep != new_ep:
            changes.append(BreakingChange(
                severity="major",
                field="entry_point",
                description="Entry point changed.",
                old_value=old_ep,
                new_value=new_ep,
            ))

    # --- Major: removed target LLMs ---
    old_llms = set(old_manifest.get("target_llms", []))
    new_llms = set(new_manifest.get("target_llms", []))
    removed_llms = old_llms - new_llms
    if removed_llms:
        changes.append(BreakingChange(
            severity="major",
            field="target_llms",
            description=f"Removed LLM support: {', '.join(removed_llms)}",
            old_value=list(old_llms),
            new_value=list(new_llms),
        ))
        migration_notes.append(
            f"Support for {', '.join(removed_llms)} has been removed. "
            f"Switch to one of: {', '.join(new_llms)}"
        )

    added_llms = new_llms - old_llms
    if added_llms:
        warnings.append(f"Added LLM support: {', '.join(added_llms)}")

    # --- Major: capability changes ---
    old_caps = old_manifest.get("capabilities", {}) or {}
    new_caps = new_manifest.get("capabilities", {}) or {}

    # Check for removed capabilities
    for cap_name in old_caps:
        if cap_name not in new_caps:
            changes.append(BreakingChange(
                severity="major",
                field=f"capabilities.{cap_name}",
                description=f"Capability '{cap_name}' was removed.",
                old_value=old_caps[cap_name],
                new_value=None,
            ))

    # Check for new capabilities (warning, not breaking)
    for cap_name in new_caps:
        if cap_name not in old_caps:
            warnings.append(f"New capability added: {cap_name}")

    # --- Minor: removed dependencies ---
    old_deps = old_manifest.get("dependencies", {}) or {}
    new_deps = new_manifest.get("dependencies", {}) or {}

    old_skill_deps = set(old_deps.get("skills", []))
    new_skill_deps = set(new_deps.get("skills", []))

    removed_deps = old_skill_deps - new_skill_deps
    if removed_deps:
        changes.append(BreakingChange(
            severity="minor",
            field="dependencies.skills",
            description=f"Removed skill dependencies: {', '.join(removed_deps)}",
            old_value=list(old_skill_deps),
            new_value=list(new_skill_deps),
        ))

    added_deps = new_skill_deps - old_skill_deps
    if added_deps:
        warnings.append(f"New skill dependencies added: {', '.join(added_deps)}")
        migration_notes.append(
            f"Install new dependencies: {', '.join(added_deps)}"
        )

    # --- Minor: license change ---
    if old_manifest.get("license") != new_manifest.get("license"):
        old_lic = old_manifest.get("license", "unspecified")
        new_lic = new_manifest.get("license", "unspecified")
        changes.append(BreakingChange(
            severity="minor",
            field="license",
            description=f"License changed from {old_lic} to {new_lic}.",
            old_value=old_lic,
            new_value=new_lic,
        ))
        migration_notes.append(
            f"Review the new license ({new_lic}) for compliance with your project."
        )

    # --- Determine compatibility and suggest version ---
    is_compatible = len(changes) == 0

    has_critical = any(c.severity == "critical" for c in changes)
    has_major = any(c.severity == "major" for c in changes)

    suggested_version = suggest_version_bump(old_ver, has_critical, has_major, len(changes) > 0)

    return CompatibilityReport(
        old_version=old_ver,
        new_version=new_ver,
        is_compatible=is_compatible,
        breaking_changes=changes,
        warnings=warnings,
        suggested_version=suggested_version,
        migration_notes=migration_notes,
    )


def suggest_version_bump(current: str, has_critical: bool, has_major: bool, has_changes: bool) -> str:
    """
    Suggest the next version number based on detected changes.
    Follows semver: major.minor.patch
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", current)
    if not match:
        return current

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))

    if has_critical or has_major:
        return f"{major + 1}.0.0"
    elif has_changes:
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def check_dependency_impact(
    skill_name: str,
    breaking_changes: List[BreakingChange],
    all_skills: List[Dict],
) -> List[Dict]:
    """
    Given a skill's breaking changes, find all other skills that depend
    on this skill and would be impacted.
    """
    impacted = []
    for skill in all_skills:
        deps = skill.get("dependencies", {}) or {}
        skill_deps = deps.get("skills", [])
        if skill_name in skill_deps:
            impact_details = []
            for bc in breaking_changes:
                if bc.severity in ("critical", "major"):
                    impact_details.append(bc.description)

            if impact_details:
                impacted.append({
                    "skill_name": skill.get("name"),
                    "current_version": skill.get("version"),
                    "impact": impact_details,
                })

    return impacted
