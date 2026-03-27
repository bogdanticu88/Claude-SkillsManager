# SkillPM Registry - Organizations Router
# Author: Bogdan Ticu
# License: MIT

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from ..db import connection, models
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


class OrgCreate(BaseModel):
    name: str
    display_name: str = None
    description: str = None
    website: str = None


class OrgUpdate(BaseModel):
    display_name: str = None
    description: str = None
    website: str = None
    avatar_url: str = None


class OrgResponse(BaseModel):
    id: int
    name: str
    display_name: str = None
    description: str = None
    website: str = None
    member_count: int = 0
    skill_count: int = 0

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    username: str
    role: str


class AddMember(BaseModel):
    username: str
    role: str = "member"


def build_org_response(db: Session, org: models.Organization) -> dict:
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
        "website": org.website,
        "member_count": member_count,
        "skill_count": skill_count,
    }


@router.post("/", response_model=OrgResponse, status_code=201)
def create_organization(
    org_in: OrgCreate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new organization. The creating user becomes admin."""
    existing = db.query(models.Organization).filter(
        models.Organization.name == org_in.name
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization name already taken")

    org = models.Organization(
        name=org_in.name,
        display_name=org_in.display_name or org_in.name,
        description=org_in.description,
        website=org_in.website,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Add creator as admin
    member = models.OrganizationMember(
        org_id=org.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(member)
    db.commit()

    return build_org_response(db, org)


@router.get("/{name}", response_model=OrgResponse)
def get_organization(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """Get organization details."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return build_org_response(db, org)


@router.put("/{name}", response_model=OrgResponse)
def update_organization(
    name: str,
    org_in: OrgUpdate,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update organization details. Admin only."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check admin
    member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role == "admin",
    ).first()
    if not member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    update_data = org_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    db.commit()
    db.refresh(org)

    return build_org_response(db, org)


@router.get("/{name}/members", response_model=List[MemberResponse])
def list_members(
    name: str,
    db: Session = Depends(connection.get_db),
):
    """List all members of an organization."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    members = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id
    ).all()

    results = []
    for m in members:
        user = db.query(models.User).filter(models.User.id == m.user_id).first()
        results.append({
            "username": user.username if user else "unknown",
            "role": m.role,
        })
    return results


@router.post("/{name}/members", status_code=201)
def add_member(
    name: str,
    member_in: AddMember,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a member to an organization. Admin only."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check admin
    admin_member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role == "admin",
    ).first()
    if not admin_member and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

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


@router.delete("/{name}/members/{username}", status_code=204)
def remove_member(
    name: str,
    username: str,
    db: Session = Depends(connection.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a member from an organization. Admin only."""
    org = db.query(models.Organization).filter(
        models.Organization.name == name
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    admin_member = db.query(models.OrganizationMember).filter(
        models.OrganizationMember.org_id == org.id,
        models.OrganizationMember.user_id == current_user.id,
        models.OrganizationMember.role == "admin",
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

    db.delete(member)
    db.commit()
    return None
