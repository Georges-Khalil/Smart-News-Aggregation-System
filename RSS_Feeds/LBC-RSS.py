import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article  # Updated import statement

RSS_FEED_URL = "https://www.lbcgroup.tv/Rss/latest-news/en"
LAST_PROCESSED_LINK = None

def fetch_rss_feed():
    """Fetch and parse the RSS feed."""
    return feedparser.parse(RSS_FEED_URL)

def scrape_article_content(article_url):
    """Scrapes the full article content from the given URL."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        article_body = soup.find("div", class_="LongDesc")
        return article_body.get_text(separator="\n", strip=True) if article_body else "Content not found"

    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {e}"

def process_feed():
    """Fetches new articles and sends them to RabbitMQ."""
    global LAST_PROCESSED_LINK
    feed = fetch_rss_feed()

    if not feed.entries:
        print("No articles found in RSS feed.")
        return

    latest_article = feed.entries[0]

    if LAST_PROCESSED_LINK == latest_article.link:
        print("No new articles.")
        return

    article_data = {
        "title": latest_article.title,
        "description": latest_article.description,
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": latest_article.media_content[0]["url"] if hasattr(latest_article, "media_content") else "No Image",
        "source": "LBCI",
        "content": scrape_article_content(latest_article.link)
    }

    # Send to RabbitMQ
    publish_article(article_data)

    LAST_PROCESSED_LINK = latest_article.link  

if __name__ == "__main__":
    print("Starting LBC RSS Fetcher...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes
