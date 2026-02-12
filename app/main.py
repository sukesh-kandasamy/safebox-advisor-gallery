"""
Safebox Blog - FastAPI Main Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
import os
import re
import aiosqlite
from datetime import datetime

from config import get_settings
from db.database import init_db, create_default_admin, DATABASE_PATH
from routers import auth, public, upload, utils, videos
from routers.auth import UnauthenticatedPageException

settings = get_settings()

# Setup templates
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    print("🚀 Starting Safebox Video Gallery API...")
    await init_db()
    await create_default_admin()
    print("✓ Database initialized")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    yield
    print("👋 Shutting down Safebox Video Gallery API...")


app = FastAPI(
    title="Safebox Video Gallery API",
    description="API for Safebox Video Gallery",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# 404 Handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(UnauthenticatedPageException)
async def unauthenticated_page_handler(request: Request, exc):
    return RedirectResponse(url="/admin/login", status_code=303)


# Include API routers
app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(public.router)
app.include_router(upload.router)
app.include_router(utils.router)


# Template routes are now handled in routers/public.py


# ============ Admin Template Routes ============

@app.get("/admin/login", response_class=HTMLResponse, name="admin_login")
async def admin_login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.get("/admin/dashboard")
async def admin_dashboard_redirect():
    """Redirect dashboard to videos."""
    return RedirectResponse(url="/admin/videos", status_code=303)


# Unused legacy routes removed (editor, questions)


@app.get("/admin/settings", response_class=HTMLResponse, name="admin_settings")
async def admin_settings_page(request: Request):
    """Admin settings page."""
    return templates.TemplateResponse("admin/settings.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
