import numpy as np
import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, Column, ARRAY, Float, select
from sqlalchemy.exc import SQLAlchemyError
from ..models.models import Article, User, user_article_interactions
from ..core.config import settings
import traceback

class RecommendationService:
    """Service to provide personalized article recommendations using vector similarity."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def get_recommendations_with_multi_vectors(
        self, 
        user_id: str, 
        limit: int = settings.DEFAULT_ARTICLES_LIMIT,
        offset: int = 0,
        exclude_read: bool = True,
        exploration_ratio: float = 0.2  # 20% exploration content by default
    ) -> List[Article]:
        """
        Get personalized recommendations using multiple interest vectors.
        
        This enhanced method uses the multiple interest vectors to better match
        diverse user interests, while still maintaining a balance between
        personalization and exploration.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of articles to return
            offset: Pagination offset
            exclude_read: Whether to exclude articles the user has already read
            exploration_ratio: Proportion of results dedicated to exploration
            
        Returns:
            A list of articles combining personalized recommendations and exploration content
        """
        try:
            # Calculate how many items to allocate to each category
            exploration_count = max(1, int(limit * exploration_ratio))
            standard_count = limit - exploration_count
            
            # Get the user
            user = self._get_user(user_id)
            if not user:
                return []
                
            # Get articles that haven't been read by the user if exclude_read is True
            articles = self._get_filtered_articles(user_id, exclude_read)
            if not articles:
                return []
            
            # Get the current time for recency calculation
            current_time = datetime.datetime.utcnow()
            max_age_days = 14  # Articles older than 14 days get minimum recency score
            
            # Initialize recommendation lists
            standard_recs = []  # For standard recommendations
            exploration_candidates = []  # For exploration recommendations
            
            # Score articles based on user preferences
            if self._has_preference_vectors(user):
                # Get user preference vectors and weights
                preference_vectors, vector_weights = self._extract_preference_vectors(user)
                
                # Score each article against user interests
                for article in articles:
                    if not article.embedding:
                        continue
                        
                    # Calculate recency score (0-1)
                    recency_score = self._calculate_recency_score(article, current_time, max_age_days)
                    
                    # Calculate urgency score (0-1)
                    urgency_score = article.urgency_score / 10
                    
                    # Calculate weighted similarity with each interest vector
                    max_similarity, weighted_similarity = self._calculate_similarities(
                        article.embedding, preference_vectors, vector_weights
                    )
                    
                    # Score for standard and exploration recommendations
                    standard_score = self._calculate_standard_score(weighted_similarity, recency_score, urgency_score)
                    exploration_score = self._calculate_exploration_score(max_similarity, recency_score, urgency_score)
                    
                    # Add to both candidate pools with appropriate scores
                    standard_recs.append((article, standard_score))
                    exploration_candidates.append((article, exploration_score))
            
            # If we have recommendation candidates
            if standard_recs:
                # Get final recommendations
                final_result = self._combine_and_paginate_recommendations(
                    standard_recs, exploration_candidates, limit, offset, exploration_ratio
                )
                return final_result
            else:
                # If no preference data, fall back to recency and urgency
                return self._get_fallback_recommendations(limit, offset)
                
        except SQLAlchemyError as e:
            self._log_error(f"Database error in get_recommendations_with_multi_vectors: {e}")
            return []
        except Exception as e:
            self._log_error(f"Error getting multi-vector recommendations: {e}")
            return []
    
    def update_user_preferences(self, user_id: str, num_clusters: int = 3) -> bool:
        """
        Unified method to update user's preference embeddings using both liked and read articles.
        
        This method combines the functionality of:
        - update_multi_vector_time_weighted_preferences
        - update_multi_vector_preferences_with_read_articles
        
        It applies different weights based on interaction type:
        - Liked articles: Strong positive signals (weight 1.0)
        - Read articles: Weaker positive signals (weight 0.3)
        
        Both types of interactions use time weighting for recency and support
        multiple vectors to represent diverse interests.
        
        Args:
            user_id: The user's ID
            num_clusters: Number of interest vectors to maintain (default: 3)
            
        Returns:
            bool: Whether the update was successful
        """
        try:
            # Get the user
            user = self._get_user(user_id)
            if not user:
                self._log_error(f"User not found: {user_id}")
                return False
            
            # Get all relevant interactions (both liked and read)
            interaction_data = self._get_liked_and_read_interactions(user_id)
            if not interaction_data:
                self._log_error(f"No article interactions found for user: {user_id}")
                return False
            
            # Extract article data with interaction weights
            article_data = self._extract_article_data_with_weights(interaction_data)
            if not article_data:
                self._log_error(f"No valid article embeddings found for user: {user_id}")
                return False
            
            # Apply time weighting combined with interaction weights
            weighted_embeddings, embedding_weights = self._apply_time_weighting_with_interaction(article_data)
            
            # Cluster the embeddings and update user preferences
            return self._cluster_and_update_preferences(user, weighted_embeddings, embedding_weights, num_clusters)
            
        except SQLAlchemyError as e:
            self._log_error(f"Database error in update_user_preferences: {e}")
            return False
        except Exception as e:
            self._log_error(f"Error updating user preferences: {e}")
            return False

    def count_available_recommendations(
        self, 
        user_id: str,
        exclude_read: bool = True,
        exploration_ratio: float = 0.2
    ) -> int:
        """
        Count the total number of articles available for recommendation for a user.
        
        This method calculates the total count of articles that would be returned
        by get_recommendations_with_multi_vectors across all pages, using the same
        filtering criteria but without pagination.
        
        Args:
            user_id: The user's ID
            exclude_read: Whether to exclude articles the user has already read
            exploration_ratio: Proportion of results dedicated to exploration
            
        Returns:
            The count of articles that match recommendation criteria
        """
        try:
            # Get the user
            user = self._get_user(user_id)
            if not user:
                return 0
                
            # Get articles that haven't been read by the user if exclude_read is True
            articles = self._get_filtered_articles(user_id, exclude_read)
            if not articles:
                return 0
            
            # If we don't have preference vectors, return the count of all filterable articles
            if not self._has_preference_vectors(user):
                return len(articles)
            
            # Count articles with valid embeddings
            valid_article_count = 0
            for article in articles:
                if article.embedding is not None:
                    valid_article_count += 1
            
            return valid_article_count
            
        except Exception as e:
            self._log_error(f"Error counting available recommendations: {e}")
            return 0

    # Helper methods for database operations
    
    def _get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def _get_article(self, article_id: str) -> Optional[Article]:
        """Get article by ID."""
        return self.db.query(Article).filter(Article.id == article_id).first()
    
    def _get_filtered_articles(self, user_id: str, exclude_read: bool) -> List[Article]:
        """Get articles filtered by read status and publication date."""
        # Start with a base query
        query = self.db.query(Article)
        
        # Filter by publication date - only get articles from the past 2 weeks
        two_weeks_ago = datetime.datetime.utcnow() - datetime.timedelta(days=14)
        query = query.filter(Article.pub_date >= two_weeks_ago)
        
        # Apply read filter if needed
        if exclude_read:
            read_article_ids = self.db.query(user_article_interactions.c.article_id).filter(
                user_article_interactions.c.user_id == user_id,
                user_article_interactions.c.read == True
            ).all()
            read_ids = [str(article_id[0]) for article_id in read_article_ids]
            if read_ids:
                query = query.filter(~Article.id.in_(read_ids))
        
        return query.all()
    
    def _get_liked_articles_with_timestamps(self, user_id: str) -> List[Tuple]:
        """Get liked articles with their timestamps."""
        return self.db.query(
            user_article_interactions.c.article_id,
            user_article_interactions.c.created_at
        ).filter(
            user_article_interactions.c.user_id == user_id,
            user_article_interactions.c.liked == True
        ).all()
    
    def _get_liked_and_read_interactions(self, user_id: str) -> List[Tuple]:
        """Get liked and read articles with interaction data."""
        return self.db.query(
            user_article_interactions.c.article_id,
            user_article_interactions.c.created_at,
            user_article_interactions.c.liked,
            user_article_interactions.c.read
        ).filter(
            user_article_interactions.c.user_id == user_id,
            # Either liked OR read
            (user_article_interactions.c.liked == True) | 
            (user_article_interactions.c.read == True)
        ).all()
    
    def _get_fallback_recommendations(self, limit: int, offset: int) -> List[Article]:
        """Get fallback recommendations based on recency and urgency."""
        return self.db.query(Article).order_by(
            desc(Article.urgency_score),
            desc(Article.pub_date)
        ).offset(offset).limit(limit).all()
    
    # Helper methods for scoring and ranking
    
    def _calculate_recency_score(self, article, current_time, max_age_days: int) -> float:
        """Calculate recency score between 0 and 1."""
        article_age = (current_time - article.pub_date).total_seconds() / 86400  # age in days
        return max(0, 1 - (article_age / max_age_days))
    
    def _calculate_similarities(self, article_embedding, preference_vectors, vector_weights) -> Tuple[float, float]:
        """Calculate max and weighted similarities between article and preference vectors."""
        max_similarity = 0
        weighted_similarity = 0
        total_weight = sum(vector_weights)
        
        for i, vector in enumerate(preference_vectors):
            similarity = self.compute_cosine_similarity(vector, article_embedding)
            # Keep track of the max similarity for exploration scoring
            max_similarity = max(max_similarity, similarity)
            # Add weighted similarity for standard scoring
            if total_weight > 0:
                weighted_similarity += similarity * (vector_weights[i] / total_weight)
        
        return max_similarity, weighted_similarity
    
    def _calculate_standard_score(self, similarity: float, recency_score: float, urgency_score: float) -> float:
        """Calculate standard recommendation score."""
        # 80% similarity, 10% recency, 10% urgency
        return (similarity * 0.8) + (recency_score * 0.1) + (urgency_score * 0.1)
    
    def _calculate_exploration_score(self, similarity: float, recency_score: float, urgency_score: float) -> float:
        """Calculate exploration recommendation score."""
        # 80% diversity (1-similarity), 10% recency, 10% urgency
        return ((1.0 - similarity) * 0.8) + (recency_score * 0.1) + (urgency_score * 0.1)
    
    def _combine_and_paginate_recommendations(
        self, 
        standard_recs: List[Tuple], 
        exploration_candidates: List[Tuple],
        limit: int,
        offset: int,
        exploration_ratio: float
    ) -> List[Article]:
        """Combine and paginate standard and exploration recommendations."""
        # Sort recommendations by their respective scores (higher is better)
        standard_recs.sort(key=lambda x: x[1], reverse=True)
        exploration_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select standard articles
        standard_articles = [article for article, _ in standard_recs]
        
        # Get IDs of standard articles to avoid duplication
        standard_ids = {str(article.id) for article in standard_articles}
        
        # Select exploration articles that aren't in standard recommendations
        exploration_articles = []
        for article, _ in exploration_candidates:
            if str(article.id) not in standard_ids:
                exploration_articles.append(article)
        
        # Calculate ratio proportions for blending
        standard_ratio = 1.0 - exploration_ratio
        
        # Create a deterministic combined list for consistent pagination
        # This is crucial for ensuring all articles are accessible through pagination
        combined_articles = []
        
        # Calculate how many of each type to include per page
        # This ensures consistent distribution across all pages
        num_standard_per_page = max(1, int(limit * standard_ratio))
        num_exploration_per_page = limit - num_standard_per_page
        
        # Calculate total number of full pages we can create
        total_standard_pages = (len(standard_articles) + num_standard_per_page - 1) // num_standard_per_page
        total_exploration_pages = (len(exploration_articles) + num_exploration_per_page - 1) // num_exploration_per_page
        total_pages = max(total_standard_pages, total_exploration_pages)
        
        # Build the complete combined article list to ensure consistent pagination
        for page in range(total_pages):
            # Add standard articles for this page
            start_idx = page * num_standard_per_page
            end_idx = min(start_idx + num_standard_per_page, len(standard_articles))
            for i in range(start_idx, end_idx):
                combined_articles.append(standard_articles[i])
            
            # Add exploration articles for this page
            start_idx = page * num_exploration_per_page
            end_idx = min(start_idx + num_exploration_per_page, len(exploration_articles))
            for i in range(start_idx, end_idx):
                combined_articles.append(exploration_articles[i])
        
        # Apply pagination to the combined list
        start_idx = offset
        end_idx = min(start_idx + limit, len(combined_articles))
        
        # Check if we're requesting a page beyond what's available
        if start_idx >= len(combined_articles):
            return []
        
        return combined_articles[start_idx:end_idx]
    
    # Helper methods for preference vectors
    
    def _has_preference_vectors(self, user: User) -> bool:
        """Check if user has preference vectors."""
        return user.preference_embeddings is not None
    
    def _extract_preference_vectors(self, user: User) -> Tuple[List, List]:
        """Extract preference vectors and weights from user data."""
        preference_vectors = []
        vector_weights = []
        
        # Handle both formats - either the structured JSON object or direct list of vectors
        if isinstance(user.preference_embeddings, dict) and "vectors" in user.preference_embeddings:
            preference_vectors = user.preference_embeddings["vectors"]
            # Optionally use the weights if they exist
            vector_weights = user.preference_embeddings.get("weights", [1.0] * len(preference_vectors))
        elif isinstance(user.preference_embeddings, list):
            # Handle legacy format (direct list of vectors)
            preference_vectors = user.preference_embeddings
            vector_weights = [1.0] * len(preference_vectors)
        
        return preference_vectors, vector_weights
    
    # Methods for handling article data
    
    def _extract_article_data(self, liked_article_records: List[Tuple]) -> List[Tuple]:
        """Extract article embeddings with timestamps from liked article records."""
        article_ids = [record[0] for record in liked_article_records]
        articles_by_id = {}
        
        for article in self.db.query(Article).filter(Article.id.in_(article_ids)).all():
            articles_by_id[article.id] = article
        
        article_data = []
        for article_id, created_at in liked_article_records:
            # Skip if article not found or has no embedding
            if article_id not in articles_by_id:
                continue
                
            article = articles_by_id[article_id]
            if not article or not hasattr(article, 'embedding') or article.embedding is None:
                continue
                
            # Add tuple of (embedding, timestamp) to our list
            article_data.append((article.embedding, created_at))
        
        return article_data
    
    def _extract_article_data_with_weights(self, interactions: List[Tuple]) -> List[Tuple]:
        """Extract article data with interaction weights from interaction records."""
        article_ids = [record[0] for record in interactions]
        articles_by_id = {}
        
        for article in self.db.query(Article).filter(Article.id.in_(article_ids)).all():
            articles_by_id[article.id] = article
        
        article_data = []
        for article_id, created_at, liked, read in interactions:
            # Skip if article not found or has no embedding
            if article_id not in articles_by_id:
                continue
                
            article = articles_by_id[article_id]
            if not article or not hasattr(article, 'embedding') or article.embedding is None:
                continue
            
            # Determine interaction weight
            # Liked articles get full weight (1.0)
            # Read articles get a constant lower weight (0.3)
            if liked:
                interaction_weight = 1.0
            elif read:
                interaction_weight = 0.3
            else:
                continue  # Skip if neither liked nor read
            
            # Add tuple of (embedding, timestamp, weight) to our list
            article_data.append((article.embedding, created_at, interaction_weight))
        
        return article_data
    
    def _apply_time_weighting(self, article_data: List[Tuple]) -> Tuple[List, List]:
        """Apply time weighting to article embeddings."""
        now = datetime.datetime.utcnow()
        max_age_days = 60  # Articles older than 60 days get minimum weight
        
        weighted_embeddings = []
        embedding_weights = []
        
        for embedding, timestamp in article_data:
            # Calculate age in days
            age_days = (now - timestamp).total_seconds() / 86400
            
            # Calculate time weight (1.0 for newest, approaching 0.0 for oldest)
            time_weight = max(0.1, 1.0 - (age_days / max_age_days))
            
            # Apply weight to embedding
            weighted_embeddings.append(np.array(embedding) * time_weight)
            embedding_weights.append(time_weight)
        
        return weighted_embeddings, embedding_weights
    
    def _apply_time_weighting_with_interaction(self, article_data: List[Tuple]) -> Tuple[List, List]:
        """Apply time weighting combined with interaction weights to article embeddings."""
        now = datetime.datetime.utcnow()
        max_age_days = 60  # Articles older than 60 days get minimum weight
        
        weighted_embeddings = []
        embedding_weights = []
        
        for embedding, timestamp, interaction_weight in article_data:
            # Calculate age in days
            age_days = (now - timestamp).total_seconds() / 86400
            
            # Calculate time weight (1.0 for newest, approaching 0.0 for oldest)
            time_weight = max(0.1, 1.0 - (age_days / max_age_days))
            
            # Combined weight factors in both interaction type and recency
            combined_weight = interaction_weight * time_weight
            
            # Apply weight to embedding
            weighted_embeddings.append(np.array(embedding) * combined_weight)
            embedding_weights.append(combined_weight)
        
        return weighted_embeddings, embedding_weights
    
    # Methods for clustering
    
    def _cluster_and_update_preferences(
        self, 
        user: User, 
        weighted_embeddings: List,
        embedding_weights: List,
        num_clusters: int
    ) -> bool:
        """Cluster embeddings and update user preferences."""
        # Convert to numpy arrays
        embeddings_array = np.array(weighted_embeddings)
        
        # Determine appropriate number of clusters
        effective_num_clusters = min(num_clusters, len(weighted_embeddings) // 2)
        if effective_num_clusters < 2:
            # Not enough data for multiple clusters, fall back to weighted average
            if len(weighted_embeddings) > 0:
                total_weight = sum(embedding_weights)
                avg_embedding = np.sum(embeddings_array, axis=0) / total_weight
                # Only update preference_embeddings, not the singular field
                user.preference_embeddings = {
                    "vectors": [avg_embedding.tolist()],
                    "weights": [1.0]
                }
                self.db.commit()
                return True
            return False
        
        # Perform K-means clustering
        preference_vectors, cluster_weights, cluster_sizes = self._kmeans_clustering(
            weighted_embeddings, embedding_weights, effective_num_clusters
        )
        
        # Save preferences to user
        user.preference_embeddings = {
            "vectors": preference_vectors,
            "weights": cluster_weights
        }
        
        # Commit changes
        self.db.commit()
        return True
    
    def _kmeans_clustering(
        self, 
        embeddings: List,
        weights: List,
        num_clusters: int
    ) -> Tuple[List, List, List]:
        """Perform k-means clustering on embeddings with weights."""
        # Initialize cluster centers randomly
        indices = np.random.choice(len(embeddings), num_clusters, replace=False)
        centroids = [embeddings[i].copy() for i in indices]
        
        # Run k-means for a set number of iterations
        max_iterations = 10
        converged = False
        
        for _ in range(max_iterations):
            if converged:
                break
                
            # Assign points to clusters
            clusters = [[] for _ in range(num_clusters)]
            cluster_weights = [[] for _ in range(num_clusters)]
            
            for i, embedding in enumerate(embeddings):
                # Find nearest centroid using cosine similarity
                nearest_cluster = 0
                min_distance = float('inf')
                
                for c, centroid in enumerate(centroids):
                    similarity = self.compute_cosine_similarity(embedding, centroid)
                    distance = 1.0 - similarity  # Convert to distance (lower is better)
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_cluster = c
                
                # Assign to cluster
                clusters[nearest_cluster].append(embedding)
                cluster_weights[nearest_cluster].append(weights[i])
            
            # Update centroids
            old_centroids = centroids.copy()
            for i in range(num_clusters):
                if len(clusters[i]) > 0:
                    # Weighted average of points in cluster
                    total_weight = sum(cluster_weights[i])
                    if total_weight > 0:
                        weighted_sum = np.zeros_like(clusters[i][0])
                        for j, point in enumerate(clusters[i]):
                            weighted_sum += point * cluster_weights[i][j]
                        centroids[i] = weighted_sum / total_weight
            
            # Check for convergence
            converged = True
            for i, centroid in enumerate(centroids):
                if len(clusters[i]) > 0:  # Only check non-empty clusters
                    sim = self.compute_cosine_similarity(centroid, old_centroids[i])
                    if sim < 0.99:  # Less than 99% similar
                        converged = False
                        break
        
        # Filter out empty clusters and convert to lists
        preference_vectors = []
        cluster_sizes = []
        cluster_weights_normalized = []
        
        for i, cluster_points in enumerate(clusters):
            if len(cluster_points) > 0:
                preference_vectors.append(centroids[i].tolist())
                cluster_sizes.append(len(cluster_points))
                cluster_weights_normalized.append(len(cluster_points))
        
        # Add diversity if needed
        self._add_diverse_vectors(
            preference_vectors, 
            cluster_sizes, 
            cluster_weights_normalized, 
            embeddings, 
            num_clusters
        )
        
        # Normalize weights to sum to 1.0
        if cluster_weights_normalized:
            total_weight = sum(cluster_weights_normalized)
            cluster_weights_normalized = [w/total_weight for w in cluster_weights_normalized]
        
        return preference_vectors, cluster_weights_normalized, cluster_sizes
    
    def _add_diverse_vectors(
        self,
        preference_vectors: List,
        cluster_sizes: List,
        cluster_weights: List,
        embeddings: List,
        target_clusters: int
    ) -> None:
        """Add diverse vectors to reach the target number of clusters."""
        while len(preference_vectors) < target_clusters and len(embeddings) > 0:
            # Add the embedding furthest from existing centers
            max_min_distance = -1
            furthest_point = None
            
            for embedding in embeddings:
                min_distance = float('inf')
                for center in preference_vectors:
                    similarity = self.compute_cosine_similarity(embedding, center)
                    distance = 1.0 - similarity
                    min_distance = min(min_distance, distance)
                
                if min_distance > max_min_distance:
                    max_min_distance = min_distance
                    furthest_point = embedding
            
            if furthest_point is not None:
                preference_vectors.append(furthest_point.tolist())
                cluster_sizes.append(1)
                # Add a small weight for this additional point
                cluster_weights.append(0.1)
    
    # Error handling
    
    def _log_error(self, message: str) -> None:
        """Log an error with traceback."""
        print(message)
        traceback.print_exc()