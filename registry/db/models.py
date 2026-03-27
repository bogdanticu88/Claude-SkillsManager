# SkillPM Registry - Database Models
# Author: Bogdan Ticu
# License: MIT

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, JSON, Float, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True, nullable=True)
    username = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(256), nullable=True)
    display_name = Column(String(256), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    website = Column(String(512), nullable=True)
    gpg_public_key = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    api_key_hash = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    skills = relationship("Skill", back_populates="author")
    reviews = relationship("Review", back_populates="user")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), unique=True, index=True, nullable=False)
    version = Column(String(64), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    is_private = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    license = Column(String(64), nullable=True)
    repository_url = Column(String(512), nullable=True)
    homepage_url = Column(String(512), nullable=True)
    icon_url = Column(String(512), nullable=True)
    entry_point = Column(String(256), nullable=True)
    language = Column(String(64), nullable=True)
    signature = Column(Text, nullable=True)
    deprecated = Column(Boolean, default=False)
    deprecated_message = Column(Text, nullable=True)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    author = relationship("User", back_populates="skills")
    metadata_rel = relationship("SkillMetadata", back_populates="skill", uselist=False, cascade="all, delete-orphan")
    versions = relationship("SkillVersion", back_populates="skill", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="skill", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="skill", cascade="all, delete-orphan")


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    version = Column(String(64), nullable=False)
    changelog = Column(Text, nullable=True)
    manifest_snapshot = Column(JSON, nullable=True)
    signature = Column(Text, nullable=True)
    yanked = Column(Boolean, default=False)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

    skill = relationship("Skill", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_version"),
    )


class SkillMetadata(Base):
    __tablename__ = "skill_metadata"

    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)
    tags = Column(JSON, default=list)
    language = Column(String(64), nullable=True)
    target_llms = Column(JSON, default=list)
    capabilities = Column(JSON, default=dict)
    dependencies = Column(JSON, default=dict)
    min_skillpm_version = Column(String(32), nullable=True)

    skill = relationship("Skill", back_populates="metadata_rel")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, index=True, nullable=False)
    display_name = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(512), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(32), default="member")  # admin, member, readonly

    organization = relationship("Organization", back_populates="members")

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    version = Column(String(64), nullable=True)
    downloaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)

    skill = relationship("Skill", back_populates="downloads")

    __table_args__ = (
        Index("idx_download_skill_date", "skill_id", "downloaded_at"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(256), nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    skill = relationship("Skill", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint("skill_id", "user_id", name="uq_skill_review"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    reported_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    version = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)  # SUCCESS, FAILURE
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    llm_used = Column(String(64), nullable=True)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_exec_skill_date", "skill_id", "executed_at"),
    )


class InstallEvent(Base):
    __tablename__ = "install_events"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    version = Column(String(64), nullable=True)
    action = Column(String(32), nullable=False)  # install, uninstall, update
    ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_install_skill_date", "skill_id", "created_at"),
    )
