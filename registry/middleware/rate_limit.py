# SkillPM Registry - Rate Limiting Middleware
# Author: Bogdan Ticu
# License: MIT
#
# Per-user rate limiting using sliding window algorithm.
# Each user/IP gets their own quota to prevent one bad actor from DoSing others.
# For production, replace with Redis-backed rate limiting.

import time
import logging
import hashlib
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-user sliding window rate limiter.
    Tracks requests separately for authenticated users and IP addresses.
    Default: 200 requests per 60 seconds for API endpoints.
    """

    def __init__(self, app, requests_per_window: int = 200, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_log: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Only rate limit API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Get user identifier (API key or IP)
        user_id = self._get_user_id(request)
        now = time.time()

        # Remove requests outside the window
        cutoff = now - self.window_seconds
        self.request_log[user_id] = [
            t for t in self.request_log[user_id] if t > cutoff
        ]

        # Check if limit exceeded
        if len(self.request_log[user_id]) >= self.requests_per_window:
            logger.warning(
                f"Rate limit exceeded for {user_id}. "
                f"Requests: {len(self.request_log[user_id])}/{self.requests_per_window}"
            )
            from ..schemas.errors import rate_limited_error
            raise HTTPException(
                status_code=429,
                detail=rate_limited_error(retry_after=self.window_seconds)
            )

        # Record this request
        self.request_log[user_id].append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining = self.requests_per_window - len(self.request_log[user_id])
        reset_time = int(now + self.window_seconds)

        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_user_id(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.
        Prioritizes authenticated users, falls back to IP address.
        """
        # Check for API key in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
            if api_key.startswith("skpm_"):
                # Use hash of API key (don't expose full key)
                key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:20]
                return f"user:{key_hash}"

        # Fall back to client IP address
        if request.client:
            return f"ip:{request.client.host}"

        # Fallback (shouldn't happen)
        return "unknown"
