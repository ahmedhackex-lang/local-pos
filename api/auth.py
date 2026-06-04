"""
Authentication API endpoints
Login, logout, session validation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from auth import authenticate_user, create_access_token, get_current_user
from schemas import LoginRequest, LoginResponse, UserResponse
from config import settings

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    User login endpoint
    
    Returns JWT token in response and sets httponly cookie
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    # Set httponly cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        secure=not settings.DEBUG,  # HTTPS only in production
        samesite="lax"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }


@router.post("/logout")
async def logout(response: Response):
    """
    User logout endpoint
    
    Clears authentication cookie
    """
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user information
    
    Validates session and returns user details
    """
    return UserResponse.from_orm(current_user)


@router.post("/validate")
async def validate_session(current_user = Depends(get_current_user)):
    """
    Validate current session
    
    Returns 200 if session is valid, 401 otherwise
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }