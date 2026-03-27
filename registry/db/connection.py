# SkillPM Registry - Database Connection
# Author: Bogdan Ticu
# License: MIT

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
import os
from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./skillpm.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=os.getenv("SQL_DEBUG", "").lower() == "true",
)

# Enable WAL mode for SQLite for better concurrent reads
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
