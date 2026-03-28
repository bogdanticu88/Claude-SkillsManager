# SkillPM Registry - Main Application
# Author: Bogdan Ticu
# License: MIT
#
# The central registry API for SkillPM. Provides skill discovery,
# publishing, author management, reviews, analytics, and moderation.

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
import time
from datetime import datetime

from .db import connection
from .routers import skills, search, authors, reviews, analytics, moderation, organizations, frontend, dashboard, compatibility, teams
from .middleware.rate_limit import RateLimitMiddleware

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    logger.info("Starting SkillPM Registry")
    connection.init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down SkillPM Registry")


app = FastAPI(
    title="SkillPM Registry API",
    description="Package registry for Claude/LLM skills",
    version="1.0.0",
    lifespan=lifespan,
)

# Request size limit middleware
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", "1000000"))  # 1MB default

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Enforce maximum request body size to prevent abuse."""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "code": "INVALID_INPUT",
                            "message": "Request too large",
                            "detail": f"Maximum request size is {MAX_BODY_SIZE} bytes"
                        }
                    )
            except (ValueError, TypeError):
                pass
    return await call_next(request)


# Request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", str(int(time.time() * 1000)))

    # Log request
    logger.info(
        f"[{request_id}] {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - Error: {str(e)}"
        )
        raise


# CORS configuration - environment-based
allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8080"  # Local dev defaults
).split(",")

if os.getenv("ENV") == "production" and "http://localhost" in allowed_origins:
    logger.warning("CORS not properly configured for production. Set CORS_ORIGINS env var.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    max_age=600,
)

logger.info(f"CORS enabled for origins: {', '.join(allowed_origins)}")

# Rate limiting - per-user (configurable via environment)
rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "200"))
rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
app.add_middleware(RateLimitMiddleware, requests_per_window=rate_limit_requests, window_seconds=rate_limit_window)

# Register routers
app.include_router(skills.router)
app.include_router(search.router)
app.include_router(authors.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(moderation.router)
app.include_router(organizations.router)
app.include_router(frontend.router)
app.include_router(dashboard.router)
app.include_router(compatibility.router)
app.include_router(teams.router)


@app.get("/")
async def root():
    return {
        "service": "SkillPM Registry",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/v1/cache/stats")
async def cache_stats():
    from .services.cache import cache
    return cache.stats()


@app.post("/api/v1/cache/clear")
async def cache_clear():
    from .services.cache import cache
    cache.clear()
    return {"status": "cache cleared"}
