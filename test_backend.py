import requests
import json
import sys
from datetime import datetime
import time
import uuid

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_USER = {
    "email": "test@example.com",
    "password": "test1234",
    "full_name": "Test User"
}

class BackendTester:
    def __init__(self):
        self.access_token = None
        self.headers = None
        self.available_sources = None

    def log(self, message, success=True):
        """Print a formatted log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"[{timestamp}] {status} {message}")
        sys.stdout.flush()

    def handle_response(self, response, message):
        """Handle API response and log result"""
        try:
            if response.status_code in [200, 201, 204]:
                data = response.json()
                self.log(f"{message}: Success")
                return data
            else:
                self.log(f"{message}: Failed with status {response.status_code} - {response.text}", False)
                return None
        except Exception as e:
            self.log(f"{message}: Error - {str(e)}", False)
            return None

    def register_user(self):
        """Register a test user"""
        self.log("Attempting to register user...")
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=TEST_USER
        )
        
        # If user already exists, it will return a 400 error with "Email already registered"
        if response.status_code == 400 and "Email already registered" in response.text:
            self.log("User already exists, proceeding with login")
            return True
            
        return self.handle_response(response, "User registration") is not None

    def login(self):
        """Login with test user credentials"""
        self.log("Attempting to login...")
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        data = self.handle_response(response, "User login")
        if data:
            self.access_token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            return True
        return False

    def get_user_profile(self):
        """Get current user profile"""
        self.log("Fetching user profile...")
        response = requests.get(
            f"{API_BASE_URL}/auth/me",
            headers=self.headers
        )
        return self.handle_response(response, "Get user profile") is not None

    def get_recent_articles(self, page=1, page_size=10, source_filter=None):
        """Get recent articles feed with optional source filtering and pagination"""
        self.log(f"Fetching recent articles (page {page}, size {page_size})...")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if source_filter:
            params["source_filter"] = source_filter
            self.log(f"Applying source filter: {source_filter}")
        
        response = requests.get(
            f"{API_BASE_URL}/articles/recent",
            headers=self.headers,
            params=params
        )
        
        data = self.handle_response(response, "Get recent articles")
        if data:
            article_count = len(data.get("data", []))
            total_count = data.get("total", 0)
            current_page = data.get("page", 1)
            total_pages = data.get("total_pages", 1)
            
            self.log(f"Retrieved {article_count} recent articles (page {current_page}/{total_pages}, total: {total_count})")
            
            # Extract sources for future tests if not already done
            if not self.available_sources and article_count > 0:
                self.available_sources = list(set([a.get("source") for a in data.get("data", []) if a.get("source")]))
                if self.available_sources:
                    self.log(f"Found available sources: {', '.join(self.available_sources)}")
            
            return data.get("data", [])
        return []

    def test_pagination(self):
        """Test pagination functionality on recent articles endpoint"""
        self.log("Testing pagination...")
        
        # Get first page with small page size
        page1 = self.get_recent_articles(page=1, page_size=3)
        if not page1:
            self.log("No articles found for pagination test", False)
            return False
            
        # Get second page with same page size
        page2 = self.get_recent_articles(page=2, page_size=3)
        
        # Check if pages are different
        page1_ids = [a.get("id") for a in page1]
        page2_ids = [a.get("id") for a in page2]
        
        if not page2:
            self.log("Second page empty - this could be normal if there are few articles")
            return len(page1) <= 3  # At least first page pagination works
            
        # Check for duplicate articles between pages
        duplicate_ids = set(page1_ids).intersection(set(page2_ids))
        if duplicate_ids:
            self.log(f"Found duplicate articles between pages: {duplicate_ids}", False)
            return False
            
        self.log("Pagination is working correctly")
        return True

    def test_source_filtering(self):
        """Test source filtering on recent articles endpoint"""
        self.log("Testing source filtering...")
        
        if not self.available_sources or len(self.available_sources) < 1:
            self.log("No sources available for filter testing", False)
            return False
            
        test_source = self.available_sources[0]
        self.log(f"Testing filter with source: {test_source}")
        
        filtered_articles = self.get_recent_articles(source_filter=[test_source])
        if not filtered_articles:
            self.log(f"No articles found for source: {test_source}", False)
            return False
            
        # Verify all articles match the source filter
        invalid_sources = [a.get("source") for a in filtered_articles if a.get("source") != test_source]
        if invalid_sources:
            self.log(f"Found articles with wrong sources: {set(invalid_sources)}", False)
            return False
            
        self.log("Source filtering is working correctly")
        return True

    def get_personalized_feed(self, exploration_ratio=0.2):
        """Get personalized feed with configurable exploration ratio"""
        self.log(f"Fetching personalized feed (exploration_ratio={exploration_ratio})...")
        response = requests.get(
            f"{API_BASE_URL}/articles/feed",
            headers=self.headers,
            params={"exploration_ratio": exploration_ratio}
        )
        data = self.handle_response(response, "Get personalized feed")
        if data:
            article_count = len(data.get("data", []))
            self.log(f"Retrieved {article_count} personalized articles")
            return data.get("data", [])
        return []

    def search_articles(self, query, sources=None, min_urgency=None, sort_by="relevance", personalized=True):
        """Search for articles with advanced options"""
        params = {
            "query": query,
            "sort_by": sort_by,
            "personalized": personalized
        }
        
        if sources:
            params["sources"] = sources
        if min_urgency:
            params["min_urgency"] = min_urgency
            
        search_desc = f"'{query}' (sort: {sort_by}"
        if sources:
            search_desc += f", sources: {sources}"
        if min_urgency:
            search_desc += f", min_urgency: {min_urgency}"
        search_desc += f", personalized: {personalized})"
        
        self.log(f"Searching for articles with query: {search_desc}...")
        response = requests.get(
            f"{API_BASE_URL}/articles/search",
            headers=self.headers,
            params=params
        )
        data = self.handle_response(response, "Search articles")
        if data:
            article_count = len(data.get("data", []))
            self.log(f"Found {article_count} articles matching query")
            return data.get("data", [])
        return []

    def test_search_options(self):
        """Test various search options and sorting methods"""
        self.log("Testing advanced search options...")
        
        # First, do a generic search to get some results
        base_results = self.search_articles("news")
        if not base_results:
            self.log("No results for base search query", False)
            return False
            
        # Test different sort options
        sort_methods = ["relevance", "recency", "urgency"]
        sort_results = {}
        
        for sort_method in sort_methods:
            results = self.search_articles("news", sort_by=sort_method)
            sort_results[sort_method] = results
            if not results:
                self.log(f"No results for sort method: {sort_method}", False)
                
        # Check if different sort methods give different ordering
        # This is a simple heuristic - different sort methods should usually give different ordering
        different_orders = len(set([tuple(a.get("id") for a in results[:3]) for results in sort_results.values() if results]))
        if different_orders <= 1 and len(sort_results) > 1:
            self.log("All sort methods returned identical article ordering - this is suspicious", False)
        else:
            self.log("Different sort methods return different article ordering as expected")
            
        # Test source filtering if sources are available
        if self.available_sources and len(self.available_sources) > 0:
            source_results = self.search_articles("news", sources=[self.available_sources[0]])
            if source_results:
                # Verify all articles match the source filter
                invalid_sources = [a.get("source") for a in source_results if a.get("source") != self.available_sources[0]]
                if invalid_sources:
                    self.log(f"Search source filtering not working correctly", False)
                else:
                    self.log("Search source filtering is working correctly")
                    
        return True

    def get_search_suggestions(self, query):
        """Get search suggestions"""
        self.log(f"Getting search suggestions for: '{query}'...")
        response = requests.get(
            f"{API_BASE_URL}/articles/search/suggestions",
            headers=self.headers,
            params={"query": query}
        )
        data = self.handle_response(response, "Get search suggestions")
        if data:
            self.log(f"Received {len(data)} search suggestions")
            return data
        return []

    def interact_with_article(self, article_id, read=None, liked=None, read_time=None):
        """Record interaction with an article with flexible parameters"""
        interaction_data = {
            "article_id": article_id
        }
        
        interaction_desc = []
        
        if read is not None:
            interaction_data["read"] = read
            interaction_desc.append(f"read: {read}")
            
        if liked is not None:
            interaction_data["liked"] = liked
            interaction_desc.append(f"liked: {liked}")
            
        if read_time is not None:
            interaction_data["read_time"] = read_time
            interaction_desc.append(f"read_time: {read_time}")
            
        interaction_str = ", ".join(interaction_desc)
        self.log(f"Recording interaction with article ID: {article_id} ({interaction_str})...")
        
        response = requests.post(
            f"{API_BASE_URL}/articles/interaction",
            headers=self.headers,
            json=interaction_data
        )
        return self.handle_response(response, "Record article interaction") is not None

    def test_different_interactions(self, article_id):
        """Test different combinations of article interactions"""
        self.log(f"Testing different interaction combinations for article: {article_id}...")
        
        # All interactions will have liked=True, with different read/read_time settings
        # Read and like
        read_and_like_success = self.interact_with_article(article_id, read=True, liked=True, read_time=10)
        
        # Like only (default read=False)
        like_only_success = self.interact_with_article(article_id, liked=True)
        
        # Like with read_time
        like_with_time_success = self.interact_with_article(article_id, liked=True, read_time=10)
        
        # Like with all parameters
        all_params_success = self.interact_with_article(article_id, read=True, liked=True, read_time=10)
        
        return read_and_like_success and like_only_success and like_with_time_success and all_params_success

    def test_multiple_interactions(self, article_count=5):
        """Test interactions with multiple articles to observe embedding changes"""
        self.log(f"Testing interactions with multiple articles ({article_count})...")
        
        # Get a batch of recent articles
        articles = self.get_recent_articles(page=1, page_size=article_count)
        if not articles or len(articles) < 2:
            self.log(f"Not enough articles available for multiple interaction test. Need at least 2, found {len(articles) if articles else 0}", False)
            return False
            
        # Record number of articles we're actually going to interact with
        actual_count = min(len(articles), article_count)
        self.log(f"Will interact with {actual_count} articles")
        
        # Interact with each article with different interaction types
        success = True
        for i, article in enumerate(articles[:actual_count]):
            article_id = article["id"]
            # All interactions will have liked=True
            if i % 3 == 0:
                # Read and like
                interaction_success = self.interact_with_article(article_id, read=True, liked=True, read_time=10)
            elif i % 3 == 1:
                # Like only
                interaction_success = self.interact_with_article(article_id, liked=True)
            else:
                # Like with read_time
                interaction_success = self.interact_with_article(article_id, liked=True, read_time=10)
                
            if not interaction_success:
                self.log(f"Failed to interact with article {i+1}/{actual_count}", False)
                success = False
            else:
                self.log(f"Successfully interacted with article {i+1}/{actual_count}: {article.get('title', 'Unknown title')[:50]}...")
                
            # Small pause between interactions to simulate real user behavior
            time.sleep(0.5)
            
        # Get personalized feed again to see if recommendations changed
        self.log("Getting personalized feed after multiple interactions...")
        updated_feed = self.get_personalized_feed()
        
        if not updated_feed:
            self.log("No personalized articles after interactions - this might be concerning", False)
            
        return success

    def test_error_handling(self):
        """Test error handling in the API"""
        self.log("Testing API error handling...")
        
        # Test invalid article ID for interaction
        self.log("Testing interaction with invalid article ID...")
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{API_BASE_URL}/articles/interaction",
            headers=self.headers,
            json={
                "article_id": fake_id,
                "read": True
            }
        )
        
        if response.status_code == 404:
            self.log("Error handling for invalid article ID works correctly")
            error_handling_1 = True
        else:
            self.log(f"Unexpected response for invalid article ID: {response.status_code}", False)
            error_handling_1 = False
            
        # Test invalid article ID for retrieval
        self.log("Testing retrieval of invalid article ID...")
        response = requests.get(
            f"{API_BASE_URL}/articles/{fake_id}",
            headers=self.headers
        )
        
        if response.status_code == 404:
            self.log("Error handling for invalid article retrieval works correctly")
            error_handling_2 = True
        else:
            self.log(f"Unexpected response for invalid article retrieval: {response.status_code}", False)
            error_handling_2 = False
            
        return error_handling_1 and error_handling_2

    def get_article_details(self, article_id):
        """Get details for a specific article"""
        self.log(f"Fetching details for article ID: {article_id}...")
        response = requests.get(
            f"{API_BASE_URL}/articles/{article_id}",
            headers=self.headers
        )
        data = self.handle_response(response, "Get article details")
        if data:
            self.log(f"Retrieved article: {data.get('title', 'No title')}")
            # Print description field to verify it exists
            if "description" in data:
                self.log(f"Article has description field: {'Yes' if data.get('description') else 'No (null)'}")
            return data
        return None

    def get_urgent_articles(self):
        """Get urgent articles for notifications"""
        self.log("Fetching urgent articles...")
        response = requests.get(
            f"{API_BASE_URL}/articles/urgent/notifications",
            headers=self.headers
        )
        data = self.handle_response(response, "Get urgent articles")
        if data:
            self.log(f"Retrieved {len(data)} urgent articles")
            return data
        return []

    def run_tests(self):
        """Run all tests to verify backend functionality"""
        self.log("Starting backend API tests...", True)
        print("-" * 50)

        # Test authentication
        if not self.register_user():
            self.log("Registration failed, cannot continue", False)
            return
        
        if not self.login():
            self.log("Login failed, cannot continue", False)
            return
        
        if not self.get_user_profile():
            self.log("Failed to get user profile", False)
        
        print("-" * 50)
        
        # Test article feeds
        recent_articles = self.get_recent_articles()
        if not recent_articles:
            self.log("No recent articles found - this could be normal for a new system", False)
        
        # Test pagination
        pagination_working = self.test_pagination()
        
        # Test source filtering
        source_filtering_working = self.test_source_filtering()
        
        # Test personalized feed
        personalized_feed = self.get_personalized_feed()
        if not personalized_feed:
            self.log("No personalized articles found - this could be normal for a new user", False)
        
        # Test personalized feed with different exploration ratio
        exploration_feed = self.get_personalized_feed(exploration_ratio=0.4)
        if not exploration_feed:
            self.log("No exploration articles found - this could be normal for a new system", False)
        
        print("-" * 50)
        
        # Test search functionality
        search_working = False
        if recent_articles:
            # Extract a word from the first article title to use as search term
            search_term = recent_articles[0]["title"].split()[0]
            self.log(f"Using '{search_term}' as search term from article title")
            
            search_results = self.search_articles(search_term)
            if search_results:
                search_working = True
            else:
                self.log(f"No search results found for '{search_term}'", False)
            
            # Test advanced search options
            advanced_search_working = self.test_search_options()
            
            if len(search_term) >= 3:
                suggestions = self.get_search_suggestions(search_term[:3])
                if not suggestions:
                    self.log(f"No search suggestions found for '{search_term[:3]}'", False)
        else:
            # Try a generic search term
            self.log("No articles to extract search term from, using generic term")
            search_results = self.search_articles("news")
            if search_results:
                search_working = True
            suggestions = self.get_search_suggestions("ne")
        
        print("-" * 50)
        
        # Test article interactions
        article_for_interaction = None
        interactions_working = False
        different_interactions_working = False
        
        if recent_articles:
            article_for_interaction = recent_articles[0]["id"]
            if self.interact_with_article(article_for_interaction, read=True, liked=True, read_time=60):
                interactions_working = True
            else:
                self.log("Failed to record article interaction", False)
            
            # Test different interaction combinations
            different_interactions_working = self.test_different_interactions(article_for_interaction)
            
            article_details = self.get_article_details(article_for_interaction)
            if not article_details:
                self.log("Failed to get article details", False)
        else:
            self.log("No articles available for interaction testing", False)
        
        # Test multiple interactions
        multiple_interactions_working = self.test_multiple_interactions()
        
        print("-" * 50)
        
        # Test error handling
        error_handling_working = self.test_error_handling()
        
        # Test urgent articles
        urgent_articles = self.get_urgent_articles()
        if not urgent_articles:
            self.log("No urgent articles found - this could be normal", False)
        
        print("-" * 50)
        self.log("API tests completed", True)
        
        # Return overall status
        return {
            "auth_working": self.access_token is not None,
            "feeds_working": len(recent_articles) > 0 or len(personalized_feed) > 0,
            "pagination_working": pagination_working,
            "source_filtering_working": source_filtering_working,
            "search_working": search_working,
            "interaction_working": interactions_working,
            "different_interactions_working": different_interactions_working,
            "multiple_interactions_working": multiple_interactions_working,
            "error_handling_working": error_handling_working
        }

if __name__ == "__main__":
    tester = BackendTester()
    try:
        results = tester.run_tests()
        
        print("\n" + "=" * 50)
        print("BACKEND TEST RESULTS SUMMARY")
        print("=" * 50)
        
        if results is None:
            print("[FAILED] Tests did not complete successfully")
            print("-" * 50)
            print("[WARNING] Please check the server logs for more details")
            print("=" * 50)
            exit(1)
            
        all_working = True
        for feature, status in results.items():
            feature_name = feature.replace("_", " ").title()
            status_text = "Working" if status else "Not verified"
            if not status:
                all_working = False
            print(f"{feature_name}: {status_text}")
        
        print("-" * 50)
        if all_working:
            print("[SUCCESS] All tested features are working!")
            print("Your backend is ready for frontend development.")
        else:
            print("[WARNING] Some features could not be verified.")
            print("This might be normal for a fresh system with no data.")
            print("Consider adding some test data before proceeding.")
        
        print("=" * 50)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        print("Please restart the backend server and try again.")