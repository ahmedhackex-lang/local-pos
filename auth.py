"""
Authentication and authorization utilities
JWT token management, password hashing, role-based access control
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import TokenData
from config import settings, constants


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# OAuth2 scheme (extracts token from cookie or Authorization header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ===== PASSWORD UTILITIES =====

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ===== JWT TOKEN UTILITIES =====

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload dictionary (must contain user_id, username, role)
        expires_delta: Token expiration time (default: 8 hours)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData object with user information
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if user_id is None or username is None or role is None:
            raise credentials_exception
        
        return TokenData(user_id=user_id, username=username, role=role)
    
    except JWTError:
        raise credentials_exception


# ===== AUTHENTICATION DEPENDENCIES =====

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Dependency for protected routes
    """
    token_data = decode_access_token(token)
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Alias for get_current_user (for clarity)"""
    return current_user


# ===== ROLE-BASED ACCESS CONTROL =====

class RoleChecker:
    """Dependency class for role-based access control"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user


# Pre-defined role dependencies
require_cashier = RoleChecker([constants.ROLE_CASHIER, constants.ROLE_ADMIN, constants.ROLE_OWNER, constants.ROLE_DEVELOPER])
require_admin = RoleChecker([constants.ROLE_ADMIN, constants.ROLE_OWNER, constants.ROLE_DEVELOPER])
require_owner = RoleChecker([constants.ROLE_OWNER, constants.ROLE_DEVELOPER])
require_developer = RoleChecker([constants.ROLE_DEVELOPER])


# ===== USER AUTHENTICATION =====

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate user with username and password
    
    Args:
        db: Database session
        username: User's username
        password: User's plain text password
    
    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    if not user.is_active:
        return None
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


# ===== INITIAL USER CREATION =====

def create_default_users(db: Session):
    """
    Create default users if they don't exist
    Called during application startup
    """
    default_users = [
        {
            "username": "admin",
            "password": "admin123",
            "full_name": "System Administrator",
            "role": constants.ROLE_ADMIN
        },
        {
            "username": "cashier",
            "password": "cashier123",
            "full_name": "Cashier",
            "role": constants.ROLE_CASHIER
        },
        {
            "username": "owner",
            "password": "owner123",
            "full_name": "Store Owner",
            "role": constants.ROLE_OWNER
        },
        {
            "username": "developer",
            "password": "dev123",
            "full_name": "System Developer",
            "role": constants.ROLE_DEVELOPER
        }
    ]
    
    for user_data in default_users:
        existing_user = db.query(User).filter(
            User.username == user_data["username"]
        ).first()
        
        if not existing_user:
            new_user = User(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True
            )
            db.add(new_user)
    
    db.commit()
    print("✓ Default users created")