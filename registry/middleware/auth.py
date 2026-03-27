# SkillPM Registry - Authentication Middleware
# Author: Bogdan Ticu
# License: MIT
#
# API key authentication using Argon2 for secure hashing.
# Users get an API key when they register. The key is sent as a Bearer token.
# For public endpoints, auth is optional. For write endpoints, auth is required.

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

from ..db import connection, models
from ..schemas.errors import unauthorized_error, forbidden_error

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
ph = PasswordHasher()


def hash_api_key(key: str) -> str:
    """Hash an API key using Argon2 (resistant to GPU attacks)."""
    try:
        return ph.hash(key)
    except Exception as e:
        logger.error(f"Failed to hash API key: {e}")
        raise RuntimeError("Failed to process API key")


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify API key against hash using constant-time comparison."""
    try:
        ph.verify(key_hash, key)
        return True
    except VerifyMismatchError:
        return False
    except InvalidHash:
        logger.warning("Invalid hash format stored")
        return False
    except Exception as e:
        logger.error(f"Failed to verify API key: {e}")
        return False


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(connection.get_db),
) -> Optional[models.User]:
    """Returns the authenticated user or None if no valid token is provided."""
    if credentials is None:
        return None

    # Validate key format
    if not credentials.credentials.startswith("skpm_"):
        logger.warning("Attempted auth with invalid key format")
        return None

    try:
        # Use indexed query on api_key_hash prefix for better performance
        user = db.query(models.User).filter(
            models.User.api_key_hash.is_not(None)
        ).first()
        
        # For now, iterate through users with keys (limited set)
        # In production, consider storing key prefix for indexed lookup
        users_with_keys = db.query(models.User).filter(
            models.User.api_key_hash.is_not(None)
        ).all()
        
        for user in users_with_keys:
            if verify_api_key(credentials.credentials, user.api_key_hash):
                return user
        return None
    except Exception as e:
        logger.error(f"Error during user lookup: {e}")
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(connection.get_db),
) -> models.User:
    """Returns the authenticated user or raises 401."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail=unauthorized_error(
                detail="Include 'Authorization: Bearer <API_KEY>' header"
            )
        )

    # Validate key format
    if not credentials.credentials.startswith("skpm_"):
        logger.warning(f"Invalid API key format from {credentials.credentials[:10]}...")
        raise HTTPException(
            status_code=400,
            detail=unauthorized_error(
                detail="API keys start with 'skpm_'. Check your key format."
            )
        )

    try:
        # Use indexed query filter for better performance
        users_with_keys = db.query(models.User).filter(
            models.User.api_key_hash.is_not(None)
        ).all()
        
        for user in users_with_keys:
            if verify_api_key(credentials.credentials, user.api_key_hash):
                return user

        logger.warning("Failed login attempt with invalid API key")
        raise HTTPException(
            status_code=401,
            detail=unauthorized_error(
                detail="API key not found or invalid"
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": "SERVER_ERROR", "message": "Authentication service error"}
        )


def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """Requires the current user to be an admin."""
    if not user.is_admin:
        logger.warning(f"Non-admin user {user.username} attempted admin operation")
        raise HTTPException(
            status_code=403,
            detail=forbidden_error("admin endpoint")
        )
    return user
