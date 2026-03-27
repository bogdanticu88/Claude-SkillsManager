# SkillPM Registry - Frontend Static File Server
# Author: Bogdan Ticu
# License: MIT

import os
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["frontend"])

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web-frontend")


@router.get("/app", response_class=HTMLResponse)
@router.get("/app/", response_class=HTMLResponse)
def serve_frontend():
    """Serve the main frontend page."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>SkillPM Registry</h1><p>Frontend not found.</p>")


@router.get("/app/static/{filename}")
def serve_static(filename: str):
    """Serve static assets (CSS, JS)."""
    file_path = os.path.join(FRONTEND_DIR, "static", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse("Not found", status_code=404)
