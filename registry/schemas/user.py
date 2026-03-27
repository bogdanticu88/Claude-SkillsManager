# SkillPM Registry - User Schemas
# Author: Bogdan Ticu
# License: MIT

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List
import datetime
import re


class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Username (alphanumeric, underscore, hyphen only)"
    )
    email: Optional[EmailStr] = Field(None, description="Valid email address")
    display_name: Optional[str] = Field(None, max_length=256)
    bio: Optional[str] = Field(None, max_length=2000)
    website: Optional[str] = Field(None, max_length=512)
    gpg_public_key: Optional[str] = Field(None, max_length=10000)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "Username must contain only lowercase letters, numbers, underscores, and hyphens"
            )
        reserved = {"admin", "api", "root", "system", "registry", "skillpm"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved username")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v):
        if v:
            return v.lower()
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Website must start with http:// or https://")
        return v

    class Config:
        extra = "forbid"  # Reject unknown fields


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    gpg_public_key: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    verified: bool = False
    skill_count: int = 0
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    email: Optional[str] = None
    gpg_public_key: Optional[str] = None
    total_downloads: int = 0
    avg_rating: float = 0.0


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=256)
    body: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    skill_name: str = ""
    username: str = ""
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
