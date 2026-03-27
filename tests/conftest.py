# SkillPM Registry - Pytest Configuration
# Author: Bogdan Ticu
# License: MIT
#
# Shared fixtures and configuration for all tests

import pytest
import os
import sys

# Add registry to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force SQLite to use file-based database for tests BEFORE any imports
# (in-memory has concurrency issues across connections)
test_db_path = "/tmp/skillpm_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
# Disable rate limiting for tests
os.environ["RATE_LIMIT_REQUESTS"] = "100000"
os.environ["RATE_LIMIT_WINDOW"] = "60"
# Increase request size limit for tests
os.environ["MAX_BODY_SIZE"] = "10000000"

# Now import and set up the database
from registry.db.connection import engine
from registry.db.models import Base

# Clean up old test database if it exists
import pathlib
db_file = pathlib.Path(test_db_path)
if db_file.exists():
    db_file.unlink()

# Create all tables immediately when conftest is loaded
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "db_url": "sqlite:///:memory:",  # Use in-memory database for tests
        "api_url": "http://localhost:8000"
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
