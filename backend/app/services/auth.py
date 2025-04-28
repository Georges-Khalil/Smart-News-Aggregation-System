from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from passlib.context import CryptContext
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import uuid4

from ..core.config import settings
from ..models.models import User
from ..models.schemas import UserCreate, UserUpdate

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class AuthService:
    """Service to handle user authentication and management."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a password hash."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        # Set expiration time
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        
        # Encode JWT
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = cls.get_user_by_email(db, email)
        if not user or not cls.verify_password(password, user.hashed_password):
            return None
        return user
    
    @classmethod
    def create_user(cls, db: Session, user_data: UserCreate) -> User:
        """Create a new user."""
        # Hash the password
        hashed_password = cls.get_password_hash(user_data.password)
        
        # Create the user
        db_user = User(
            id=uuid4(),
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            notification_enabled=user_data.notification_enabled,
            urgency_threshold=user_data.urgency_threshold
        )
        
        # Add to database and commit
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @classmethod
    def update_user(cls, db: Session, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        # Get the user
        user = cls.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Update user data
        user_data_dict = user_data.dict(exclude_unset=True)
        
        # Hash password if it's being updated
        if "password" in user_data_dict:
            user_data_dict["hashed_password"] = cls.get_password_hash(user_data_dict.pop("password"))
        
        # Update user attributes
        for key, value in user_data_dict.items():
            setattr(user, key, value)
        
        # Update the database
        db.commit()
        db.refresh(user)
        
        return user