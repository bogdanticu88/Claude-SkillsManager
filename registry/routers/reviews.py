# SkillPM Registry - Reviews Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..db import connection, models
from ..schemas.user import ReviewCreate, ReviewResponse
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/skills", tags=["reviews"])


@router.get("/{name}/reviews", response_model=List[ReviewResponse])
def list_reviews(
    name: str,
    sort: str = Query("newest", regex="^(newest|oldest|highest|lowest)$"),
    db: Session = Depends(connection.get_db),
):
    """List all reviews for a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    query = db.query(models.Review).filter(models.Review.skill_id == skill.id)

    if sort == "oldest":
        query = query.order_by(models.Review.created_at.asc())
    elif sort == "highest":
        query = query.order_by(models.Review.rating.desc())
    elif sort == "lowest":
        query = query.order_by(models.Review.rating.asc())
    else:
        query = query.order_by(models.Review.created_at.desc())

    reviews = query.all()
    results = []
    for r in reviews:
        user = db.query(models.User).filter(models.User.id == r.user_id).first()
        results.append({
            "id": r.id,
            "skill_name": skill.name,
            "username": user.username if user else "unknown",
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "created_at": r.created_at,
        })
    return results


@router.post("/{name}/reviews", response_model=ReviewResponse, status_code=201)
def create_review(
    name: str,
    review_in: ReviewCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a review for a skill. One review per user per skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Cannot review own skill
    if skill.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot review your own skill")

    # Check for existing review
    existing = db.query(models.Review).filter(
        models.Review.skill_id == skill.id,
        models.Review.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already reviewed this skill. Use PUT to update.",
        )

    review = models.Review(
        skill_id=skill.id,
        user_id=current_user.id,
        rating=review_in.rating,
        title=review_in.title,
        body=review_in.body,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "skill_name": skill.name,
        "username": current_user.username,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "created_at": review.created_at,
    }


@router.put("/{name}/reviews", response_model=ReviewResponse)
def update_review(
    name: str,
    review_in: ReviewCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update your review for a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    review = db.query(models.Review).filter(
        models.Review.skill_id == skill.id,
        models.Review.user_id == current_user.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.rating = review_in.rating
    review.title = review_in.title
    review.body = review_in.body
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "skill_name": skill.name,
        "username": current_user.username,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "created_at": review.created_at,
    }


@router.delete("/{name}/reviews", status_code=204)
def delete_review(
    name: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete your review for a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    review = db.query(models.Review).filter(
        models.Review.skill_id == skill.id,
        models.Review.user_id == current_user.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return None


@router.get("/{name}/rating-summary")
def get_rating_summary(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """Get aggregate rating summary for a skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    result = db.query(
        func.avg(models.Review.rating),
        func.count(models.Review.id),
    ).filter(models.Review.skill_id == skill.id).first()

    # Rating distribution
    distribution = {}
    for rating in range(1, 6):
        count = db.query(models.Review).filter(
            models.Review.skill_id == skill.id,
            models.Review.rating == rating,
        ).count()
        distribution[str(rating)] = count

    return {
        "skill_name": name,
        "average_rating": round(float(result[0] or 0), 1),
        "total_reviews": result[1] or 0,
        "distribution": distribution,
    }
