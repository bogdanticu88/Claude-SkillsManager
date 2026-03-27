# SkillPM Registry - Search Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
from typing import List, Optional

from ..db import connection, models
from ..schemas.skill import SkillResponse
from .skills import build_skill_response

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/", response_model=List[SkillResponse])
def search_skills(
    q: str = Query("", description="Search query string"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    language: Optional[str] = Query(None, description="Filter by language"),
    llm: Optional[str] = Query(None, description="Filter by target LLM"),
    author: Optional[str] = Query(None, description="Filter by author username"),
    license: Optional[str] = Query(None, description="Filter by license"),
    sort: str = Query("relevance", regex="^(relevance|downloads|rating|name|newest)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(connection.get_db),
):
    """
    Full-text search across skill names, descriptions, and tags.
    Supports multiple filters and sorting options.
    """
    query = db.query(models.Skill).filter(models.Skill.is_private == False)

    # Text search across name and description
    if q:
        search_terms = q.strip().split()
        for term in search_terms:
            pattern = f"%{term}%"
            query = query.filter(
                or_(
                    models.Skill.name.ilike(pattern),
                    models.Skill.description.ilike(pattern),
                )
            )

    # Tag filter
    if tag:
        query = query.join(
            models.SkillMetadata,
            models.SkillMetadata.skill_id == models.Skill.id,
        ).filter(models.SkillMetadata.tags.contains([tag]))

    # Language filter
    if language:
        if not tag:
            query = query.join(
                models.SkillMetadata,
                models.SkillMetadata.skill_id == models.Skill.id,
            )
        query = query.filter(models.SkillMetadata.language == language)

    # LLM filter
    if llm:
        if not tag and not language:
            query = query.join(
                models.SkillMetadata,
                models.SkillMetadata.skill_id == models.Skill.id,
            )
        query = query.filter(models.SkillMetadata.target_llms.contains([llm]))

    # Author filter
    if author:
        author_user = db.query(models.User).filter(
            models.User.username == author
        ).first()
        if author_user:
            query = query.filter(models.Skill.author_id == author_user.id)
        else:
            return []

    # License filter
    if license:
        query = query.filter(models.Skill.license == license)

    # Sorting
    if sort == "name":
        query = query.order_by(models.Skill.name.asc())
    elif sort == "newest":
        query = query.order_by(models.Skill.published_at.desc())
    elif sort == "downloads":
        # Sort by download count using a subquery
        download_count = (
            db.query(
                models.Download.skill_id,
                func.count(models.Download.id).label("dl_count"),
            )
            .group_by(models.Download.skill_id)
            .subquery()
        )
        query = query.outerjoin(
            download_count, models.Skill.id == download_count.c.skill_id
        ).order_by(func.coalesce(download_count.c.dl_count, 0).desc())
    elif sort == "rating":
        rating_avg = (
            db.query(
                models.Review.skill_id,
                func.avg(models.Review.rating).label("avg_rating"),
            )
            .group_by(models.Review.skill_id)
            .subquery()
        )
        query = query.outerjoin(
            rating_avg, models.Skill.id == rating_avg.c.skill_id
        ).order_by(func.coalesce(rating_avg.c.avg_rating, 0).desc())
    else:
        # Default relevance: prefer exact name match, then name contains, then description
        if q:
            query = query.order_by(
                case(
                    (models.Skill.name == q, 0),
                    (models.Skill.name.ilike(f"{q}%"), 1),
                    (models.Skill.name.ilike(f"%{q}%"), 2),
                    else_=3,
                ),
                models.Skill.updated_at.desc(),
            )
        else:
            query = query.order_by(models.Skill.updated_at.desc())

    skills = query.offset(offset).limit(limit).all()
    return [build_skill_response(db, s) for s in skills]


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(connection.get_db),
):
    """Return quick name suggestions for autocomplete in CLI and web."""
    skills = (
        db.query(models.Skill.name, models.Skill.description)
        .filter(
            models.Skill.is_private == False,
            models.Skill.name.ilike(f"%{q}%"),
        )
        .limit(limit)
        .all()
    )

    return [
        {"name": s.name, "description": (s.description or "")[:80]}
        for s in skills
    ]


@router.get("/tags")
def list_tags(
    db: Session = Depends(connection.get_db),
):
    """Return all unique tags used across skills."""
    metadata_list = db.query(models.SkillMetadata.tags).all()
    tag_counts = {}
    for (tags,) in metadata_list:
        if tags:
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"tag": t, "count": c} for t, c in sorted_tags]
