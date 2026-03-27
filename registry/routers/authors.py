# SkillPM Registry - Authors Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import secrets

from ..db import connection, models
from ..schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserProfileResponse,
    ReviewCreate, ReviewResponse,
)
from ..schemas.skill import SkillResponse
from ..middleware.auth import get_current_user, get_current_user_optional, hash_api_key
from .skills import build_skill_response

router = APIRouter(prefix="/api/v1/authors", tags=["authors"])


@router.post("/register", status_code=201)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(connection.get_db),
):
    """
    Register a new author account.
    Returns the generated API key. This is the only time the key is shown.
    """
    existing = db.query(models.User).filter(
        models.User.username == user_in.username
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Generate API key
    api_key = f"skpm_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(api_key)

    user = models.User(
        username=user_in.username,
        email=user_in.email,
        display_name=user_in.display_name,
        bio=user_in.bio,
        website=user_in.website,
        gpg_public_key=user_in.gpg_public_key,
        api_key_hash=key_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "api_key": api_key,
        "message": "Save this API key securely. It will not be shown again.",
    }


@router.get("/me", response_model=UserProfileResponse)
def get_current_profile(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the authenticated user's full profile."""
    skill_count = db.query(models.Skill).filter(
        models.Skill.author_id == current_user.id
    ).count()

    total_downloads = (
        db.query(func.count(models.Download.id))
        .join(models.Skill, models.Download.skill_id == models.Skill.id)
        .filter(models.Skill.author_id == current_user.id)
        .scalar()
    ) or 0

    avg_rating = (
        db.query(func.avg(models.Review.rating))
        .join(models.Skill, models.Review.skill_id == models.Skill.id)
        .filter(models.Skill.author_id == current_user.id)
        .scalar()
    )

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "website": current_user.website,
        "gpg_public_key": current_user.gpg_public_key,
        "verified": current_user.verified,
        "skill_count": skill_count,
        "total_downloads": total_downloads,
        "avg_rating": round(float(avg_rating or 0), 1),
        "created_at": current_user.created_at,
    }


@router.put("/me", response_model=UserResponse)
def update_profile(
    user_in: UserUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update the authenticated user's profile."""
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    skill_count = db.query(models.Skill).filter(
        models.Skill.author_id == current_user.id
    ).count()

    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "website": current_user.website,
        "verified": current_user.verified,
        "skill_count": skill_count,
        "created_at": current_user.created_at,
    }


@router.post("/me/rotate-key")
def rotate_api_key(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Generate a new API key, invalidating the old one."""
    api_key = f"skpm_{secrets.token_urlsafe(32)}"
    current_user.api_key_hash = hash_api_key(api_key)
    db.commit()

    return {
        "api_key": api_key,
        "message": "Old API key has been invalidated. Save this new one securely.",
    }


@router.get("/{username}", response_model=UserResponse)
def get_author(
    username: str,
    db: Session = Depends(connection.get_db),
):
    """Get a public author profile."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Author not found")

    skill_count = db.query(models.Skill).filter(
        models.Skill.author_id == user.id,
        models.Skill.is_private == False,
    ).count()

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "website": user.website,
        "verified": user.verified,
        "skill_count": skill_count,
        "created_at": user.created_at,
    }


@router.get("/{username}/skills", response_model=List[SkillResponse])
def get_author_skills(
    username: str,
    db: Session = Depends(connection.get_db),
):
    """Get all public skills by an author."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Author not found")

    skills = (
        db.query(models.Skill)
        .filter(
            models.Skill.author_id == user.id,
            models.Skill.is_private == False,
        )
        .order_by(models.Skill.updated_at.desc())
        .all()
    )

    return [build_skill_response(db, s) for s in skills]


# --- Reviews ---

@router.get("/{username}/reviews", response_model=List[ReviewResponse])
def get_author_reviews(
    username: str,
    db: Session = Depends(connection.get_db),
):
    """Get all reviews written by this author."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Author not found")

    reviews = db.query(models.Review).filter(models.Review.user_id == user.id).all()
    results = []
    for r in reviews:
        skill = db.query(models.Skill).filter(models.Skill.id == r.skill_id).first()
        results.append({
            "id": r.id,
            "skill_name": skill.name if skill else "unknown",
            "username": user.username,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "created_at": r.created_at,
        })
    return results
