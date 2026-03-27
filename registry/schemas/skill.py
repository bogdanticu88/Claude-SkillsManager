# SkillPM Registry - Skill Schemas
# Author: Bogdan Ticu
# License: MIT

from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import List, Optional, Dict, Any
import datetime
import re


class SkillMetadataIn(BaseModel):
    tags: List[str] = Field(default_factory=list, max_length=20)
    language: str = "python"
    target_llms: List[str] = Field(default_factory=list)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    min_skillpm_version: Optional[str] = None


class SkillMetadataOut(BaseModel):
    tags: List[str] = []
    language: str = "unknown"
    target_llms: List[str] = []
    capabilities: Dict[str, Any] = {}
    dependencies: Dict[str, Any] = {}
    min_skillpm_version: Optional[str] = None

    class Config:
        from_attributes = True


class SkillCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Skill name (lowercase, numbers, hyphens only)"
    )
    version: str = Field(
        ...,
        max_length=32,
        description="Version in semver format (X.Y.Z)"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Short description of skill"
    )
    long_description: Optional[str] = Field(None, max_length=5000)
    license: str = Field(
        default="MIT",
        max_length=64,
        description="SPDX license identifier"
    )
    repository_url: Optional[HttpUrl] = Field(None, description="GitHub repository URL")
    homepage_url: Optional[HttpUrl] = Field(None, description="Project homepage")
    entry_point: Optional[str] = Field(None, max_length=256)
    language: str = Field(
        ...,
        description="Implementation language"
    )
    author_username: str
    metadata: SkillMetadataIn = Field(default_factory=SkillMetadataIn)
    org_name: Optional[str] = None
    is_private: bool = False
    signature: Optional[str] = Field(None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", v):
            raise ValueError(
                "Name must start with lowercase letter or digit and contain only lowercase letters, digits, and hyphens"
            )
        reserved = {"admin", "api", "root", "system", "registry", "skillpm"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved skill name")
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        if not re.match(r"^\d+\.\d+\.\d+(-[a-z0-9]+)?$", v):
            raise ValueError(
                "Version must follow semver format (e.g., 1.0.0 or 1.0.0-beta)"
            )
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        allowed = {"python", "javascript", "go", "typescript"}
        if v.lower() not in allowed:
            raise ValueError(
                f"Language must be one of: {', '.join(allowed)}"
            )
        return v.lower()

    @field_validator("license")
    @classmethod
    def validate_license(cls, v):
        common = {"MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC"}
        if v not in common:
            # Allow custom but warn about it
            pass
        return v

    class Config:
        extra = "forbid"  # Reject unknown fields


class SkillUpdate(BaseModel):
    version: Optional[str] = None
    description: Optional[str] = None
    long_description: Optional[str] = None
    license: Optional[str] = None
    repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    entry_point: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[SkillMetadataIn] = None
    deprecated: Optional[bool] = None
    deprecated_message: Optional[str] = None
    signature: Optional[str] = None


class SkillResponse(BaseModel):
    id: int
    name: str
    version: str
    description: Optional[str] = None
    long_description: Optional[str] = None
    license: Optional[str] = None
    repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    entry_point: Optional[str] = None
    language: Optional[str] = None
    author_username: str
    metadata: SkillMetadataOut
    download_count: int = 0
    avg_rating: float = 0.0
    review_count: int = 0
    is_private: bool = False
    deprecated: bool = False
    org_name: Optional[str] = None
    published_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    skills: List[SkillResponse]
    total: int
    page: int
    per_page: int


class VersionCreate(BaseModel):
    version: str
    changelog: Optional[str] = None
    manifest_snapshot: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None


class VersionResponse(BaseModel):
    id: int
    version: str
    changelog: Optional[str] = None
    yanked: bool = False
    published_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
