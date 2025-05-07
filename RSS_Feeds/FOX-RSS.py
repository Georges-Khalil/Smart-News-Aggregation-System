import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article  # Updated import statement

RSS_FEED_URL = "https://moxie.foxnews.com/google-publisher/latest.xml"
LAST_PROCESSED_LINK = None

def fetch_rss_feed():
    """Fetch and parse the RSS feed."""
    return feedparser.parse(RSS_FEED_URL)

def clean_html(raw_html):
    """Removes HTML tags from text."""
    return BeautifulSoup(raw_html, "html.parser").get_text(strip=True)

def scrape_article_content(article_url):
    """Scrapes the full article content from Fox News."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the article content inside the correct div
        content_div = soup.find("div", class_="article-body")

        if not content_div:
            return "Content not found"

        # Extract text from all <p> tags inside the content div
        paragraphs = content_div.find_all("p")
        article_text = "\n".join(p.get_text(strip=True) for p in paragraphs)

        return clean_html(article_text) if article_text else "Content not found"

    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {e}"

def process_feed():
    """Fetches new articles and sends them to RabbitMQ."""
    global LAST_PROCESSED_LINK
    feed = fetch_rss_feed()

    if not feed.entries:
        print("No articles found in RSS feed.")
        return

    latest_article = feed.entries[0]  # The newest article

    if LAST_PROCESSED_LINK == latest_article.link:
        print("No new articles.")
        return

    article_data = {
        "title": latest_article.title,
        "description": clean_html(latest_article.description),  # Clean description
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": latest_article.media_content[0]["url"] if hasattr(latest_article, "media_content") else None,
        "source": "Fox News",
        "content": scrape_article_content(latest_article.link)  # Scrape and clean content
    }

    # Send to RabbitMQ
    publish_article(article_data)

    # Update last processed link **only after** processing is done
    LAST_PROCESSED_LINK = latest_article.link  

if __name__ == "__main__":
    print("Starting Fox News RSS Fetcher...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes
