import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article  # Updated import statement

RSS_FEED_URL = "https://www.aljazeera.com/xml/rss/all.xml"
LAST_PROCESSED_LINKS = []

def fetch_rss_feed():
    """Fetch and parse the RSS feed."""
    return feedparser.parse(RSS_FEED_URL)

def scrape_article_content(article_url):
    """Scrapes the full article content from Al Jazeera articles."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Try finding the main content using multiple possible class names
        possible_classes = ["wysiwyg wysiwyg--all-content", "gallery wysiwyg wysiwyg--all-content"]
        article_body = None

        for class_name in possible_classes:
            article_body = soup.find("div", class_=class_name)
            if article_body:
                break  # Stop if we find a match

        if article_body:
            paragraphs = article_body.find_all("p")
            article_text = "\n".join(p.get_text(strip=True) for p in paragraphs)
            return article_text if article_text else None  # Return None if text is empty
        
        return None  # Return None if no valid content is found

    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content: {e}")
        return None  # Return None on failure

def process_feed():
    """Fetches new articles and sends them to RabbitMQ if content is found."""
    global LAST_PROCESSED_LINKS
    feed = fetch_rss_feed()

    if not feed.entries:
        print("No articles found in RSS feed.")
        return

    latest_article = feed.entries[0]

    if latest_article.link in LAST_PROCESSED_LINKS:
        print("No new articles.")
        return

    # Scrape article content
    article_content = scrape_article_content(latest_article.link)
    if not article_content:
        print(f"Skipping article (No content found): {latest_article.title}")
        return  # Skip this article

    article_data = {
        "title": latest_article.title,
        "description": BeautifulSoup(latest_article.description, "html.parser").get_text(strip=True),  # Clean HTML tags
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": latest_article.media_content[0]["url"] if hasattr(latest_article, "media_content") else "No Image",
        "source": "Al Jazeera",
        "content": article_content
    }

    # Send to RabbitMQ
    publish_article(article_data)

    # Update the list of processed links
    LAST_PROCESSED_LINKS.append(latest_article.link)
    if len(LAST_PROCESSED_LINKS) > 2:
        LAST_PROCESSED_LINKS.pop(0)  # Keep only the last two links

if __name__ == "__main__":
    print("Starting Al Jazeera RSS Fetcher...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes


