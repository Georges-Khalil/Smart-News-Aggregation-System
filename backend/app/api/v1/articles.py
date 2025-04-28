from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import Article, UserArticleInteraction, PagedResponse
from app.models.models import Article as ArticleModel, user_article_interactions
from app.services.recommendation import RecommendationService
from app.api.v1.auth import get_current_user
from app.models.schemas import User

'''
Articles API
-----------

This module provides endpoints for interacting with articles, including:
- Getting recent articles (optionally filtered by source)
- Getting personalized article recommendations
- Searching for articles
- Getting search suggestions
- Recording user interactions with articles (read, like)
- Getting a specific article by ID

These endpoints support building a full-featured news app with personalized recommendations.
'''

router = APIRouter()

@router.get("/recent", response_model=PagedResponse)
async def get_recent_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_ARTICLES_LIMIT, ge=1, le=50),
    source_filter: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Any:
    """
    Get recent articles with optional source filtering
    
    Endpoint: GET /api/v1/articles/recent
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of articles per page (default from settings, max: 50)
    - source_filter: Filter by source names, can specify multiple times
      Example: ?source_filter=CNN&source_filter=BBC
    
    Headers:
    - Authorization: Bearer {access_token} (optional)
    
    Returns:
    - 200 OK: Paginated list of recent articles
      {
        "success": true,
        "message": "Recent articles retrieved successfully",
        "data": [
          {
            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "title": "Breaking News: Important Event",
            "link": "https://example.com/news/article-1",
            "description": "Brief description of the article",
            "content": "Full content of the article...",
            "pub_date": "2025-04-26T09:00:00.000Z",
            "image": "https://example.com/images/article-1.jpg",
            "source": "CNN",
            "urgency_score": 8,
            "created_at": "2025-04-26T09:05:00.000Z",
            "updated_at": "2025-04-26T09:05:00.000Z"
          },
          ...more articles...
        ],
        "total": 100,
        "page": 1,
        "page_size": 10,
        "total_pages": 10
      }
    """
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Base query
    query = db.query(ArticleModel).order_by(ArticleModel.pub_date.desc())
    
    # Apply source filter if provided
    if source_filter:
        query = query.filter(ArticleModel.source.in_(source_filter))
    
    # Get paginated results
    articles = query.offset(offset).limit(page_size).all()
    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size
    
    # Convert SQLAlchemy models to dictionaries for proper serialization
    articles_dict = [article.__dict__ for article in articles]
    for article in articles_dict:
        if '_sa_instance_state' in article:
            article.pop('_sa_instance_state')
        # Convert UUID objects to strings
        if 'id' in article and hasattr(article['id'], 'hex'):
            article['id'] = str(article['id'])
    
    return {
        "success": True,
        "message": "Recent articles retrieved successfully",
        "data": articles_dict,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/feed", response_model=PagedResponse)
async def get_personalized_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_ARTICLES_LIMIT, ge=1, le=50),
    exploration_ratio: float = Query(0.2, ge=0.0, le=0.5, description="Proportion of results that should be exploration content (0.0-0.5)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get personalized news feed for the current user
    
    Endpoint: GET /api/v1/articles/feed
    
    This endpoint returns a personalized feed with a mix of:
    1. Articles matching the user's preferences (based on previously liked articles)
    2. Exploration content to help discover new topics
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of articles per page (default from settings, max: 50)
    - exploration_ratio: Proportion of results for exploration vs. personalization
      Range: 0.0-0.5, default: 0.2 (20% exploration, 80% personalized)
    
    Headers:
    - Authorization: Bearer {access_token} (required)
    
    Returns:
    - 200 OK: Paginated list of personalized articles
      {
        "success": true,
        "message": "Personalized feed retrieved successfully",
        "data": [
          {
            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "title": "Article matching user preferences",
            "link": "https://example.com/news/personalized-1",
            "description": "Brief description of the article",
            "content": "Full content of the article...",
            "pub_date": "2025-04-26T08:30:00.000Z",
            "image": "https://example.com/images/personalized-1.jpg",
            "source": "BBC",
            "urgency_score": 7,
            "created_at": "2025-04-26T08:35:00.000Z",
            "updated_at": "2025-04-26T08:35:00.000Z"
          },
          ...more articles...
        ],
        "total": 200,
        "page": 1,
        "page_size": 10,
        "total_pages": 20
      }
    
    Error Responses:
    - 401 Unauthorized: Authentication required
    
    Notes:
    - The algorithm uses multiple interest vectors derived from liked articles
    - Articles the user has already read are automatically excluded
    - The recommendation score combines similarity, recency, and urgency factors
    """
    # Calculate offset based on pagination
    offset = (page - 1) * page_size
    
    # Get integrated recommendations with multi-vector approach
    recommendation_service = RecommendationService(db)
    articles = recommendation_service.get_recommendations_with_multi_vectors(
        user_id=str(current_user.id),
        limit=page_size,
        offset=offset,
        exploration_ratio=exploration_ratio
    )
    
    # Convert SQLAlchemy models to dictionaries for proper serialization
    articles_dict = []
    for article in articles:
        if hasattr(article, '__dict__'):
            article_data = article.__dict__.copy()
            if '_sa_instance_state' in article_data:
                article_data.pop('_sa_instance_state')
            # Convert UUID objects to strings
            if 'id' in article_data and hasattr(article_data['id'], 'hex'):
                article_data['id'] = str(article_data['id'])
            articles_dict.append(article_data)
        else:
            # If already a dict, just append it
            articles_dict.append(article)
    
    # Get total count for pagination
    total_count = db.query(ArticleModel).count()
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        "success": True,
        "message": "Personalized feed retrieved successfully",
        "data": articles_dict,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/search", response_model=PagedResponse)
async def search_articles(
    query: str = Query(None, description="Search query for matching articles"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(settings.DEFAULT_ARTICLES_LIMIT, ge=1, le=50, description="Number of articles per page"),
    sources: Optional[List[str]] = Query(None, description="Filter by source names"),
    min_urgency: Optional[int] = Query(None, ge=1, le=10, description="Minimum urgency score"),
    sort_by: str = Query("relevance", description="Sort results by: relevance, recency, or urgency"),
    personalized: bool = Query(True, description="Use user preferences to personalize results"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Any:
    """
    Search for articles with advanced filtering options
    
    Endpoint: GET /api/v1/articles/search
    
    Query Parameters:
    - query: Search query string (required)
    - page: Page number (default: 1)
    - page_size: Number of articles per page (default from settings, max: 50)
    - sources: Filter by source names, can specify multiple times
      Example: ?sources=CNN&sources=BBC
    - min_urgency: Minimum urgency score (1-10)
    - sort_by: Sort results by one of: "relevance", "recency", or "urgency" (default: "relevance")
    - personalized: Whether to use user preferences for ranking (default: true)
    
    Headers:
    - Authorization: Bearer {access_token} (optional, required for personalized=true)
    
    Returns:
    - 200 OK: Paginated search results
      {
        "success": true,
        "message": "Search results retrieved successfully",
        "data": [
          {
            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "title": "Search result matching query",
            "link": "https://example.com/news/search-1",
            "description": "Brief description of the article",
            "content": "Full content of the article...",
            "pub_date": "2025-04-25T14:20:00.000Z",
            "image": "https://example.com/images/search-1.jpg",
            "source": "Al Jazeera",
            "urgency_score": 6,
            "created_at": "2025-04-25T14:25:00.000Z",
            "updated_at": "2025-04-25T14:25:00.000Z"
          },
          ...more articles...
        ],
        "total": 45,
        "page": 1,
        "page_size": 10,
        "total_pages": 5
      }
    
    Error Responses:
    - 401 Unauthorized: If personalized=true but not authenticated
    """
    from app.services.search import SearchService
    
    # Calculate offset based on pagination
    offset = (page - 1) * page_size
    
    # Initialize search service
    search_service = SearchService(db)
    
    # Get user ID for personalization if user is authenticated and personalization is enabled
    user_id = str(current_user.id) if current_user and personalized else None
    
    # Perform search
    search_results = search_service.search_articles(
        query=query,
        user_id=user_id,
        sources=sources,
        min_urgency=min_urgency,
        sort_by=sort_by,
        personalized=personalized,
        limit=page_size,
        offset=offset
    )
    
    # Convert SQLAlchemy models to dictionaries for proper serialization
    articles_dict = []
    for article in search_results["articles"]:
        if hasattr(article, '__dict__'):
            article_data = article.__dict__.copy()
            if '_sa_instance_state' in article_data:
                article_data.pop('_sa_instance_state')
            # Convert UUID objects to strings
            for key, value in article_data.items():
                if isinstance(value, UUID):
                    article_data[key] = str(value)
            articles_dict.append(article_data)
    
    # Calculate pagination
    total_count = search_results["total"]
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
    
    return {
        "success": True,
        "message": "Search results retrieved successfully",
        "data": articles_dict,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/search/suggestions", response_model=List[str])
async def get_search_suggestions(
    query: str = Query(..., min_length=2, description="Partial search query for suggestions"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of suggestions to return"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get search suggestions based on partial query
    
    Endpoint: GET /api/v1/articles/search/suggestions
    
    Used for implementing autocomplete in search functionality.
    
    Query Parameters:
    - query: Partial search query to get suggestions for (minimum 2 characters)
    - limit: Maximum number of suggestions to return (default: 5, max: 10)
    
    Returns:
    - 200 OK: List of search term suggestions
      [
        "suggested search term 1",
        "suggested search term 2",
        "suggested search term 3"
      ]
    """
    from app.services.search import SearchService
    
    search_service = SearchService(db)
    suggestions = search_service.get_search_suggestions(query, limit)
    
    return suggestions

# Notification endpoint removed - will be reimplemented in the future with push notification support

@router.post("/interaction", response_model=dict)
async def record_article_interaction(
    interaction: UserArticleInteraction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Record user interaction with an article
    
    Endpoint: POST /api/v1/articles/interaction
    
    This endpoint records user interactions (read, like, read time) with articles.
    These interactions are used to personalize recommendations.
    
    Headers:
    - Authorization: Bearer {access_token} (required)
    
    Request Body:
    {
      "article_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "liked": true,
      "read": true,
      "read_time": 120
    }
    
    Fields:
    - article_id: Required - ID of the article the user interacted with
    - liked: Optional - Whether the user liked the article
    - read: Optional - Whether the user read the article
    - read_time: Optional - Time spent reading in seconds
    
    Returns:
    - 200 OK: Interaction recorded successfully
      {
        "success": true,
        "message": "Interaction recorded successfully"
      }
    
    Error Responses:
    - 401 Unauthorized: Authentication required
    - 404 Not Found: Article not found
    
    Notes:
    - If the user has previously interacted with this article, the existing
      interaction record will be updated
    - When an article is liked, the user's preference embeddings are updated,
      affecting future personalized recommendations
    - The read status is used to filter out articles the user has already read
      from future recommendation results
    """
    # Check if article exists
    article = db.query(ArticleModel).filter(ArticleModel.id == interaction.article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    # Check if interaction already exists
    existing_interaction = db.query(user_article_interactions).filter(
        user_article_interactions.c.user_id == current_user.id,
        user_article_interactions.c.article_id == interaction.article_id
    ).first()
    
    if existing_interaction:
        # Update existing interaction
        update_stmt = user_article_interactions.update().where(
            (user_article_interactions.c.user_id == current_user.id) &
            (user_article_interactions.c.article_id == interaction.article_id)
        )
        
        update_values = {}
        if interaction.liked is not None:
            update_values["liked"] = interaction.liked
        if interaction.read is not None:
            update_values["read"] = interaction.read
        if interaction.read_time is not None:
            update_values["read_time"] = interaction.read_time
            
        db.execute(update_stmt.values(**update_values))
    else:
        # Create new interaction
        values = {
            "user_id": current_user.id,
            "article_id": interaction.article_id
        }
        
        if interaction.liked is not None:
            values["liked"] = interaction.liked
        if interaction.read is not None:
            values["read"] = interaction.read
        if interaction.read_time is not None:
            values["read_time"] = interaction.read_time
            
        db.execute(user_article_interactions.insert().values(**values))
    
    db.commit()
    
    # If user liked article, update their preference embedding
    if interaction.liked:
        try:
            recommendation_service = RecommendationService(db)
            # Convert user ID to string to avoid UUID object error
            user_id_str = str(current_user.id)
            
            # Use the new multi-vector time-weighted method instead of the simple average
            update_successful = recommendation_service.update_multi_vector_time_weighted_preferences(user_id_str)
            if not update_successful:
                print(f"[DEBUG] Preference update unsuccessful for user {user_id_str}")
        except Exception as e:
            # Log the error but don't fail the request - the interaction was already recorded
            print(f"[ERROR] Error updating preferences after interaction: {e}")
            import traceback
            traceback.print_exc()
    
    return {"success": True, "message": "Interaction recorded successfully"}

@router.get("/{article_id}", response_model=Article)
async def get_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Any:
    """
    Get a specific article by ID
    
    Endpoint: GET /api/v1/articles/{article_id}
    
    Path Parameters:
    - article_id: UUID of the article to retrieve
    
    Headers:
    - Authorization: Bearer {access_token} (optional)
    
    Returns:
    - 200 OK: Article details
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "title": "Specific Article Title",
        "link": "https://example.com/news/specific-article",
        "description": "Brief description of the specific article",
        "content": "Full content of the specific article...",
        "pub_date": "2025-04-24T11:15:00.000Z",
        "image": "https://example.com/images/specific-article.jpg",
        "source": "The Guardian",
        "urgency_score": 5,
        "created_at": "2025-04-24T11:20:00.000Z",
        "updated_at": "2025-04-24T11:20:00.000Z"
      }
    
    Error Responses:
    - 404 Not Found: Article not found
    """
    article = db.query(ArticleModel).filter(ArticleModel.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    # Convert SQLAlchemy model to dictionary for proper serialization
    article_dict = article.__dict__.copy()
    if '_sa_instance_state' in article_dict:
        article_dict.pop('_sa_instance_state')
    # Convert UUID objects to strings
    if 'id' in article_dict and hasattr(article_dict['id'], 'hex'):
        article_dict['id'] = str(article_dict['id'])
    
    return article_dict