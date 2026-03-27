# SkillPM Registry - Compatibility and Version Management Router (Phase 2)
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Optional
from pydantic import BaseModel

from ..db import connection, models
from ..services.breaking_changes import compare_versions, check_dependency_impact
from ..services.version_resolver import DependencyResolver, build_dependency_tree

router = APIRouter(prefix="/api/v1/compatibility", tags=["compatibility"])


class ManifestCompareRequest(BaseModel):
    old_manifest: Dict
    new_manifest: Dict


@router.post("/check")
def check_compatibility(
    request: ManifestCompareRequest,
):
    """
    Compare two manifest dicts and return a compatibility report.
    Send the old and new manifest as JSON objects.
    """
    report = compare_versions(request.old_manifest, request.new_manifest)
    return report.model_dump()


@router.get("/check/{name}")
def check_skill_compatibility(
    name: str,
    old_version: str = Query(..., description="Old version to compare from"),
    new_version: str = Query(..., description="New version to compare to"),
    db: Session = Depends(connection.get_db),
):
    """
    Compare two stored versions of a skill and return a compatibility report.
    """
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    old_ver = db.query(models.SkillVersion).filter(
        models.SkillVersion.skill_id == skill.id,
        models.SkillVersion.version == old_version,
    ).first()
    if not old_ver:
        raise HTTPException(status_code=404, detail=f"Version {old_version} not found")

    new_ver = db.query(models.SkillVersion).filter(
        models.SkillVersion.skill_id == skill.id,
        models.SkillVersion.version == new_version,
    ).first()
    if not new_ver:
        raise HTTPException(status_code=404, detail=f"Version {new_version} not found")

    old_manifest = old_ver.manifest_snapshot or {"version": old_version, "name": name}
    new_manifest = new_ver.manifest_snapshot or {"version": new_version, "name": name}

    report = compare_versions(old_manifest, new_manifest)

    # Check impact on dependent skills
    if report.breaking_changes:
        all_skills = []
        for s in db.query(models.Skill).all():
            meta = db.query(models.SkillMetadata).filter(
                models.SkillMetadata.skill_id == s.id
            ).first()
            all_skills.append({
                "name": s.name,
                "version": s.version,
                "dependencies": meta.dependencies if meta else {},
            })

        impacted = check_dependency_impact(name, report.breaking_changes, all_skills)
        return {
            **report.model_dump(),
            "impacted_skills": impacted,
        }

    return report.model_dump()


@router.post("/resolve")
def resolve_dependencies(
    dependencies: Dict[str, str],
    db: Session = Depends(connection.get_db),
):
    """
    Resolve a set of dependency constraints against the registry.
    Input: {"skill-name": "^1.0.0", "other-skill": ">=2.1.0"}
    """
    # Build available versions map from the database
    available: Dict[str, list] = {}
    for s in db.query(models.Skill).all():
        versions = db.query(models.SkillVersion).filter(
            models.SkillVersion.skill_id == s.id,
            models.SkillVersion.yanked == False,
        ).order_by(models.SkillVersion.published_at.asc()).all()

        available[s.name] = [v.version for v in versions]

    resolver = DependencyResolver(available)
    result = resolver.resolve(dependencies)

    return {
        "success": result.success,
        "resolved": result.resolved,
        "conflicts": result.conflicts,
        "install_order": result.install_order,
    }


@router.get("/tree/{name}")
def dependency_tree(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """
    Build and return the full dependency tree for a skill.
    """
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Build a map of all skill dependencies
    all_skill_deps = {}
    for s in db.query(models.Skill).all():
        meta = db.query(models.SkillMetadata).filter(
            models.SkillMetadata.skill_id == s.id
        ).first()
        if meta and meta.dependencies:
            deps = meta.dependencies
            skill_deps = {}
            if isinstance(deps, dict) and "skills" in deps:
                # Convert list to constraint map
                for dep in deps.get("skills", []):
                    if isinstance(dep, str):
                        skill_deps[dep] = "*"
                    elif isinstance(dep, dict):
                        for k, v in dep.items():
                            skill_deps[k] = v
            all_skill_deps[s.name] = skill_deps

    root_deps = all_skill_deps.get(name, {})
    tree = build_dependency_tree(name, root_deps, all_skill_deps)

    return tree
