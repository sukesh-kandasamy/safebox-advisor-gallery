
"""
Public video gallery endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from datetime import datetime

from db.database import DATABASE_PATH

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.now()


@router.get("/", response_class=HTMLResponse, name="home")
async def home_page(request: Request):
    """Home page - Shows first 6 videos."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get only first 6 videos for homepage (ordered first to last)
        cursor = await db.execute("SELECT * FROM videos ORDER BY order_index ASC LIMIT 6")
        videos = await cursor.fetchall()
        
        # Get total count for "View All" button
        cursor = await db.execute("SELECT COUNT(*) as count FROM videos")
        total_count = (await cursor.fetchone())["count"]
        
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "videos": videos,
        "total_videos": total_count,
        "show_footer": True,
        "title": "Safebox Video Gallery"
    })


@router.get("/videos", response_class=HTMLResponse, name="all_videos")
async def all_videos_page(request: Request):
    """All videos page with step-by-step guide."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Initial load limit to 6
        cursor = await db.execute("SELECT * FROM videos ORDER BY order_index ASC LIMIT 6")
        videos = await cursor.fetchall()
        
    return templates.TemplateResponse("all_videos.html", {
        "request": request, 
        "videos": videos,
        "show_footer": False,
        "title": "All Videos - Safebox"
    })


@router.get("/videos/partial", response_class=HTMLResponse)
async def videos_partial(request: Request, skip: int = 0, limit: int = 6):
    """Fetch partial video list for load more functionality."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM videos ORDER BY order_index ASC LIMIT ? OFFSET ?", 
            (limit, skip)
        )
        videos = await cursor.fetchall()
        
    return templates.TemplateResponse("components/video_card_list.html", {
        "request": request,
        "videos": videos
    })



@router.get("/guide", response_class=HTMLResponse, name="docs")
async def docs_page(request: Request):
    """Documentation page."""
    return templates.TemplateResponse("docs.html", {"request": request})

@router.get("/video/{id}", response_class=HTMLResponse, name="video_detail")
async def video_page(request: Request, id: str):
    """Video player page."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM videos WHERE id = ?", (id,))
        video = await cursor.fetchone()
        
        if not video:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
        # Fetch next video if linked
        next_video = None
        if video["next_video_id"]:
            cursor = await db.execute(
                "SELECT id, title, youtube_id FROM videos WHERE id = ?", 
                (video["next_video_id"],)
            )
            next_video = await cursor.fetchone()
        
    return templates.TemplateResponse("video.html", {
        "request": request, 
        "video": video,
        "next_video": next_video,
        "show_footer": False,
        "title": video["title"]
    })
