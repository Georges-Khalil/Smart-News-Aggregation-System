import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, ForeignKey, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from ..core.database import Base

# Association table for many-to-many relationship between users and articles
user_article_interactions = Table(
    'user_article_interactions',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('article_id', UUID(as_uuid=True), ForeignKey('articles.id')),
    Column('liked', Boolean, default=False),
    Column('read', Boolean, default=False),
    Column('read_time', Integer, default=0),  # Time spent reading in seconds
    Column('created_at', DateTime, default=datetime.utcnow)
)

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, index=True)
    link = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)  # Added description field
    content = Column(String)
    pub_date = Column(DateTime, index=True)
    image = Column(String, nullable=True)
    source = Column(String, index=True)
    urgency_score = Column(Integer, index=True)
    embedding = Column(ARRAY(Float))  # Store embedding as an array of floats
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", secondary=user_article_interactions, back_populates="articles")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User preferences
    preference_embedding = Column(ARRAY(Float), nullable=True)  # Main preference vector
    preference_embeddings = Column(JSON, nullable=True)  # Multiple interest vectors stored as JSON
    notification_enabled = Column(Boolean, default=True)
    urgency_threshold = Column(Integer, default=7)  # Articles above this urgency score will trigger notifications
    
    # Firebase token for push notifications
    firebase_token = Column(String, nullable=True)
    
    # New column for storing device tokens for push notifications
    device_tokens = Column(JSON, nullable=True, default=list)  # List of device tokens for push notifications
    
    # Relationships
    articles = relationship("Article", secondary=user_article_interactions, back_populates="users")