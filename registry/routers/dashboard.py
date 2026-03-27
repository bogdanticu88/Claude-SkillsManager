# SkillPM Registry - Analytics Dashboard Router (Phase 1.5)
# Author: Bogdan Ticu
# License: MIT
#
# Provides endpoints for the analytics dashboard:
# - Installation trends over time
# - Error rate tracking
# - User rating distributions
# - Performance metrics (execution times)
# - Per-skill and global analytics

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
import datetime

from ..db import connection, models
from ..middleware.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/installs-over-time")
def installs_over_time(
    skill_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """
    Get daily installation counts for the past N days.
    Optionally filter by skill name.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = db.query(
        func.date(models.InstallEvent.created_at).label("date"),
        func.count(models.InstallEvent.id).label("count"),
    ).filter(
        models.InstallEvent.created_at >= cutoff,
        models.InstallEvent.action == "install",
    )

    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        query = query.filter(models.InstallEvent.skill_id == skill.id)

    results = query.group_by("date").order_by("date").all()

    return {
        "period_days": days,
        "skill": skill_name or "all",
        "data": [
            {"date": str(r.date), "installs": r.count}
            for r in results
        ],
    }


@router.get("/downloads-over-time")
def downloads_over_time(
    skill_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """Get daily download counts."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = db.query(
        func.date(models.Download.downloaded_at).label("date"),
        func.count(models.Download.id).label("count"),
    ).filter(models.Download.downloaded_at >= cutoff)

    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        query = query.filter(models.Download.skill_id == skill.id)

    results = query.group_by("date").order_by("date").all()

    return {
        "period_days": days,
        "skill": skill_name or "all",
        "data": [
            {"date": str(r.date), "downloads": r.count}
            for r in results
        ],
    }


@router.get("/error-rates")
def error_rates(
    skill_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """
    Get error rates over time. Returns daily success/failure counts.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    base_filter = [models.ExecutionEvent.executed_at >= cutoff]
    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        base_filter.append(models.ExecutionEvent.skill_id == skill.id)

    results = (
        db.query(
            func.date(models.ExecutionEvent.executed_at).label("date"),
            models.ExecutionEvent.status,
            func.count(models.ExecutionEvent.id).label("count"),
        )
        .filter(*base_filter)
        .group_by("date", models.ExecutionEvent.status)
        .order_by("date")
        .all()
    )

    # Merge into per-day records
    day_map = {}
    for r in results:
        date_str = str(r.date)
        if date_str not in day_map:
            day_map[date_str] = {"date": date_str, "success": 0, "failure": 0}
        if r.status == "SUCCESS":
            day_map[date_str]["success"] = r.count
        else:
            day_map[date_str]["failure"] = r.count

    data = sorted(day_map.values(), key=lambda x: x["date"])
    for d in data:
        total = d["success"] + d["failure"]
        d["error_rate"] = round(d["failure"] / total * 100, 1) if total > 0 else 0

    return {
        "period_days": days,
        "skill": skill_name or "all",
        "data": data,
    }


@router.get("/performance")
def performance_metrics(
    skill_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """
    Get execution performance metrics: avg, p50, p95, p99 durations.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = db.query(models.ExecutionEvent.duration_ms).filter(
        models.ExecutionEvent.executed_at >= cutoff,
        models.ExecutionEvent.duration_ms != None,
        models.ExecutionEvent.status == "SUCCESS",
    )

    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        query = query.filter(models.ExecutionEvent.skill_id == skill.id)

    durations = sorted([r[0] for r in query.all()])

    if not durations:
        return {
            "skill": skill_name or "all",
            "period_days": days,
            "count": 0,
            "avg_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
        }

    count = len(durations)
    avg = sum(durations) / count

    def percentile(data, p):
        idx = int(len(data) * p / 100)
        idx = min(idx, len(data) - 1)
        return data[idx]

    return {
        "skill": skill_name or "all",
        "period_days": days,
        "count": count,
        "avg_ms": round(avg, 1),
        "p50_ms": percentile(durations, 50),
        "p95_ms": percentile(durations, 95),
        "p99_ms": percentile(durations, 99),
        "min_ms": durations[0],
        "max_ms": durations[-1],
    }


@router.get("/rating-trends")
def rating_trends(
    skill_name: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """Get rating trends over time."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = db.query(
        func.date(models.Review.created_at).label("date"),
        func.avg(models.Review.rating).label("avg_rating"),
        func.count(models.Review.id).label("count"),
    ).filter(models.Review.created_at >= cutoff)

    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        query = query.filter(models.Review.skill_id == skill.id)

    results = query.group_by("date").order_by("date").all()

    return {
        "period_days": days,
        "skill": skill_name or "all",
        "data": [
            {
                "date": str(r.date),
                "avg_rating": round(float(r.avg_rating or 0), 1),
                "count": r.count,
            }
            for r in results
        ],
    }


@router.get("/top-errors")
def top_errors(
    skill_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(connection.get_db),
):
    """Get the most common error messages."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = (
        db.query(
            models.ExecutionEvent.error_message,
            func.count(models.ExecutionEvent.id).label("count"),
        )
        .filter(
            models.ExecutionEvent.executed_at >= cutoff,
            models.ExecutionEvent.status == "FAILURE",
            models.ExecutionEvent.error_message != None,
        )
    )

    if skill_name:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        query = query.filter(models.ExecutionEvent.skill_id == skill.id)

    results = (
        query.group_by(models.ExecutionEvent.error_message)
        .order_by(func.count(models.ExecutionEvent.id).desc())
        .limit(limit)
        .all()
    )

    return {
        "period_days": days,
        "skill": skill_name or "all",
        "errors": [
            {"message": r[0][:300], "count": r[1]}
            for r in results
        ],
    }


@router.get("/llm-usage")
def llm_usage(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(connection.get_db),
):
    """Get LLM usage breakdown across all executions."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    results = (
        db.query(
            models.ExecutionEvent.llm_used,
            func.count(models.ExecutionEvent.id).label("count"),
        )
        .filter(
            models.ExecutionEvent.executed_at >= cutoff,
            models.ExecutionEvent.llm_used != None,
        )
        .group_by(models.ExecutionEvent.llm_used)
        .order_by(func.count(models.ExecutionEvent.id).desc())
        .all()
    )

    total = sum(r[1] for r in results)

    return {
        "period_days": days,
        "total_executions": total,
        "breakdown": [
            {
                "llm": r[0],
                "count": r[1],
                "percentage": round(r[1] / total * 100, 1) if total > 0 else 0,
            }
            for r in results
        ],
    }
