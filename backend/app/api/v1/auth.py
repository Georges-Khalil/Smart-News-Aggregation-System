from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import Token, UserCreate, User, ResponseBase
from app.services.auth import AuthService, oauth2_scheme

'''
Authentication API
-----------------

This module provides endpoints for user authentication, including:
- User registration
- User login with JWT token
- Getting current user information

All authentication is handled using OAuth2 password flow with JWT tokens.
'''

router = APIRouter()

async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = AuthService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    
    Endpoint: POST /api/v1/auth/login
    
    Form Parameters:
    - username: User's email address
    - password: User's password
    
    Returns:
    - 200 OK: JWT access token for authenticating future requests
      {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
      }
    
    Error Responses:
    - 401 Unauthorized: Incorrect email or password
    
    Notes:
    - The access token expires after the time set in settings (default 30 minutes)
    - The token must be included in the Authorization header for subsequent requests
    """
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=ResponseBase)
async def register_user(
    user_data: UserCreate, db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user
    
    Endpoint: POST /api/v1/auth/register
    
    Request Body:
    {
        "email": "user@example.com",
        "full_name": "John Doe",
        "password": "securepassword123",
        "notification_enabled": true,
        "urgency_threshold": 7
    }
    
    Fields:
    - email: Required - User's email address (must be valid format)
    - full_name: Optional - User's full name
    - password: Required - User's password
    - notification_enabled: Optional - Whether notifications are enabled (default: true)
    - urgency_threshold: Optional - Threshold for article urgency (1-10, default: 7)
    
    Returns:
    - 200 OK: User created successfully
      {
        "success": true,
        "message": "User registered successfully"
      }
    
    Error Responses:
    - 400 Bad Request: Email already registered
    - 422 Unprocessable Entity: Invalid input data
    """
    # Check if user exists
    user = AuthService.get_user_by_email(db, user_data.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user
    user = AuthService.create_user(db, user_data)
    
    return {"success": True, "message": "User registered successfully"}

@router.get("/me", response_model=User)
async def get_user_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user information
    
    Endpoint: GET /api/v1/auth/me
    
    Headers:
    - Authorization: Bearer {access_token} (required)
    
    Returns:
    - 200 OK: Current user information
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "email": "user@example.com",
        "full_name": "John Doe",
        "notification_enabled": true,
        "urgency_threshold": 7,
        "is_active": true,
        "is_superuser": false,
        "created_at": "2025-04-26T10:00:00.000Z",
        "updated_at": "2025-04-26T10:00:00.000Z"
      }
    
    Error Responses:
    - 401 Unauthorized: Invalid or expired token
    """
    return current_user