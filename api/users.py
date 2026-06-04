"""
User management API endpoints
CRUD operations for user accounts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User
from schemas import UserCreate, UserUpdate, UserResponse
from auth import require_admin, hash_password, get_current_user
from config import constants

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get all users
    
    Requires admin role
    """
    users = db.query(User).all()
    return [UserResponse.from_orm(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.from_orm(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Create new user
    
    Requires admin role
    """
    # Check if username exists
    existing = db.query(User).filter(
        User.username == user_data.username
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Username '{user_data.username}' already exists"
        )
    
    # Create user
    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        created_by=current_user.id
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update user
    
    Requires admin role
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    # Handle password separately
    if 'password' in update_data:
        user.password_hash = hash_password(update_data.pop('password'))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Deactivate user (soft delete)
    
    Requires admin role
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot deactivate self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}