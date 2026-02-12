"""
Authentication router for admin login/logout and settings
Uses HTTP-only cookie-based authentication with 10-day expiry
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite

from db.database import get_db
from schemas.auth import (
    LoginRequest, TokenResponse, AdminResponse, 
    ProfileUpdate, PasswordChange
)
from utils.security import verify_password, create_access_token, decode_token, get_password_hash
from config import get_settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()

COOKIE_NAME = "admin_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 10  # 10 days in seconds


async def get_current_admin(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Get current authenticated admin from cookie token."""
    token = request.cookies.get(COOKIE_NAME)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    cursor = await db.execute(
        "SELECT * FROM admins WHERE email = ?",
        (email,)
    )
    admin = await cursor.fetchone()
    
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )
    
    return dict(admin)


class UnauthenticatedPageException(Exception):
    """Exception raised when a user is not authenticated for a page view."""
    pass


async def get_current_admin_html(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """
    Get current authenticated admin from cookie token for HTML pages.
    Raises UnauthenticatedPageException instead of HTTPException on failure,
    triggering a redirect to the login page.
    """
    try:
        return await get_current_admin(request, db)
    except HTTPException:
        raise UnauthenticatedPageException()


@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Admin login endpoint - sets HTTP-only cookie."""
    cursor = await db.execute(
        "SELECT id, email, password_hash, name FROM admins WHERE email = ?",
        (login_data.email,)
    )
    admin = await cursor.fetchone()
    
    if not admin or not verify_password(login_data.password, admin["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(
        data={"sub": admin["email"], "admin_id": admin["id"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    
    return {"message": "Login successful", "redirect": "/admin/dashboard"}


@router.get("/me", response_model=AdminResponse)
async def get_me(current_admin: dict = Depends(get_current_admin)):
    """Get current admin info."""
    return AdminResponse(
        id=current_admin["id"],
        email=current_admin["email"],
        name=current_admin["name"],
        profile_image_url=current_admin.get("profile_image_url"),
        created_at=current_admin["created_at"],
        updated_at=current_admin.get("updated_at")
    )


@router.get("/check")
async def check_auth(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Check if user is authenticated (for redirect logic)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return {"authenticated": False}
    
    payload = decode_token(token)
    if payload is None:
        return {"authenticated": False}
    
    email = payload.get("sub")
    if email is None:
        return {"authenticated": False}
    
    cursor = await db.execute("SELECT id, name FROM admins WHERE email = ?", (email,))
    admin = await cursor.fetchone()
    
    if admin is None:
        return {"authenticated": False}
    
    return {"authenticated": True, "name": admin["name"]}


@router.put("/profile", response_model=AdminResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Update admin profile (name, profile image)."""
    updates = []
    params = []
    
    if profile_data.name is not None:
        updates.append("name = ?")
        params.append(profile_data.name)
    
    if profile_data.profile_image_url is not None:
        updates.append("profile_image_url = ?")
        params.append(profile_data.profile_image_url)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(current_admin["id"])
    
    await db.execute(
        f"UPDATE admins SET {', '.join(updates)} WHERE id = ?",
        params
    )
    await db.commit()
    
    cursor = await db.execute(
        "SELECT id, email, name, profile_image_url, created_at, updated_at FROM admins WHERE id = ?",
        (current_admin["id"],)
    )
    admin = await cursor.fetchone()
    return AdminResponse(**dict(admin))


@router.put("/password")
async def change_password(
    password_data: PasswordChange,
    current_admin: dict = Depends(get_current_admin),
    db: aiosqlite.Connection = Depends(get_db)
):
    """Change admin password."""
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    cursor = await db.execute(
        "SELECT password_hash FROM admins WHERE id = ?",
        (current_admin["id"],)
    )
    admin = await cursor.fetchone()
    
    if not verify_password(password_data.current_password, admin["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    new_hash = get_password_hash(password_data.new_password)
    await db.execute(
        "UPDATE admins SET password_hash = ?, updated_at = ? WHERE id = ?",
        (new_hash, datetime.now().isoformat(), current_admin["id"])
    )
    await db.commit()
    
    return {"message": "Password updated successfully"}





@router.post("/logout")
async def logout(response: Response):
    """Logout endpoint - clears the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out successfully", "redirect": "/admin/login"}
