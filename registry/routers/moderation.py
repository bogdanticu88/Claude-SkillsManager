# SkillPM Registry - Moderation Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import datetime

from ..db import connection, models
from ..middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/moderation", tags=["moderation"])


class ReportCreate(BaseModel):
    skill_name: str
    reason: str
    details: str


class ReportResponse(BaseModel):
    id: int
    skill_id: int
    reason: str
    details: str
    reported_at: datetime.datetime
    resolved: bool
    resolution_note: str = None

    class Config:
        from_attributes = True


class ResolveReport(BaseModel):
    resolution_note: str
    action: str = "none"  # none, yank, delete


@router.post("/report", response_model=ReportResponse, status_code=201)
def report_skill(
    report_in: ReportCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Report a skill for policy violation."""
    skill = db.query(models.Skill).filter(
        models.Skill.name == report_in.skill_name
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    db_report = models.Report(
        skill_id=skill.id,
        reporter_id=current_user.id,
        reason=report_in.reason,
        details=report_in.details,
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


@router.get("/reports", response_model=List[ReportResponse])
def list_reports(
    resolved: bool = False,
    db: Session = Depends(connection.get_db),
    admin: models.User = Depends(require_admin),
):
    """List reports. Admin only."""
    return (
        db.query(models.Report)
        .filter(models.Report.resolved == resolved)
        .order_by(models.Report.reported_at.desc())
        .all()
    )


@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    resolve_in: ResolveReport,
    db: Session = Depends(connection.get_db),
    admin: models.User = Depends(require_admin),
):
    """Resolve a report. Admin only."""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.resolved = True
    report.resolved_at = datetime.datetime.utcnow()
    report.resolution_note = resolve_in.resolution_note

    # Take action on the skill if needed
    if resolve_in.action == "yank":
        skill = db.query(models.Skill).filter(models.Skill.id == report.skill_id).first()
        if skill:
            skill.deprecated = True
            skill.deprecated_message = f"Yanked due to report: {resolve_in.resolution_note}"
    elif resolve_in.action == "delete":
        skill = db.query(models.Skill).filter(models.Skill.id == report.skill_id).first()
        if skill:
            db.delete(skill)

    db.commit()
    return {"status": "resolved", "action": resolve_in.action}
