import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article

RSS_FEED_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
LAST_PROCESSED_LINK = None

def fetch_rss_feed():
    """Fetch and parse the RSS feed."""
    return feedparser.parse(RSS_FEED_URL)

def clean_html(raw_html):
    """Removes HTML tags from text."""
    return BeautifulSoup(raw_html, "html.parser").get_text(strip=True)

def scrape_article_content(article_url):
    """Scrapes the full article content from New York Times."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # NYT typically has article content in div elements with specific classes
        # First try to find the main article body
        article_content = soup.find("section", class_="meteredContent")
        
        if not article_content:
            # Try alternative content sections
            content_candidates = [
                soup.find("div", class_="article-content"),
                soup.find("article", id="story"),
                soup.find("div", class_="StoryBodyCompanionColumn")
            ]
            
            for candidate in content_candidates:
                if candidate:
                    article_content = candidate
                    break

        if article_content:
            # Get all paragraphs from the article content
            paragraphs = article_content.find_all("p")
            article_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            
            if article_text:
                return article_text
        
        # Fallback method - try to get any substantive paragraphs
        all_paragraphs = soup.find_all("p")
        article_text = "\n".join(
            p.get_text(strip=True) for p in all_paragraphs 
            if len(p.get_text(strip=True)) > 40  # Filter out short paragraphs
        )
        
        return article_text if article_text else "Content not found"

    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {e}"
    except Exception as e:
        return f"Error parsing content: {e}"

def process_feed():
    """Fetches new articles and sends them to RabbitMQ."""
    global LAST_PROCESSED_LINK
    feed = fetch_rss_feed()

    if not feed.entries:
        print("No articles found in RSS feed.")
        return

    latest_article = feed.entries[0]  # The newest article in the feed

    if LAST_PROCESSED_LINK == latest_article.link:
        print("No new articles.")
        return

    # Extract image URL if available
    image_url = None
    if hasattr(latest_article, "media_content") and latest_article.media_content:
        image_url = latest_article.media_content[0]["url"]
    
    # Create description from the article's summary
    description = ""
    if hasattr(latest_article, "description"):
        description = clean_html(latest_article.description)
    elif hasattr(latest_article, "summary"):
        description = clean_html(latest_article.summary)

    # Extract required fields
    article_data = {
        "title": latest_article.title,
        "description": description,
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": image_url,
        "source": "The New York Times",
        "content": scrape_article_content(latest_article.link)  # Scrape and clean content
    }

    # Send to RabbitMQ
    publish_article(article_data)

    # Update last processed link **only after** processing is done
    LAST_PROCESSED_LINK = latest_article.link  

if __name__ == "__main__":
    print("Starting RSS Fetcher for The New York Times Technology News...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes