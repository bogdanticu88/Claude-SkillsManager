# SkillPM Registry - Teams and Governance Router (Phase 3)
# Author: Bogdan Ticu
# License: MIT
#
# Provides team management, role-based access, and governance features:
# - Team creation and member management
# - Role-based permissions (owner, admin, developer, viewer)
# - Skill transfer between teams
# - Governance policies

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import datetime

from ..db import connection, models
from ..middleware.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    member_count: int = 0
    skill_count: int = 0


class TeamMemberAdd(BaseModel):
    username: str
    role: str = "developer"  # owner, admin, developer, viewer


class TeamMemberResponse(BaseModel):
    username: str
    role: str
    display_name: Optional[str] = None


class SkillTransfer(BaseModel):
    skill_name: str
    target_org: str


def build_team_response(db: Session, org: models.Organization) -> dict:
    member_count = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id
    ).count()
    skill_count = db.query(models.Skill).filter(
        models.Skill.org_id == org.id
    ).count()
    return {
        "id": org.id,
        "name": org.name,
        "display_name": org.display_name,
        "description": org.description,
        "member_count": member_count,
        "skill_count": skill_count,
    }


@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new team. The creating user becomes the owner."""
    existing = db.query(models.Organization).filter(
        models.Organization.name == team_in.name
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Team name already taken")

    org = models.Organization(
        name=team_in.name,
        display_name=team_in.display_name or team_in.name,
        description=team_in.description,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    member = models.OrganizationMember(
        org_id=org.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)
    db.commit()

    return build_team_response(db, org)


@router.get("/my-teams", response_model=List[TeamResponse])
def list_my_teams(
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all teams the current user belongs to."""
    memberships = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.user_id == current_user.id
    ).all()

    teams = []
    for m in memberships:
        org = db.query(models.Organization).filter(
            models.Organization.id == m.org_id
        ).first()
        if org:
            resp = build_team_response(db, org)
            resp["my_role"] = m.role
            teams.append(resp)

    return teams


@router.get("/{name}", response_model=TeamResponse)
def get_team(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """Get team details."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")
    return build_team_response(db, org)


@router.put("/{name}", response_model=TeamResponse)
def update_team(
    name: str,
    team_in: TeamUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update team details. Admin or owner only."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")

    member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role.in_(["owner", "admin"]),
    ).first()
    if not member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin or owner access required")

    update_data = team_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(org, key):
            setattr(org, key, value)
    db.commit()
    db.refresh(org)

    return build_team_response(db, org)


@router.get("/{name}/members", response_model=List[TeamMemberResponse])
def list_team_members(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """List all members of a team with their roles."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")

    members = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id
    ).all()

    results = []
    for m in members:
        user = db.query(models.User).filter(models.User.id == m.user_id).first()
        results.append({
            "username": user.username if user else "unknown",
            "role": m.role,
            "display_name": user.display_name if user else None,
        })
    return results


@router.post("/{name}/members", status_code=201)
def add_team_member(
    name: str,
    member_in: TeamMemberAdd,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a member to a team. Admin or owner only."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check permissions
    admin_member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role.in_(["owner", "admin"]),
    ).first()
    if not admin_member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin or owner access required")

    # Only owners can add admins or owners
    if member_in.role in ("admin", "owner") and (not admin_member or admin_member.role != "owner"):
        raise HTTPException(status_code=403, detail="Only owners can add admins or owners")

    user = db.query(models.User).filter(
        models.User.username == member_in.username
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    member = models.OrganizationMember(
        org_id=org.id,
        user_id=user.id,
        role=member_in.role,
    )
    db.add(member)
    db.commit()

    return {"status": "added", "username": member_in.username, "role": member_in.role}


@router.put("/{name}/members/{username}/role")
def update_member_role(
    name: str,
    username: str,
    role: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Change a member's role. Owner only for elevated roles."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")

    owner_member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role == "owner",
    ).first()
    if not owner_member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Owner access required")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if role not in ("owner", "admin", "developer", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    member.role = role
    db.commit()

    return {"status": "updated", "username": username, "role": role}


@router.delete("/{name}/members/{username}", status_code=204)
def remove_team_member(
    name: str,
    username: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a member from a team."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")

    admin_member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role.in_(["owner", "admin"]),
    ).first()
    if not admin_member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Prevent removing the last owner
    if member.role == "owner":
        owner_count = db.query(models.OrganizationMember).filter(
            models.OrganizationMember.org_id == org.id,
            models.OrganizationMember.role == "owner",
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    db.delete(member)
    db.commit()
    return None


@router.post("/{name}/transfer-skill")
def transfer_skill(
    name: str,
    transfer: SkillTransfer,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Transfer a skill from one team to another."""
    # Verify source team
    source_org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not source_org:
        raise HTTPException(status_code=404, detail="Source team not found")

    # Check source admin
    source_admin = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == source_org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role.in_(["owner", "admin"]),
    ).first()
    if not source_admin and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required on source team")

    # Verify target team
    target_org = db.query(models.Organization).filter(
        models.Organization.name == transfer.target_org
    ).first()
    if not target_org:
        raise HTTPException(status_code=404, detail="Target team not found")

    # Find the skill
    skill = db.query(models.Skill).filter(
        models.Skill.name == transfer.skill_name,
        models.Skill.org_id == source_org.id,
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found in source team")

    skill.org_id = target_org.id
    db.commit()

    return {
        "status": "transferred",
        "skill": transfer.skill_name,
        "from": name,
        "to": transfer.target_org,
    }
