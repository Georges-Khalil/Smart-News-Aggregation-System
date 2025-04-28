from typing import List, Optional, Any, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator

# Base response model
class ResponseBase(BaseModel):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None

# User models
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    notification_enabled: bool = True
    urgency_threshold: int = 7

class UserCreate(UserBase):
    password: str
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    notification_enabled: Optional[bool] = None
    urgency_threshold: Optional[int] = None
    firebase_token: Optional[str] = None

class User(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        orm_mode = True  # Keep for backward compatibility

# Token model
class Token(BaseModel):
    access_token: str
    token_type: str

# Article models
class ArticleBase(BaseModel):
    title: str
    link: str
    description: Optional[str] = None  # Added description field
    content: str
    pub_date: datetime
    image: Optional[str] = None
    source: str
    urgency_score: int

class ArticleCreate(ArticleBase):
    embedding: List[float]

class Article(ArticleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        orm_mode = True  # Keep for backward compatibility

# User-article interaction
class UserArticleInteraction(BaseModel):
    article_id: UUID
    liked: Optional[bool] = None
    read: Optional[bool] = None
    read_time: Optional[int] = None  # Time spent reading in seconds

# Paginated response
class PagedResponse(ResponseBase):
    total: int
    page: int
    page_size: int
    total_pages: int