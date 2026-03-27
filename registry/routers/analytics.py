# SkillPM Registry - Analytics Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from pydantic import BaseModel
import datetime

from ..db import connection, models
from ..middleware.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class ExecutionReport(BaseModel):
    skill_name: str
    version: Optional[str] = None
    status: str  # SUCCESS, FAILURE
    duration_ms: int
    error_message: Optional[str] = None
    llm_used: Optional[str] = None


class InstallReport(BaseModel):
    skill_name: str
    version: Optional[str] = None
    action: str  # install, uninstall, update


@router.post("/execution")
def report_execution(
    report_in: ExecutionReport,
    db: Session = Depends(connection.get_db),
):
    """Report a skill execution event from the CLI."""
    skill = db.query(models.Skill).filter(
        models.Skill.name == report_in.skill_name
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    event = models.ExecutionEvent(
        skill_id=skill.id,
        version=report_in.version or skill.version,
        status=report_in.status,
        duration_ms=report_in.duration_ms,
        error_message=report_in.error_message,
        llm_used=report_in.llm_used,
    )
    db.add(event)
    db.commit()
    return {"status": "recorded"}


@router.post("/install")
def report_install(
    report_in: InstallReport,
    db: Session = Depends(connection.get_db),
):
    """Report a skill install/uninstall/update event from the CLI."""
    skill = db.query(models.Skill).filter(
        models.Skill.name == report_in.skill_name
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    event = models.InstallEvent(
        skill_id=skill.id,
        version=report_in.version or skill.version,
        action=report_in.action,
    )
    db.add(event)
    db.commit()
    return {"status": "recorded"}


@router.get("/skill/{name}")
def get_skill_analytics(
    name: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """Get analytics for a single skill."""
    skill = db.query(models.Skill).filter(models.Skill.name == name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    # Execution stats
    total_executions = db.query(models.ExecutionEvent).filter(
        models.ExecutionEvent.skill_id == skill.id,
        models.ExecutionEvent.executed_at >= cutoff,
    ).count()

    success_count = db.query(models.ExecutionEvent).filter(
        models.ExecutionEvent.skill_id == skill.id,
        models.ExecutionEvent.status == "SUCCESS",
        models.ExecutionEvent.executed_at >= cutoff,
    ).count()

    avg_duration = db.query(func.avg(models.ExecutionEvent.duration_ms)).filter(
        models.ExecutionEvent.skill_id == skill.id,
        models.ExecutionEvent.executed_at >= cutoff,
    ).scalar()

    # Download stats
    total_downloads = db.query(models.Download).filter(
        models.Download.skill_id == skill.id,
    ).count()

    recent_downloads = db.query(models.Download).filter(
        models.Download.skill_id == skill.id,
        models.Download.downloaded_at >= cutoff,
    ).count()

    # Install stats
    total_installs = db.query(models.InstallEvent).filter(
        models.InstallEvent.skill_id == skill.id,
        models.InstallEvent.action == "install",
    ).count()

    # Review stats
    avg_rating = db.query(func.avg(models.Review.rating)).filter(
        models.Review.skill_id == skill.id,
    ).scalar()

    review_count = db.query(models.Review).filter(
        models.Review.skill_id == skill.id,
    ).count()

    # Common errors
    errors = (
        db.query(
            models.ExecutionEvent.error_message,
            func.count(models.ExecutionEvent.id).label("count"),
        )
        .filter(
            models.ExecutionEvent.skill_id == skill.id,
            models.ExecutionEvent.status == "FAILURE",
            models.ExecutionEvent.error_message != None,
            models.ExecutionEvent.executed_at >= cutoff,
        )
        .group_by(models.ExecutionEvent.error_message)
        .order_by(func.count(models.ExecutionEvent.id).desc())
        .limit(5)
        .all()
    )

    # LLM usage breakdown
    llm_usage = (
        db.query(
            models.ExecutionEvent.llm_used,
            func.count(models.ExecutionEvent.id).label("count"),
        )
        .filter(
            models.ExecutionEvent.skill_id == skill.id,
            models.ExecutionEvent.llm_used != None,
            models.ExecutionEvent.executed_at >= cutoff,
        )
        .group_by(models.ExecutionEvent.llm_used)
        .all()
    )

    return {
        "skill_name": name,
        "period_days": days,
        "executions": {
            "total": total_executions,
            "success_count": success_count,
            "failure_count": total_executions - success_count,
            "success_rate": round(
                (success_count / total_executions * 100) if total_executions > 0 else 0, 1
            ),
            "avg_duration_ms": round(float(avg_duration or 0), 1),
        },
        "downloads": {
            "total": total_downloads,
            "recent": recent_downloads,
        },
        "installs": {
            "total": total_installs,
        },
        "ratings": {
            "average": round(float(avg_rating or 0), 1),
            "count": review_count,
        },
        "top_errors": [
            {"message": e[0][:200], "count": e[1]} for e in errors
        ],
        "llm_breakdown": {
            e[0]: e[1] for e in llm_usage
        },
    }


@router.get("/author/{username}")
def get_author_analytics(
    username: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """Get aggregate analytics for all skills by an author."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Author not found")

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    skill_ids = [
        s.id for s in db.query(models.Skill.id).filter(
            models.Skill.author_id == user.id
        ).all()
    ]

    if not skill_ids:
        return {
            "author": username,
            "period_days": days,
            "total_skills": 0,
            "total_downloads": 0,
            "total_executions": 0,
            "avg_rating": 0,
            "skills": [],
        }

    total_downloads = db.query(models.Download).filter(
        models.Download.skill_id.in_(skill_ids),
    ).count()

    total_executions = db.query(models.ExecutionEvent).filter(
        models.ExecutionEvent.skill_id.in_(skill_ids),
        models.ExecutionEvent.executed_at >= cutoff,
    ).count()

    avg_rating = db.query(func.avg(models.Review.rating)).filter(
        models.Review.skill_id.in_(skill_ids),
    ).scalar()

    # Per-skill breakdown
    per_skill = []
    for sid in skill_ids:
        skill = db.query(models.Skill).filter(models.Skill.id == sid).first()
        dl_count = db.query(models.Download).filter(
            models.Download.skill_id == sid
        ).count()
        exec_count = db.query(models.ExecutionEvent).filter(
            models.ExecutionEvent.skill_id == sid,
            models.ExecutionEvent.executed_at >= cutoff,
        ).count()
        per_skill.append({
            "name": skill.name,
            "downloads": dl_count,
            "executions": exec_count,
        })

    per_skill.sort(key=lambda x: x["downloads"], reverse=True)

    return {
        "author": username,
        "period_days": days,
        "total_skills": len(skill_ids),
        "total_downloads": total_downloads,
        "total_executions": total_executions,
        "avg_rating": round(float(avg_rating or 0), 1),
        "skills": per_skill,
    }


@router.get("/global")
def get_global_analytics(
    db: Session = Depends(connection.get_db),
):
    """Get global registry statistics."""
    total_skills = db.query(models.Skill).filter(
        models.Skill.is_private == False
    ).count()
    total_authors = db.query(models.User).count()
    total_downloads = db.query(models.Download).count()
    total_executions = db.query(models.ExecutionEvent).count()
    total_reviews = db.query(models.Review).count()

    # Top skills by downloads
    top_downloaded = (
        db.query(
            models.Skill.name,
            func.count(models.Download.id).label("dl_count"),
        )
        .join(models.Download, models.Download.skill_id == models.Skill.id)
        .group_by(models.Skill.name)
        .order_by(func.count(models.Download.id).desc())
        .limit(10)
        .all()
    )

    # Newest skills
    newest = (
        db.query(models.Skill.name, models.Skill.version, models.Skill.published_at)
        .filter(models.Skill.is_private == False)
        .order_by(models.Skill.published_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_skills": total_skills,
        "total_authors": total_authors,
        "total_downloads": total_downloads,
        "total_executions": total_executions,
        "total_reviews": total_reviews,
        "top_downloaded": [
            {"name": t[0], "downloads": t[1]} for t in top_downloaded
        ],
        "newest_skills": [
            {"name": n[0], "version": n[1], "published_at": str(n[2])}
            for n in newest
        ],
    }
