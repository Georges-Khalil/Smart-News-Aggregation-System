import numpy as np
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, Column, ARRAY, Float
from ..models.models import Article, User, user_article_interactions
from ..core.config import settings
# Temporarily remove KMeans to avoid compatibility issues
# from sklearn.cluster import KMeans

class RecommendationService:
    """Service to provide personalized article recommendations using vector similarity."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def update_user_preference_embedding(self, user_id: str) -> bool:
        """Update user's preference embedding based on their liked articles."""
        try:
            # Get the user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Get articles the user has interacted with (liked)
            liked_articles = self.db.query(Article).join(
                user_article_interactions,
                Article.id == user_article_interactions.c.article_id
            ).filter(
                user_article_interactions.c.user_id == user_id,
                user_article_interactions.c.liked == True
            ).all()
            
            if not liked_articles:
                # User hasn't liked any articles yet
                return False
            
            # Average the embeddings of liked articles
            embeddings = [np.array(article.embedding) for article in liked_articles if article.embedding]
            if not embeddings:
                return False
                
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            
            # Update user's preference embedding
            user.preference_embedding = avg_embedding
            self.db.commit()
            
            return True
        except Exception as e:
            print(f"Error updating user preference: {e}")
            return False
    
    def update_multi_vector_time_weighted_preferences(self, user_id: str, num_clusters: int = 3) -> bool:
        """
        Update user's preference embeddings using multiple interest vectors with time weighting.
        
        This combines two approaches:
        1. Time-weighting: Recent likes have more influence than older ones
        2. Multi-vector: Multiple embeddings to represent diverse interests
        
        Args:
            user_id: The user's ID
            num_clusters: Number of interest vectors to maintain (default: 3)
            
        Returns:
            bool: Whether the update was successful
        """
        try:
            # Get the user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"User not found: {user_id}")
                return False
            
            # Instead of using a complex join that might return inconsistent results,
            # let's use a two-step query approach that's more reliable:
            
            # 1. First query: Get article IDs and timestamps for liked articles
            liked_article_records = self.db.query(
                user_article_interactions.c.article_id,
                user_article_interactions.c.created_at
            ).filter(
                user_article_interactions.c.user_id == user_id,
                user_article_interactions.c.liked == True
            ).all()
            
            if not liked_article_records:
                print(f"No liked articles found for user: {user_id}")
                return False
            
            # 2. Second query: Fetch the full Article objects directly using their IDs
            # and create a mapping for easy lookup
            article_ids = [record[0] for record in liked_article_records]
            articles_by_id = {}
            
            for article in self.db.query(Article).filter(Article.id.in_(article_ids)).all():
                articles_by_id[article.id] = article
            
            # Extract article embeddings with timestamps
            article_data = []
            
            for article_id, created_at in liked_article_records:
                # Safely get the article using the ID
                if article_id not in articles_by_id:
                    print(f"Warning: Article {article_id} not found in database")
                    continue
                    
                article = articles_by_id[article_id]
                
                # Skip if article doesn't have an embedding
                if not article or not hasattr(article, 'embedding') or article.embedding is None:
                    print(f"Warning: Article {article_id} has no embedding")
                    continue
                    
                # Add tuple of (embedding, timestamp) to our list
                article_data.append((article.embedding, created_at))
            
            if not article_data:
                print(f"No valid article embeddings found for user: {user_id}")
                return False
            
            # Apply time weighting
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
            
            # Convert to numpy arrays for easier manipulation
            embeddings_array = np.array(weighted_embeddings)
            
            # Determine appropriate number of clusters based on data size
            effective_num_clusters = min(num_clusters, len(weighted_embeddings) // 2)
            if effective_num_clusters < 2:
                # Not enough data for multiple clusters, fall back to weighted average
                if len(weighted_embeddings) > 0:
                    total_weight = sum(embedding_weights)
                    avg_embedding = np.sum(embeddings_array, axis=0) / total_weight
                    user.preference_embedding = avg_embedding.tolist()
                    # Initialize preference_embeddings as a structured JSON object with one vector
                    user.preference_embeddings = {
                        "vectors": [avg_embedding.tolist()],
                        "weights": [1.0]
                    }
                    self.db.commit()
                    return True
                return False
            
            # Custom clustering implementation instead of KMeans
            # This is a simple implementation of k-means clustering
            # Initialize cluster centers randomly
            indices = np.random.choice(len(weighted_embeddings), effective_num_clusters, replace=False)
            centroids = [weighted_embeddings[i].copy() for i in indices]
            
            # Run k-means for a set number of iterations
            max_iterations = 10
            for _ in range(max_iterations):
                # Assign points to clusters
                clusters = [[] for _ in range(effective_num_clusters)]
                cluster_weights = [[] for _ in range(effective_num_clusters)]
                
                for i, embedding in enumerate(weighted_embeddings):
                    # Find nearest centroid
                    nearest_cluster = 0
                    min_distance = float('inf')
                    
                    for c, centroid in enumerate(centroids):
                        # Using cosine similarity (higher is better)
                        similarity = self.compute_cosine_similarity(embedding, centroid)
                        distance = 1.0 - similarity  # Convert to distance (lower is better)
                        
                        if distance < min_distance:
                            min_distance = distance
                            nearest_cluster = c
                    
                    # Assign to cluster
                    clusters[nearest_cluster].append(embedding)
                    cluster_weights[nearest_cluster].append(embedding_weights[i])
                
                # Update centroids
                old_centroids = centroids.copy()
                for i in range(effective_num_clusters):
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
                
                if converged:
                    break
            
            # Filter out empty clusters and convert to lists
            preference_vectors = []
            cluster_sizes = []
            cluster_weights_normalized = []
            
            for i, cluster_points in enumerate(clusters):
                if len(cluster_points) > 0:
                    preference_vectors.append(centroids[i].tolist())
                    cluster_sizes.append(len(cluster_points))
                    # Calculate normalized weight based on cluster size
                    cluster_weights_normalized.append(len(cluster_points))
            
            # Normalize weights to sum to 1.0
            total_size = sum(cluster_weights_normalized)
            if total_size > 0:
                cluster_weights_normalized = [size/total_size for size in cluster_weights_normalized]
            
            # If we lost clusters due to convergence, add some diversity
            while len(preference_vectors) < effective_num_clusters and len(weighted_embeddings) > 0:
                # Add the embedding furthest from existing centers
                max_min_distance = -1
                furthest_point = None
                
                for embedding in weighted_embeddings:
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
                    cluster_weights_normalized.append(0.1)
                    
            # Ensure weights are normalized to sum to 1.0
            if cluster_weights_normalized:
                total_weight = sum(cluster_weights_normalized)
                cluster_weights_normalized = [w/total_weight for w in cluster_weights_normalized]
            
            # Store in user's preference_embeddings field using consistent JSON structure
            user.preference_embeddings = {
                "vectors": preference_vectors,
                "weights": cluster_weights_normalized
            }
            
            # Keep the main preference_embedding as the centroid of the largest cluster
            largest_cluster_idx = cluster_sizes.index(max(cluster_sizes))
            user.preference_embedding = preference_vectors[largest_cluster_idx]
            
            # Commit changes
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating multi-vector preferences: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_personalized_recommendations(
        self, 
        user_id: str, 
        limit: int = settings.DEFAULT_ARTICLES_LIMIT,
        offset: int = 0,
        exclude_read: bool = True
    ) -> List[Article]:
        """Get personalized article recommendations for a user."""
        try:
            # Get the user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
                
            # Start building the query
            query = self.db.query(Article)
                
            # Filter out articles the user has already read if requested
            if exclude_read:
                read_article_ids = self.db.query(user_article_interactions.c.article_id).filter(
                    user_article_interactions.c.user_id == user_id,
                    user_article_interactions.c.read == True
                )
                query = query.filter(~Article.id.in_(read_article_ids))
            
            # If user has a preference embedding, use it for similarity ranking
            if user.preference_embedding:
                # Get all articles that match the filters
                articles = query.all()
                
                # Get the current time for recency calculation
                current_time = datetime.datetime.utcnow()
                max_age_days = 14  # Articles older than 14 days get minimum recency score
                
                # Compute similarity scores
                scored_articles = []
                for article in articles:
                    if article.embedding:
                        # Calculate similarity score (0-1)
                        similarity = self.compute_cosine_similarity(
                            user.preference_embedding, article.embedding
                        )
                        
                        # Calculate recency score (0-1)
                        # Newer articles get scores closer to 1, older articles closer to 0
                        article_age = (current_time - article.pub_date).total_seconds() / (86400)  # age in days
                        recency_score = max(0, 1 - (article_age / max_age_days))
                        
                        # Blend similarity, recency, and urgency for final score
                        # 60% similarity, 20% recency, 20% urgency
                        score = (similarity * 0.6) + (recency_score * 0.2) + ((article.urgency_score / 10) * 0.2)
                        scored_articles.append((article, score))
                
                # Sort by score (descending) and get the requested slice
                scored_articles.sort(key=lambda x: x[1], reverse=True)
                result = [article for article, _ in scored_articles[offset:offset+limit]]
                return result
            else:
                # If no preference embedding, fall back to recency and urgency
                return query.order_by(
                    desc(Article.urgency_score),
                    desc(Article.pub_date)
                ).offset(offset).limit(limit).all()
                
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def get_recommendations(
        self, 
        user_id: str, 
        limit: int = settings.DEFAULT_ARTICLES_LIMIT,
        offset: int = 0,
        exclude_read: bool = True,
        exploration_ratio: float = 0.2  # 20% exploration content by default
    ) -> List[Article]:
        """
        Get personalized recommendations with integrated content exploration.
        
        This method combines personalized recommendations with diverse exploration content,
        providing a balanced feed that both matches user interests and helps them
        discover new content outside their usual preferences.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of articles to return
            offset: Pagination offset
            exclude_read: Whether to exclude articles the user has already read
            exploration_ratio: Proportion of results dedicated to exploration (0.0-1.0)
            
        Returns:
            A list of articles combining personalized recommendations and exploration content
        """
        try:
            # Calculate how many items to allocate to each category
            exploration_count = max(1, int(limit * exploration_ratio))
            standard_count = limit - exploration_count
            
            # Get the user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
                
            # Start building the query
            query = self.db.query(Article)
                
            # Filter out articles the user has already read if requested
            if exclude_read:
                read_article_ids = self.db.query(user_article_interactions.c.article_id).filter(
                    user_article_interactions.c.user_id == user_id,
                    user_article_interactions.c.read == True
                ).all()
                read_ids = [str(article_id[0]) for article_id in read_article_ids]
                query = query.filter(~Article.id.in_(read_ids))
            else:
                read_ids = []
            
            # Get all articles that match the filters
            articles = query.all()
            
            # Get the current time for recency calculation
            current_time = datetime.datetime.utcnow()
            max_age_days = 14  # Articles older than 14 days get minimum recency score
            
            # For standard recommendations
            standard_recs = []
            # For exploration recommendations
            exploration_candidates = []
            
            # If user has a preference embedding, use it for scoring
            if user.preference_embedding:
                # Separate articles into standard and exploration candidates based on scoring
                for article in articles:
                    if not article.embedding:
                        continue
                        
                    # Calculate similarity score (0-1)
                    similarity = self.compute_cosine_similarity(
                        user.preference_embedding, article.embedding
                    )
                    
                    # Calculate recency score (0-1)
                    article_age = (current_time - article.pub_date).total_seconds() / (86400)  # age in days
                    recency_score = max(0, 1 - (article_age / max_age_days))
                    
                    # Calculate urgency score (0-1)
                    urgency_score = article.urgency_score / 10
                    
                    # Standard recommendation score: high similarity is good
                    # 60% similarity, 20% recency, 20% urgency
                    standard_score = (similarity * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
                    
                    # Exploration score: low similarity (diversity) is good
                    # 60% diversity (1-similarity), 20% recency, 20% urgency
                    exploration_score = ((1.0 - similarity) * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
                    
                    # Add to both candidate pools with appropriate scores
                    standard_recs.append((article, standard_score))
                    exploration_candidates.append((article, exploration_score))
                
                # Sort recommendations by their respective scores (higher is better)
                standard_recs.sort(key=lambda x: x[1], reverse=True)
                exploration_candidates.sort(key=lambda x: x[1], reverse=True)
                
                # Select top standard recommendations
                standard_articles = [article for article, _ in standard_recs[:standard_count]]
                
                # Get IDs of selected standard articles to avoid duplication
                standard_ids = {str(article.id) for article in standard_articles}
                
                # Select top exploration articles that aren't in standard recommendations
                exploration_articles = []
                for article, _ in exploration_candidates:
                    if str(article.id) not in standard_ids and len(exploration_articles) < exploration_count:
                        exploration_articles.append(article)
                
                # Combine the recommendations
                result = standard_articles + exploration_articles
                
                # Apply pagination
                final_result = result[offset:offset+limit]
                return final_result
            else:
                # If no preference embedding, fall back to recency and urgency
                return query.order_by(
                    desc(Article.urgency_score),
                    desc(Article.pub_date)
                ).offset(offset).limit(limit).all()
                
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []

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
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
                
            # Start building the query
            query = self.db.query(Article)
                
            # Filter out articles the user has already read if requested
            if exclude_read:
                read_article_ids = self.db.query(user_article_interactions.c.article_id).filter(
                    user_article_interactions.c.user_id == user_id,
                    user_article_interactions.c.read == True
                ).all()
                read_ids = [str(article_id[0]) for article_id in read_article_ids]
                query = query.filter(~Article.id.in_(read_ids))
            else:
                read_ids = []
            
            # Get all articles that match the filters
            articles = query.all()
            
            # Get the current time for recency calculation
            current_time = datetime.datetime.utcnow()
            max_age_days = 14  # Articles older than 14 days get minimum recency score
            
            # For standard recommendations
            standard_recs = []
            # For exploration recommendations
            exploration_candidates = []
            
            # Handle multiple preference embeddings with proper structure handling
            if user.preference_embeddings:
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
                
                if preference_vectors and len(preference_vectors) > 0:
                    # Score each article against each interest vector
                    for article in articles:
                        if not article.embedding:
                            continue
                            
                        # Calculate recency score (0-1)
                        article_age = (current_time - article.pub_date).total_seconds() / (86400)  # age in days
                        recency_score = max(0, 1 - (article_age / max_age_days))
                        
                        # Calculate urgency score (0-1)
                        urgency_score = article.urgency_score / 10
                        
                        # Calculate weighted similarity with each interest vector
                        max_similarity = 0
                        weighted_similarity = 0
                        total_weight = sum(vector_weights)
                        
                        for i, vector in enumerate(preference_vectors):
                            similarity = self.compute_cosine_similarity(vector, article.embedding)
                            # Keep track of the max similarity for exploration scoring
                            max_similarity = max(max_similarity, similarity)
                            # Add weighted similarity for standard scoring
                            if total_weight > 0:
                                weighted_similarity += similarity * (vector_weights[i] / total_weight)
                        
                        # Standard recommendation score: weighted similarity is good
                        # 60% similarity, 20% recency, 20% urgency
                        standard_score = (weighted_similarity * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
                        
                        # Exploration score: low similarity (diversity) is good
                        # Use max_similarity to ensure we're truly different from all interests
                        # 60% diversity (1-similarity), 20% recency, 20% urgency
                        exploration_score = ((1.0 - max_similarity) * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
                        
                        # Add to both candidate pools with appropriate scores
                        standard_recs.append((article, standard_score))
                        exploration_candidates.append((article, exploration_score))
                else:
                    # Fall back to single vector if multiple vectors are empty
                    self._score_with_single_vector(user, articles, current_time, max_age_days, 
                                                 standard_recs, exploration_candidates)
            # Fall back to single vector if multiple vectors not available
            elif user.preference_embedding:
                self._score_with_single_vector(user, articles, current_time, max_age_days, 
                                             standard_recs, exploration_candidates)
            
            # If we have recommendation candidates
            if standard_recs:
                # Sort recommendations by their respective scores (higher is better)
                standard_recs.sort(key=lambda x: x[1], reverse=True)
                exploration_candidates.sort(key=lambda x: x[1], reverse=True)
                
                # Select top standard recommendations across all pages, not just for current page
                # This way we maintain the ratio of personalized vs exploration content
                standard_articles = [article for article, _ in standard_recs]
                
                # Get IDs of selected standard articles to avoid duplication
                standard_ids = {str(article.id) for article in standard_articles}
                
                # Select exploration articles that aren't in standard recommendations
                exploration_articles = []
                for article, _ in exploration_candidates:
                    if str(article.id) not in standard_ids:
                        exploration_articles.append(article)
                
                # Combine all recommendations
                all_results = []
                
                # First add standard articles based on the exploration ratio
                # For example, if ratio is 0.2, we add 80% standard and 20% exploration
                standard_ratio = 1.0 - exploration_ratio
                num_standard_per_page = int(limit * standard_ratio)
                num_exploration_per_page = limit - num_standard_per_page
                
                # Get total number of articles for pagination info
                total_recommendations = len(standard_articles) + len(exploration_articles)
                
                # Calculate how many standard and exploration articles we need up to the current offset
                total_standard_needed = min(len(standard_articles), num_standard_per_page * ((offset // limit) + 1))
                total_exploration_needed = min(len(exploration_articles), num_exploration_per_page * ((offset // limit) + 1))
                
                # Add standard articles
                for i in range(min(total_standard_needed, len(standard_articles))):
                    all_results.append((standard_articles[i], 1, i))  # (article, type, original_position)
                
                # Add exploration articles
                for i in range(min(total_exploration_needed, len(exploration_articles))):
                    all_results.append((exploration_articles[i], 2, i))  # (article, type, original_position)
                
                # Sort the mixed results ensuring we maintain the exact ratio within each page
                # The formula ensures standard articles are placed first, followed by exploration
                # But they maintain their internal relative ordering based on original position
                all_results.sort(key=lambda x: (
                    (x[1] - 1) * limit + (x[2] // num_standard_per_page if x[1] == 1 else x[2] // num_exploration_per_page)
                ))
                
                # Extract just the articles for the requested page
                start_idx = offset
                end_idx = min(start_idx + limit, len(all_results))
                
                # Make sure we don't go out of bounds (this is what fixed the pagination bug)
                if start_idx >= len(all_results):
                    return []  # Return empty list if we're past the last page
                
                # Get the final paginated result
                final_result = [article for article, _, _ in all_results[start_idx:end_idx]]
                
                return final_result
            else:
                # If no preference data, fall back to recency and urgency
                return query.order_by(
                    desc(Article.urgency_score),
                    desc(Article.pub_date)
                ).offset(offset).limit(limit).all()
                
        except Exception as e:
            print(f"Error getting multi-vector recommendations: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _score_with_single_vector(self, user, articles, current_time, max_age_days, standard_recs, exploration_candidates):
        """Helper method to score articles with a single preference vector."""
        for article in articles:
            if not article.embedding:
                continue
                
            # Calculate similarity score (0-1)
            similarity = self.compute_cosine_similarity(
                user.preference_embedding, article.embedding
            )
            
            # Calculate recency score (0-1)
            article_age = (current_time - article.pub_date).total_seconds() / (86400)  # age in days
            recency_score = max(0, 1 - (article_age / max_age_days))
            
            # Calculate urgency score (0-1)
            urgency_score = article.urgency_score / 10
            
            # Standard recommendation score: high similarity is good
            # 60% similarity, 20% recency, 20% urgency
            standard_score = (similarity * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
            
            # Exploration score: low similarity (diversity) is good
            # 60% diversity (1-similarity), 20% recency, 20% urgency
            exploration_score = ((1.0 - similarity) * 0.6) + (recency_score * 0.2) + (urgency_score * 0.2)
            
            # Add to both candidate pools with appropriate scores
            standard_recs.append((article, standard_score))
            exploration_candidates.append((article, exploration_score))
    
    def update_preference_from_feedback(
        self, 
        user_id: str, 
        article_id: str, 
        feedback_type: str
    ) -> bool:
        """
        Update user preferences based on article feedback.
        
        Args:
            user_id: The user's ID
            article_id: ID of the article the user interacted with
            feedback_type: Type of feedback (like, dislike, save, etc.)
            
        Returns:
            Whether the update was successful
        """
        try:
            # Get the user and article
            user = self.db.query(User).filter(User.id == user_id).first()
            article = self.db.query(Article).filter(Article.id == article_id).first()
            
            if not user or not article or not article.embedding:
                return False
            
            # Get the current preference data
            preference_data = {}
            if not user.preference_embeddings:
                # If user has no preferences yet, initialize with a single vector
                preference_data = {
                    "vectors": [article.embedding],
                    "weights": [1.0]
                }
            else:
                # Handle both formats for backward compatibility
                if isinstance(user.preference_embeddings, dict) and "vectors" in user.preference_embeddings:
                    preference_data = user.preference_embeddings
                elif isinstance(user.preference_embeddings, list):
                    # Convert legacy format to structured format
                    preference_data = {
                        "vectors": user.preference_embeddings,
                        "weights": [1.0] * len(user.preference_embeddings)
                    }
                else:
                    # Initialize with defaults if invalid format
                    preference_data = {
                        "vectors": [article.embedding],
                        "weights": [1.0]
                    }
            
            # Extract vectors and weights
            vectors = preference_data.get("vectors", [])
            weights = preference_data.get("weights", [])
            
            # Ensure weights match vectors
            if len(weights) != len(vectors):
                weights = [1.0] * len(vectors)
            
            # Calculate similarities to find the closest interest vector
            closest_idx = 0
            max_similarity = -1
            
            for i, vector in enumerate(vectors):
                similarity = self.compute_cosine_similarity(vector, article.embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    closest_idx = i
            
            # Determine learning rate based on feedback type
            learning_rate = 0.1  # Default learning rate
            if feedback_type.lower() == 'like':
                adjustment = learning_rate
            elif feedback_type.lower() == 'dislike':
                adjustment = -learning_rate
            elif feedback_type.lower() == 'save':
                adjustment = learning_rate * 1.5  # Stronger positive signal
            else:
                adjustment = 0  # No adjustment for other types
            
            # If strong positive feedback and similarity is low, add as a new interest vector
            if adjustment > 0 and max_similarity < 0.3 and feedback_type.lower() in ['like', 'save']:
                # Add new interest vector based on this article
                vectors.append(article.embedding)
                
                # Assign a moderate weight to this new interest
                new_weight = 0.5
                
                # Normalize existing weights to accommodate the new vector
                total_current_weight = sum(weights)
                if total_current_weight > 0:
                    scale_factor = (1.0 - new_weight) / total_current_weight
                    weights = [w * scale_factor for w in weights]
                
                # Add the new weight
                weights.append(new_weight)
            else:
                # Otherwise adjust the closest vector's weight
                weights[closest_idx] = max(0.1, min(2.0, weights[closest_idx] + adjustment))
                
                # Normalize weights to sum to 1
                weight_sum = sum(weights)
                if weight_sum > 0:
                    weights = [w / weight_sum for w in weights]
            
            # Update the preference data
            preference_data = {
                "vectors": vectors,
                "weights": weights
            }
            
            # Save the updated preferences
            user.preference_embeddings = preference_data
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating preferences from feedback: {e}")
            self.db.rollback()
            return False