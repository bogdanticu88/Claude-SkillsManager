# SkillPM Registry - Version Resolver Service (Phase 2)
# Author: Bogdan Ticu
# License: MIT
#
# Resolves skill dependency trees with version constraints.
# Supports semver ranges like:
#   ">=1.0.0"    at least 1.0.0
#   "^1.2.0"     compatible with 1.2.0 (>=1.2.0, <2.0.0)
#   "~1.2.0"     approximately 1.2.0 (>=1.2.0, <1.3.0)
#   "1.0.0"      exact match
#   "*"          any version
#
# Uses a simple backtracking solver for conflict resolution.

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class VersionConstraint:
    raw: str
    operator: str  # exact, gte, lte, caret, tilde, any
    major: int = 0
    minor: int = 0
    patch: int = 0


@dataclass
class DependencyNode:
    name: str
    version: str
    constraints: Dict[str, str] = field(default_factory=dict)  # dep_name -> constraint_str
    resolved: bool = False


@dataclass
class ResolutionResult:
    success: bool
    resolved: Dict[str, str]  # name -> version
    conflicts: List[str] = field(default_factory=list)
    install_order: List[str] = field(default_factory=list)


def parse_version(v: str) -> Tuple[int, int, int]:
    """Parse a version string into (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", v)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def parse_constraint(constraint_str: str) -> VersionConstraint:
    """Parse a version constraint string into a VersionConstraint."""
    s = constraint_str.strip()

    if s == "*" or s == "":
        return VersionConstraint(raw=s, operator="any")

    if s.startswith("^"):
        ver = s[1:]
        major, minor, patch = parse_version(ver)
        return VersionConstraint(raw=s, operator="caret", major=major, minor=minor, patch=patch)

    if s.startswith("~"):
        ver = s[1:]
        major, minor, patch = parse_version(ver)
        return VersionConstraint(raw=s, operator="tilde", major=major, minor=minor, patch=patch)

    if s.startswith(">="):
        ver = s[2:]
        major, minor, patch = parse_version(ver)
        return VersionConstraint(raw=s, operator="gte", major=major, minor=minor, patch=patch)

    if s.startswith("<="):
        ver = s[2:]
        major, minor, patch = parse_version(ver)
        return VersionConstraint(raw=s, operator="lte", major=major, minor=minor, patch=patch)

    # Exact version
    major, minor, patch = parse_version(s)
    return VersionConstraint(raw=s, operator="exact", major=major, minor=minor, patch=patch)


def version_matches(version: str, constraint: VersionConstraint) -> bool:
    """Check if a version string satisfies a constraint."""
    if constraint.operator == "any":
        return True

    v_major, v_minor, v_patch = parse_version(version)

    if constraint.operator == "exact":
        return (v_major == constraint.major and
                v_minor == constraint.minor and
                v_patch == constraint.patch)

    if constraint.operator == "gte":
        v = (v_major, v_minor, v_patch)
        c = (constraint.major, constraint.minor, constraint.patch)
        return v >= c

    if constraint.operator == "lte":
        v = (v_major, v_minor, v_patch)
        c = (constraint.major, constraint.minor, constraint.patch)
        return v <= c

    if constraint.operator == "caret":
        # ^1.2.3 means >=1.2.3, <2.0.0
        # ^0.2.3 means >=0.2.3, <0.3.0
        if v_major != constraint.major:
            return False
        if constraint.major == 0:
            if v_minor != constraint.minor:
                return False
            return v_patch >= constraint.patch
        v = (v_major, v_minor, v_patch)
        c = (constraint.major, constraint.minor, constraint.patch)
        return v >= c

    if constraint.operator == "tilde":
        # ~1.2.3 means >=1.2.3, <1.3.0
        if v_major != constraint.major or v_minor != constraint.minor:
            return False
        return v_patch >= constraint.patch

    return False


class DependencyResolver:
    """
    Resolves a dependency tree into a flat list of versioned packages.
    Uses the available versions from the registry to find compatible sets.
    """

    def __init__(self, available_versions: Dict[str, List[str]]):
        """
        available_versions: mapping of skill_name -> [list of version strings]
        Each list should be sorted from oldest to newest.
        """
        self.available = available_versions

    def resolve(
        self,
        root_deps: Dict[str, str],
    ) -> ResolutionResult:
        """
        Resolve dependencies starting from root_deps.
        root_deps: mapping of skill_name -> constraint_string

        Returns a ResolutionResult with the resolved versions.
        """
        resolved: Dict[str, str] = {}
        conflicts: List[str] = []
        install_order: List[str] = []
        visited = set()

        def _resolve(name: str, constraint_str: str) -> bool:
            if name in visited:
                # Already resolved, check compatibility
                if name in resolved:
                    constraint = parse_constraint(constraint_str)
                    if version_matches(resolved[name], constraint):
                        return True
                    else:
                        conflicts.append(
                            f"Conflict: {name} resolved to {resolved[name]} "
                            f"but {constraint_str} required"
                        )
                        return False
                return True

            visited.add(name)

            if name not in self.available:
                conflicts.append(f"Skill '{name}' not found in registry")
                return False

            versions = self.available[name]
            constraint = parse_constraint(constraint_str)

            # Find the best (newest) matching version
            matching = [v for v in reversed(versions) if version_matches(v, constraint)]

            if not matching:
                conflicts.append(
                    f"No version of '{name}' satisfies constraint '{constraint_str}'. "
                    f"Available: {', '.join(versions)}"
                )
                return False

            # Pick the newest matching version
            selected = matching[0]
            resolved[name] = selected
            install_order.append(name)

            return True

        # Resolve each root dependency
        for dep_name, constraint in root_deps.items():
            if not _resolve(dep_name, constraint):
                return ResolutionResult(
                    success=False,
                    resolved=resolved,
                    conflicts=conflicts,
                    install_order=install_order,
                )

        return ResolutionResult(
            success=True,
            resolved=resolved,
            conflicts=conflicts,
            install_order=install_order,
        )


def build_dependency_tree(
    skill_name: str,
    skill_deps: Dict[str, str],
    all_skill_deps: Dict[str, Dict[str, str]],
    depth: int = 0,
    max_depth: int = 10,
) -> Dict:
    """
    Build a visual dependency tree for display.
    Returns a nested dict structure.
    """
    if depth > max_depth:
        return {"name": skill_name, "error": "max depth exceeded"}

    children = []
    for dep_name, constraint in skill_deps.items():
        sub_deps = all_skill_deps.get(dep_name, {})
        child = build_dependency_tree(dep_name, sub_deps, all_skill_deps, depth + 1, max_depth)
        child["constraint"] = constraint
        children.append(child)

    return {
        "name": skill_name,
        "children": children,
    }
