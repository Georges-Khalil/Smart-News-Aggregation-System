import feedparser
import requests
import time
from bs4 import BeautifulSoup
import sys
import os
import re

# Add the parent directory to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from send2queue import publish_article  # Updated import statement

# Guardian RSS Feed URL
RSS_FEED_URL = "https://www.theguardian.com/world/middleeast/rss"
LAST_PROCESSED_LINK = None  # Keeps track of the last seen article

def fetch_rss_feed():
    """Fetch and parse the RSS feed."""
    return feedparser.parse(RSS_FEED_URL)

def clean_html(raw_html):
    """Removes HTML tags from text."""
    return BeautifulSoup(raw_html, "html.parser").get_text(strip=True)

def scrape_article_content(article_url):
    """Scrapes the full article content from a Guardian article."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract the article content
        article_paragraphs = []
        
        # Method 1: Look for article content div with specific class names
        content_classes = [
            "dcr-11jq3zt",               # Primary class from example
            "article-body-commercial-selector",  # Original class
            "dcr-1uvtuj9",               # Alternative container
            "dcr-1a4fred",               # Another container seen in example
        ]
        
        article_div = None
        for class_name in content_classes:
            article_div = soup.find("div", class_=class_name)
            if article_div:
                break
        
        if article_div:
            # First try with the specific paragraph class
            paragraphs = article_div.find_all("p", class_="dcr-16w5gq9")
            
            # If no specific class paragraphs found, try all paragraphs in the div
            if not paragraphs:
                paragraphs = article_div.find_all("p")
                
            # Extract text from all paragraphs
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # Skip very short paragraphs like single characters
                    article_paragraphs.append(text)
        
        # Method 2: Try alternative approach if no content found
        if not article_paragraphs:
            # Look for the main article element
            article_element = soup.find("article") or soup.find("main")
            if article_element:
                paragraphs = article_element.find_all("p")
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        article_paragraphs.append(text)
        
        # Method 3: As a fallback, look for any substantial paragraphs 
        if not article_paragraphs:
            # Sometimes the article is spread across multiple containers
            all_paragraphs = soup.find_all("p")
            # Filter likely content paragraphs (longer than 40 chars to filter navigation items)
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 40:
                    article_paragraphs.append(text)
        
        # Method 4: For articles behind paywalls or sign-in walls, try to extract using metadata
        if not article_paragraphs:
            # Check for JSON-LD structured data that might contain the article content
            script_tags = soup.find_all("script", {"type": "application/ld+json"})
            for script in script_tags:
                if script.string:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get("articleBody"):
                            # Extract article body from JSON-LD
                            article_body = data.get("articleBody")
                            # Split by paragraphs if it's a single string
                            if isinstance(article_body, str):
                                for para in re.split(r'\n+', article_body):
                                    if para.strip():
                                        article_paragraphs.append(para.strip())
                    except:
                        pass
        
        # Join all paragraphs into one text with proper spacing
        article_text = "\n\n".join(article_paragraphs)
        
        # Debug information
        if not article_text:
            print(f"Warning: No content found for {article_url}")
            return "Content not found"
        
        return article_text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching content: {e}")
        return f"Error fetching content: {e}"
    except Exception as e:
        print(f"Error parsing content: {e}")
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

    # Extract required fields
    article_data = {
        "title": latest_article.title,
        "description": clean_html(latest_article.description),  # Clean description
        "link": latest_article.link,
        "pub_date": latest_article.published,
        "image": latest_article.media_content[0]["url"] if hasattr(latest_article, "media_content") else "No Image",
        "source": "The Guardian",
        "content": scrape_article_content(latest_article.link)  # Scrape and clean content
    }

    # Send to RabbitMQ
    publish_article(article_data)

    # Update last processed link **only after** processing is done
    LAST_PROCESSED_LINK = latest_article.link  

if __name__ == "__main__":
    print("Starting RSS Fetcher for The Guardian...\n")
    while True:
        process_feed()
        time.sleep(150)  # Check every 2.5 minutes
