"""Authentication API endpoints."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import (
    get_user_by_email,
    get_user_by_username,
    create_user,
    authenticate_user,
    create_user_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = create_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    access_token = create_user_token(user)
    return Token(access_token=access_token)


@router.post("/guest", response_model=Token)
def guest_login(db: Session = Depends(get_db)):
    """Create a guest account and login."""
    # Generate unique guest credentials
    guest_id = uuid.uuid4().hex[:8]
    guest_email = f"guest_{guest_id}@example.com"
    guest_username = f"Guest_{guest_id}"
    guest_password = f"guest_{guest_id}_pass"
    
    # Create guest user
    user_data = UserCreate(
        email=guest_email,
        username=guest_username,
        password=guest_password
    )
    user = create_user(db, user_data)
    
    # Generate token
    access_token = create_user_token(user)
    return Token(access_token=access_token)
