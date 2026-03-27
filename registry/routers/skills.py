# SkillPM Registry - Skills Router (Complete CRUD)
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import hashlib
import datetime

from ..db import connection, models
from ..schemas.skill import (
    SkillCreate, SkillUpdate, SkillResponse, SkillListResponse,
    SkillMetadataOut, VersionCreate, VersionResponse,
)
from ..middleware.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


def build_skill_response(db: Session, skill: models.Skill) -> dict:
    """Build a standard skill response dict from a Skill model."""
    author = db.query(models.User).filter(models.User.id == skill.author_id).first()
    metadata = db.query(models.SkillMetadata).filter(
        models.SkillMetadata.skill_id == skill.id
    ).first()
    download_count = db.query(models.Download).filter(
        models.Download.skill_id == skill.id
    ).count()

    # Calculate average rating
    rating_result = db.query(
        func.avg(models.Review.rating),
        func.count(models.Review.id),
    ).filter(models.Review.skill_id == skill.id).first()
    avg_rating = round(float(rating_result[0] or 0), 1)
    review_count = rating_result[1] or 0

    org = None
    if skill.org_id:
        org = db.query(models.Organization).filter(
            models.Organization.id == skill.org_id
        ).first()

    return {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "long_description": skill.long_description,
        "license": skill.license,
        "repository_url": skill.repository_url,
        "homepage_url": skill.homepage_url,
        "entry_point": skill.entry_point,
        "language": skill.language,
        "author_username": author.username if author else "unknown",
        "download_count": download_count,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "is_private": skill.is_private,
        "deprecated": skill.deprecated,
        "org_name": org.name if org else None,
        "published_at": skill.published_at,
        "updated_at": skill.updated_at,
        "metadata": {
            "tags": metadata.tags if metadata else [],
            "language": metadata.language if metadata else "unknown",
            "target_llms": metadata.target_llms if metadata else [],
            "capabilities": metadata.capabilities if metadata else {},
            "dependencies": metadata.dependencies if metadata else {},
            "min_skillpm_version": metadata.min_skillpm_version if metadata else None,
        },
    }


@router.get("/", response_model=SkillListResponse)
def list_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("updated", regex="^(updated|name|downloads|rating)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    tag: Optional[str] = None,
    language: Optional[str] = None,
    author: Optional[str] = None,
    db: Session = Depends(connection.get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    """List all public skills with pagination, sorting, and filtering."""
    query = db.query(models.Skill).filter(models.Skill.is_private == False)

    # Filter by author
    if author:
        author_user = db.query(models.User).filter(models.User.username == author).first()
        if author_user:
            query = query.filter(models.Skill.author_id == author_user.id)
        else:
            return {"skills": [], "total": 0, "page": page, "per_page": per_page}

    # Filter by tag
    if tag:
        query = query.join(models.SkillMetadata).filter(
            models.SkillMetadata.tags.contains([tag])
        )

    # Filter by language
    if language:
        if not tag:
            query = query.join(models.SkillMetadata)
        query = query.filter(models.SkillMetadata.language == language)

    # Sorting
    if sort == "name":
        order_col = models.Skill.name
    elif sort == "downloads":
        # Subquery for download count sorting
        query = query  # We will sort after fetching for SQLite compat
        order_col = models.Skill.updated_at
    elif sort == "rating":
        order_col = models.Skill.updated_at
    else:
        order_col = models.Skill.updated_at

    if order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    total = query.count()
    offset = (page - 1) * per_page
    skills = query.offset(offset).limit(per_page).all()

    results = [build_skill_response(db, s) for s in skills]

    return {
        "skills": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{name}", response_model=SkillResponse)
def get_skill(
    name: str,
    request: Request,
    db: Session = Depends(connection.get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
):
    """Get a single skill by name. Records a download event."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.is_private:
        if not current_user:
            raise HTTPException(status_code=403, detail="Private skill requires authentication")
        if skill.author_id != current_user.id:
            # Check org membership
            if skill.org_id:
                member = db.query(models.OrganizationMember).filter(
                    models.OrganizationMember.org_id == skill.org_id,
                    models.OrganizationMember.user_id == current_user.id,
                ).first()
                if not member:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=403, detail="Access denied")

    # Record download
    ip_addr = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(ip_addr.encode()).hexdigest()
    user_agent = request.headers.get("user-agent", "")
    db_download = models.Download(
        skill_id=skill.id,
        version=skill.version,
        ip_hash=ip_hash,
        user_agent=user_agent[:512] if user_agent else None,
    )
    db.add(db_download)
    db.commit()

    return build_skill_response(db, skill)


@router.post("/", response_model=SkillResponse, status_code=201)
def create_skill(
    skill_in: SkillCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create (publish) a new skill to the registry. Requires authentication."""
    # Verify user is publishing as themselves
    if current_user.username != skill_in.author_username:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Cannot publish as another user"}
        )

    author = current_user

    # Check for duplicate name
    existing = db.query(models.Skill).filter(models.Skill.name == skill_in.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Skill name already taken")

    # Resolve organization
    org_id = None
    if skill_in.org_name:
        org = db.query(models.Organization).filter(
            models.Organization.name == skill_in.org_name
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        org_id = org.id

    # Create skill
    db_skill = models.Skill(
        name=skill_in.name,
        version=skill_in.version,
        description=skill_in.description,
        long_description=skill_in.long_description,
        license=skill_in.license,
        repository_url=str(skill_in.repository_url) if skill_in.repository_url else None,
        homepage_url=str(skill_in.homepage_url) if skill_in.homepage_url else None,
        entry_point=skill_in.entry_point,
        language=skill_in.language or skill_in.metadata.language,
        author_id=author.id,
        org_id=org_id,
        is_private=skill_in.is_private,
        signature=skill_in.signature,
    )
    db.add(db_skill)
    
    try:
        db.commit()
        db.refresh(db_skill)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"code": "DATABASE_ERROR", "message": "Failed to create skill"})

    # Create metadata
    db_metadata = models.SkillMetadata(
        skill_id=db_skill.id,
        tags=skill_in.metadata.tags,
        language=skill_in.metadata.language,
        target_llms=skill_in.metadata.target_llms,
        capabilities=skill_in.metadata.capabilities,
        dependencies=skill_in.metadata.dependencies,
        min_skillpm_version=skill_in.metadata.min_skillpm_version,
    )
    db.add(db_metadata)

    # Create initial version record
    db_version = models.SkillVersion(
        skill_id=db_skill.id,
        version=skill_in.version,
        changelog="Initial release",
        signature=skill_in.signature,
    )
    db.add(db_version)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"code": "DATABASE_ERROR", "message": "Failed to create skill metadata"})
        
    return build_skill_response(db, db_skill)


@router.put("/{name}", response_model=SkillResponse)
def update_skill(
    name: str,
    skill_in: SkillUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update an existing skill. Only the author or org admin can update."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Check ownership
    if skill.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author can update this skill")

    # Update fields
    update_data = skill_in.model_dump(exclude_unset=True)

    if "metadata" in update_data and update_data["metadata"]:
        meta_data = update_data.pop("metadata")
        metadata = db.query(models.SkillMetadata).filter(
            models.SkillMetadata.skill_id == skill.id
        ).first()
        if metadata:
            for k, v in meta_data.items():
                setattr(metadata, k, v)
        else:
            db.add(models.SkillMetadata(skill_id=skill.id, **meta_data))
    else:
        update_data.pop("metadata", None)

    for key, value in update_data.items():
        setattr(skill, key, value)

    skill.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(skill)

    return build_skill_response(db, skill)


@router.delete("/{name}", status_code=204)
def delete_skill(
    name: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a skill. Only the author or an admin can delete."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author or admin can delete this skill")

    db.delete(skill)
    db.commit()
    return None


# --- Version Management ---

@router.get("/{name}/versions", response_model=List[VersionResponse])
def list_versions(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """List all versions of a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    versions = db.query(models.SkillVersion).filter(
        models.SkillVersion.skill_id == skill.id
    ).order_by(models.SkillVersion.published_at.desc()).all()

    return versions


@router.post("/{name}/versions", response_model=VersionResponse, status_code=201)
def publish_version(
    name: str,
    version_in: VersionCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Publish a new version of a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author can publish new versions")

    # Check for duplicate version
    existing = db.query(models.SkillVersion).filter(
        models.SkillVersion.skill_id == skill.id,
        models.SkillVersion.version == version_in.version,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Version already exists")

    db_version = models.SkillVersion(
        skill_id=skill.id,
        version=version_in.version,
        changelog=version_in.changelog,
        manifest_snapshot=version_in.manifest_snapshot,
        signature=version_in.signature,
    )
    db.add(db_version)

    # Update the skill's current version
    skill.version = version_in.version
    skill.updated_at = datetime.datetime.utcnow()
    if version_in.signature:
        skill.signature = version_in.signature

    db.commit()
    db.refresh(db_version)

    return db_version


@router.post("/{name}/versions/{version}/yank", status_code=200)
def yank_version(
    name: str,
    version: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Yank (soft-delete) a version so it cannot be installed."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the author can yank versions")

    db_version = db.query(models.SkillVersion).filter(
        models.SkillVersion.skill_id == skill.id,
        models.SkillVersion.version == version,
    ).first()
    if not db_version:
        raise HTTPException(status_code=404, detail="Version not found")

    db_version.yanked = True
    db.commit()

    return {"status": "yanked", "version": version}
