import requests
import json
import sys
from typing import Dict, List, Any, Optional
import time

# API configuration
BASE_URL = "http://localhost:8000"  # Update this if your server runs on a different URL
API_VERSION = "v1"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text: str, color: str):
    """Print colored text to the terminal"""
    print(f"{color}{text}{Colors.ENDC}")

def login(email: str, password: str) -> Optional[str]:
    """Login and return the access token"""
    login_url = f"{BASE_URL}/api/{API_VERSION}/auth/login"
    
    try:
        response = requests.post(
            login_url, 
            data={"username": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print_colored(f"Login failed: {response.status_code} - {response.text}", Colors.FAIL)
            return None
    except Exception as e:
        print_colored(f"Error during login: {e}", Colors.FAIL)
        return None

def get_recommendations(token: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """Get personalized recommendations with pagination"""
    rec_url = f"{BASE_URL}/api/{API_VERSION}/articles/feed"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    params = {
        "page": page,
        "page_size": page_size,
        "exploration_ratio": 0.2  # The default value in the API
    }
    
    try:
        print_colored(f"Requesting feed with params: {params}", Colors.CYAN)
        response = requests.get(rec_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print_colored(f"Failed to get recommendations: {response.status_code} - {response.text}", Colors.FAIL)
            return {}
    except Exception as e:
        print_colored(f"Error getting recommendations: {e}", Colors.FAIL)
        return {}

def get_recent_articles(token: Optional[str] = None, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """Get recent articles with pagination (for comparison)"""
    recent_url = f"{BASE_URL}/api/{API_VERSION}/articles/recent"
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    params = {
        "page": page,
        "page_size": page_size
    }
    
    try:
        print_colored(f"Requesting recent articles with params: {params}", Colors.CYAN)
        response = requests.get(recent_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print_colored(f"Failed to get recent articles: {response.status_code} - {response.text}", Colors.FAIL)
            return {}
    except Exception as e:
        print_colored(f"Error getting recent articles: {e}", Colors.FAIL)
        return {}

def print_article_summary(article: Dict[str, Any]):
    """Print a summary of an article"""
    title = article.get("title", "No title")
    source = article.get("source", "Unknown source")
    pub_date = article.get("pub_date", "Unknown date")
    
    print(f"- {title} [{source}] ({pub_date})")

def print_pagination_info(response: Dict[str, Any]):
    """Print pagination information from response"""
    if not response:
        return
        
    total = response.get("total", 0)
    page = response.get("page", 0)
    page_size = response.get("page_size", 0)
    total_pages = response.get("total_pages", 0)
    
    print_colored(f"\nPagination Information:", Colors.BOLD)
    print(f"Page {page} of {total_pages}")
    print(f"Showing {min(page_size, len(response.get('data', [])))} items (size: {page_size})")
    print(f"Total items: {total}")
    
    if page < total_pages:
        print_colored(f"There should be a next page (page {page + 1})", Colors.GREEN)
    else:
        print_colored(f"This is the last page", Colors.WARNING)

def test_pagination(email: str, password: str):
    """Test pagination for both recommendation feed and recent articles"""
    print_colored("Testing Feed Pagination", Colors.HEADER)
    
    # Login
    token = login(email, password)
    if not token:
        print_colored("Cannot proceed without authentication", Colors.FAIL)
        return
    
    print_colored("Successfully logged in", Colors.GREEN)
    
    # Test recommendation feed pagination
    print_colored("\n=== RECOMMENDATION FEED TEST ===", Colors.BOLD)
    
    # Get first page
    page_1 = get_recommendations(token, page=1, page_size=5)
    
    print_colored("\nFirst Page Results:", Colors.BOLD)
    if page_1 and "data" in page_1 and page_1["data"]:
        for article in page_1["data"]:
            print_article_summary(article)
        print_pagination_info(page_1)
    else:
        print_colored("No articles found in first page", Colors.WARNING)
    
    # Get second page
    print_colored("\nFetching second page...", Colors.CYAN)
    page_2 = get_recommendations(token, page=2, page_size=5)
    
    print_colored("\nSecond Page Results:", Colors.BOLD)
    if page_2 and "data" in page_2 and page_2["data"]:
        for article in page_2["data"]:
            print_article_summary(article)
        print_pagination_info(page_2)
        
        # Check for duplicates between pages
        page_1_ids = [article.get("id") for article in page_1.get("data", [])]
        page_2_ids = [article.get("id") for article in page_2.get("data", [])]
        
        duplicates = set(page_1_ids) & set(page_2_ids)
        if duplicates:
            print_colored(f"WARNING: Found {len(duplicates)} duplicate articles between pages!", Colors.FAIL)
            for dup_id in duplicates:
                print(f"Duplicate ID: {dup_id}")
        else:
            print_colored("No duplicates found between pages.", Colors.GREEN)
    else:
        print_colored("No articles found in second page", Colors.WARNING)
    
    # For comparison, test recent articles pagination
    print_colored("\n=== RECENT ARTICLES TEST (FOR COMPARISON) ===", Colors.BOLD)
    
    # Get first page of recent
    recent_1 = get_recent_articles(token, page=1, page_size=5)
    
    print_colored("\nRecent Articles - First Page:", Colors.BOLD)
    if recent_1 and "data" in recent_1 and recent_1["data"]:
        for article in recent_1["data"]:
            print_article_summary(article)
        print_pagination_info(recent_1)
    else:
        print_colored("No recent articles found in first page", Colors.WARNING)
    
    # Get second page of recent
    print_colored("\nFetching second page of recent articles...", Colors.CYAN)
    recent_2 = get_recent_articles(token, page=2, page_size=5)
    
    print_colored("\nRecent Articles - Second Page:", Colors.BOLD)
    if recent_2 and "data" in recent_2 and recent_2["data"]:
        for article in recent_2["data"]:
            print_article_summary(article)
        print_pagination_info(recent_2)
    else:
        print_colored("No recent articles found in second page", Colors.WARNING)

def print_usage():
    print("Usage: python test_recommendation_feed.py <email> <password>")
    print("Example: python test_recommendation_feed.py user@example.com mypassword")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
        
    email = sys.argv[1]
    password = sys.argv[2]
    
    test_pagination(email, password)