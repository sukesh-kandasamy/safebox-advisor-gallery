"""
File upload router for images and videos
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os
import uuid
from datetime import datetime

from routers.auth import get_current_admin
from config import get_settings

router = APIRouter(prefix="/api", tags=["Uploads"])
settings = get_settings()

# Ensure upload directory exists
UPLOAD_PATH = os.path.join(os.path.dirname(__file__), "..", settings.UPLOAD_DIR)
os.makedirs(UPLOAD_PATH, exist_ok=True)


@router.post("/admin/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin)
):
    """Upload an image or video file."""
    # Validate file type
    content_type = file.content_type or ""
    
    if content_type in settings.ALLOWED_IMAGE_TYPES:
        file_type = "image"
    elif content_type in settings.ALLOWED_VIDEO_TYPES:
        file_type = "video"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: images ({', '.join(settings.ALLOWED_IMAGE_TYPES)}), videos ({', '.join(settings.ALLOWED_VIDEO_TYPES)})"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_PATH, unique_name)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return URL
    return {
        "url": f"/api/uploads/{unique_name}",
        "filename": file.filename,
        "type": file_type,
        "size": len(content)
    }


@router.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve an uploaded file."""
    file_path = os.path.join(UPLOAD_PATH, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)
