def update_preferences(self, user_id: str, preference_vectors: Union[List[List[float]], Dict], weight_vectors: Optional[List[float]] = None) -> bool:
        """
        Update a user's preference embeddings.
        
        Args:
            user_id: The user's ID
            preference_vectors: Multiple interest vectors OR a structured dictionary containing vectors and weights
            weight_vectors: Optional weights for the vectors (if preference_vectors is a list)
            
        Returns:
            Whether the update was successful
        """
        try:
            # Standardize the format to use the structured JSON approach
            embeddings_data = {}
            
            # If the input is already in the structured format, use it directly
            if isinstance(preference_vectors, dict) and "vectors" in preference_vectors:
                embeddings_data = preference_vectors
            # Otherwise, convert the list of vectors to the structured format
            elif isinstance(preference_vectors, list):
                # Use provided weights or default to equal weights
                if not weight_vectors or len(weight_vectors) != len(preference_vectors):
                    weight_vectors = [1.0] * len(preference_vectors)
                    
                embeddings_data = {
                    "vectors": preference_vectors,
                    "weights": weight_vectors
                }
            
            # Update the user's preferences
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
                
            user.preference_embeddings = embeddings_data
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            self.db.rollback()
            return False

def initialize_preferences(self, user_id: str, initial_categories: List[str] = None) -> bool:
        """
        Initialize a new user's preference embeddings based on selected categories.
        
        Args:
            user_id: The user's ID
            initial_categories: List of category names the user is interested in
            
        Returns:
            Whether the initialization was successful
        """
        try:
            if not initial_categories:
                initial_categories = ["general"]  # Default to general news
                
            # Get the category embeddings for the selected categories
            category_service = CategoryService(self.db)
            category_vectors = []
            for category_name in initial_categories:
                category = category_service.get_category_by_name(category_name)
                if category and category.embedding:
                    category_vectors.append(category.embedding)
            
            if not category_vectors:
                # If no valid categories, use a default general embedding
                # This could be an average of all categories or a pre-defined general vector
                default_vector = [0.0] * 384  # Using 384 for Sentence-BERT dimension
                category_vectors.append(default_vector)
            
            # Structure the preference data in our standardized format
            # Each category gets equal weight initially
            weight_vectors = [1.0 / len(category_vectors)] * len(category_vectors)
            
            embeddings_data = {
                "vectors": category_vectors,
                "weights": weight_vectors
            }
            
            # Update the user's preferences with the structured data
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
                
            user.preference_embeddings = embeddings_data
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error initializing user preferences: {e}")
            self.db.rollback()
            return False