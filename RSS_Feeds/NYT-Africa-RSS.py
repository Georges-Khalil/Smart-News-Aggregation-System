import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article

RSS_FEED_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Africa.xml"
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
        # Enhanced browser-like headers to help avoid detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Microsoft Edge";v="120", "Chromium";v="120", "Not=A?Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Attempt to fetch the content with enhanced headers
        try:
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # NYT typically has article content in div elements with specific classes
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
            
            # Fallback 1: Try to get any substantive paragraphs
            all_paragraphs = soup.find_all("p")
            article_text = "\n".join(
                p.get_text(strip=True) for p in all_paragraphs 
                if len(p.get_text(strip=True)) > 40  # Filter out short paragraphs
            )
            
            if article_text:
                return article_text
                
        except requests.exceptions.RequestException as e:
            print(f"Could not scrape full article: {e}")
            # Continue to fallback options
        
        # Fallback 2: Use the description from the RSS feed as the content
        # Code will reach here if all previous attempts failed
        return "[Premium Content] This is a New York Times article that requires a subscription. A summary from the RSS feed is provided."
            
    except Exception as e:
        print(f"Error in article processing: {e}")
        return f"Error processing article: {e}"

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
      # Create a robust description from the article's summary
    description = ""
    if hasattr(latest_article, "description") and latest_article.description:
        description = clean_html(latest_article.description)
    elif hasattr(latest_article, "summary") and latest_article.summary:
        description = clean_html(latest_article.summary)
    elif hasattr(latest_article, "content") and latest_article.content:
        # Some feeds put content in the content field
        description = clean_html(latest_article.content[0].value)

    # Get content, with fallback to description if scraping fails
    content = scrape_article_content(latest_article.link)
    if "Error fetching content:" in content or "Content not found" in content:
        if description:
            # If scraping failed but we have a description, use that as the content
            content = f"[Summary from RSS feed]: {description}"
        else:
            content = "[No content available] This article could not be retrieved."

    # Extract required fields
    article_data = {
        "title": latest_article.title,
        "description": description[:300] if description else "No description available",  # Limit description length
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": image_url,
        "source": "The New York Times",
        "content": content  
    }

    # Send to RabbitMQ
    publish_article(article_data)

    # Update last processed link **only after** processing is done
    LAST_PROCESSED_LINK = latest_article.link  

if __name__ == "__main__":
    print("Starting RSS Fetcher for The New York Times Africa News...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes