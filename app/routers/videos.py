
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from datetime import datetime
from db.database import DATABASE_PATH
from config import get_settings
from routers.auth import get_current_admin, get_current_admin_html

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["now"] = datetime.now()
settings = get_settings()

def get_youtube_id(url: str) -> str:
    """Extract YouTube ID from URL."""
    import re
    # Patterns for: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@router.get("/admin/dashboard", response_class=HTMLResponse, name="admin_dashboard")
async def list_videos(request: Request, user: dict = Depends(get_current_admin_html)):
    """List videos in admin dashboard."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM videos ORDER BY order_index ASC")
        videos = await cursor.fetchall()
        
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "videos": videos,
        "user": user
    })

@router.get("/admin/videos/new", response_class=HTMLResponse)
async def new_video_form(request: Request, user: dict = Depends(get_current_admin_html)):
    """Show add video form."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, title FROM videos ORDER BY created_at DESC")
        all_videos = await cursor.fetchall()
    
    return templates.TemplateResponse("admin/video_form.html", {
        "request": request, 
        "user": user,
        "all_videos": all_videos
    })

@router.post("/admin/videos")
async def create_video(
    title: str = Form(...),
    description: str = Form(""),
    video_link: str = Form(...),
    next_video_id: str = Form(None),
    user: dict = Depends(get_current_admin_html)
):
    """Create a new video."""
    import uuid
    id = str(uuid.uuid4())
    youtube_id = get_youtube_id(video_link)
    
    if not youtube_id:
        return RedirectResponse(url="/admin/videos/new?error=Invalid YouTube URL", status_code=303)

    # Handle empty string as None
    next_video_id = next_video_id if next_video_id else None

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get next order_index
        cursor = await db.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM videos")
        next_order_index = (await cursor.fetchone())[0]
        
        await db.execute(
            """INSERT INTO videos (id, title, description, video_link, youtube_id, next_video_id, order_index) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id, title, description, video_link, youtube_id, next_video_id, next_order_index)
        )
        await db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.get("/admin/videos/{id}/edit", response_class=HTMLResponse)
async def edit_video_form(request: Request, id: str, user: dict = Depends(get_current_admin_html)):
    """Show edit video form."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM videos WHERE id = ?", (id,))
        video = await cursor.fetchone()
        
        # Get all videos for the dropdown (excluding current)
        cursor = await db.execute("SELECT id, title FROM videos ORDER BY created_at DESC")
        all_videos = await cursor.fetchall()
        
    if not video:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
        
    return templates.TemplateResponse("admin/video_form.html", {
        "request": request, 
        "video": video,
        "user": user,
        "all_videos": all_videos
    })

@router.post("/admin/videos/{id}")
async def update_video(
    id: str,
    title: str = Form(...),
    description: str = Form(""),
    video_link: str = Form(...),
    next_video_id: str = Form(None),
    user: dict = Depends(get_current_admin_html)
):
    """Update a video."""
    youtube_id = get_youtube_id(video_link)
    
    # Handle empty string as None
    next_video_id = next_video_id if next_video_id else None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE videos 
               SET title = ?, description = ?, video_link = ?, youtube_id = ?, next_video_id = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (title, description, video_link, youtube_id, next_video_id, id)
        )
        await db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/admin/videos/{id}/delete")
async def delete_video(id: str, user: dict = Depends(get_current_admin_html)):
    """Delete a video and reindex remaining videos."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get the order_index of the video being deleted
        cursor = await db.execute("SELECT order_index FROM videos WHERE id = ?", (id,))
        result = await cursor.fetchone()
        
        if result:
            deleted_index = result[0]
            
            # Delete the video
            await db.execute("DELETE FROM videos WHERE id = ?", (id,))
            
            # Decrement order_index for all videos after the deleted one
            await db.execute(
                "UPDATE videos SET order_index = order_index - 1 WHERE order_index > ?",
                (deleted_index,)
            )
            await db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)
