import numpy as np
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from ..models.models import Article, User

class SearchService:
    """Service to search articles using keyword and/or vector similarity."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def search_articles(
        self,
        query: str,
        user_id: Optional[str] = None,
        sources: Optional[List[str]] = None,
        min_urgency: Optional[int] = None,
        sort_by: str = "relevance",  # Options: relevance, recency, urgency
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for articles using a text query and optional filters.
        
        This method combines:
        1. Text-based search on title, description and content
        2. Optional filtering by sources
        3. Flexible sorting by relevance, recency, or urgency
        """
        # Start with basic query for search
        base_query = self.db.query(Article)
        
        # Apply text search if query provided
        if query and query.strip():
            search_terms = [term.strip() for term in query.split() if term.strip()]
            search_conditions = []
            
            # For each term, search in title, description and content
            for term in search_terms:
                term_pattern = f"%{term}%"
                search_conditions.append(
                    or_(
                        Article.title.ilike(term_pattern),
                        Article.description.ilike(term_pattern),
                        Article.content.ilike(term_pattern)
                    )
                )
            
            # Combine conditions with AND between terms (all terms must match)
            for condition in search_conditions:
                base_query = base_query.filter(condition)
        
        # Apply source filter if provided
        if sources and len(sources) > 0:
            base_query = base_query.filter(Article.source.in_(sources))
        
        # Apply urgency filter if provided
        if min_urgency is not None:
            base_query = base_query.filter(Article.urgency_score >= min_urgency)
        
        # Execute the query to get filtered articles
        filtered_articles = base_query.all()
        
        # If no articles found, return empty result
        if not filtered_articles:
            return {
                "articles": [],
                "total": 0
            }
        
        # Handle sorting based on preference
        if sort_by == "recency":
            # Sort by publication date (newest first)
            sorted_articles = sorted(
                filtered_articles, 
                key=lambda a: a.pub_date, 
                reverse=True
            )
        elif sort_by == "urgency":
            # Sort by urgency score (highest first)
            sorted_articles = sorted(
                filtered_articles, 
                key=lambda a: a.urgency_score, 
                reverse=True
            )
        else:  # Default to relevance
            # For relevance, we need to score articles based on match
            article_scores = []
            
            for article in filtered_articles:
                # Base relevance score - could be based on term frequency, position, etc.
                # For simplicity, we'll use a default score of 1.0
                base_score = 1.0
                
                # Include urgency as a minor factor in relevance
                urgency_boost = article.urgency_score / 10 * 0.2
                final_score = base_score + urgency_boost
                
                article_scores.append((article, final_score))
            
            # Sort by final score (highest first)
            article_scores.sort(key=lambda x: x[1], reverse=True)
            sorted_articles = [article for article, _ in article_scores]
        
        # Apply pagination
        paginated_articles = sorted_articles[offset:offset+limit]
        
        return {
            "articles": paginated_articles,
            "total": len(filtered_articles)
        }
    
    def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on article titles that match the query.
        These can be used for autocompletion in the search box.
        """
        if not query or len(query.strip()) < 2:
            return []
            
        # Look for article titles that contain the query
        pattern = f"%{query}%"
        suggestions = self.db.query(Article.title).filter(
            Article.title.ilike(pattern)
        ).distinct().limit(limit).all()
        
        # Extract just the titles
        return [suggestion[0] for suggestion in suggestions]