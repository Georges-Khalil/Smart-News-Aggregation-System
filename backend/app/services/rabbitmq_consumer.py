import json
import pika
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import sys

from ..core.config import settings
from ..models.models import Article
from ..models.schemas import ArticleCreate

class RabbitMQConsumer:
    """Service to consume processed articles from RabbitMQ and store them in the database."""
    
    def __init__(self, db: Session):
        self.db = db
        self.connection = None
        self.channel = None
        self.queue_name = "processed_articles_queue"  # Use the exact same queue name as in Temp-Backend.py
        print(f"RabbitMQ Consumer initialized with queue: {self.queue_name}")
        sys.stdout.flush()
        
    async def setup(self):
        """Set up the RabbitMQ connection and channel."""
        try:
            # Use the exact same connection parameters as Temp-Backend.py
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
            self.channel = self.connection.channel()
            
            # Declare the queue with the same parameters
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            print(f"[CONSUMER] Connected to RabbitMQ at localhost and declared queue: {self.queue_name}")
            print(f"[CONSUMER] Waiting for messages on queue: {self.queue_name}...")
            sys.stdout.flush()
            return True
        except Exception as e:
            print(f"[CONSUMER] Error connecting to RabbitMQ: {e}")
            sys.stdout.flush()
            return False
    
    def close(self):
        """Close the RabbitMQ connection."""
        if self.connection:
            self.connection.close()
            print("[CONSUMER] RabbitMQ connection closed")
            sys.stdout.flush()
            
    def callback(self, ch, method, properties, body):
        """Process the message from RabbitMQ and store it in the database."""
        try:
            # Parse the message body as JSON
            article_data = json.loads(body)
            
            # Print message in format similar to Temp-Backend.py for consistency
            print("\n===== Processed Article Received =====")
            print(f"Title: {article_data['title']}")
            print(f"Source: {article_data['source']}")
            print(f"Urgency Score: {article_data['urgency_score']}/10")
            embedding_present = "Yes" if article_data['embedding'] else "No"
            print(f"Embedding Present: {embedding_present}")
            sys.stdout.flush()
            
            # Check if article already exists in the database (by link)
            existing_article = self.db.query(Article).filter(Article.link == article_data['link']).first()
            
            if existing_article:
                print(f"[CONSUMER] Article already exists in database: {article_data['title']}")
                sys.stdout.flush()
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Convert pub_date string to datetime object if needed
            if isinstance(article_data['pub_date'], str):
                try:
                    # Try multiple date formats
                    date_formats = [
                        # ISO format
                        "%Y-%m-%dT%H:%M:%S.%fZ", 
                        "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S",
                        # Common RSS date formats
                        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 format
                        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
                        "%a, %d %b %Y %H:%M:%S",     # RFC 822 without timezone
                        "%d %b %Y %H:%M:%S",         # Without weekday
                        "%d %b %Y",                  # Just day, month, year
                        "%B %d, %Y",                 # Month name, day, year
                        "%Y-%m-%d"                   # Just the date
                    ]
                    
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            if fmt.endswith("%z") or fmt.endswith("%Z"):
                                parsed_date = datetime.strptime(article_data['pub_date'], fmt)
                            else:
                                # For formats without timezone, assume UTC
                                parsed_date = datetime.strptime(article_data['pub_date'], fmt)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date:
                        article_data['pub_date'] = parsed_date
                    else:
                        raise ValueError("None of the date formats matched")
                        
                except (ValueError, TypeError):
                    print(f"[CONSUMER] Invalid pub_date format for article: {article_data['title']}. Using current time.")
                    print(f"[CONSUMER] The date string was: {article_data['pub_date']}")
                    sys.stdout.flush()
                    article_data['pub_date'] = datetime.utcnow()
            
            # Create new article
            new_article = Article(
                title=article_data['title'],
                link=article_data['link'],
                description=article_data.get('description', ''),  # Use .get() with default empty string
                content=article_data['content'],
                pub_date=article_data['pub_date'],
                image=article_data.get('image'),
                source=article_data['source'],
                urgency_score=article_data['urgency_score'],
                embedding=article_data['embedding']
            )
            
            # Add to database and commit
            self.db.add(new_article)
            self.db.commit()
            
            print(f"[CONSUMER] Successfully stored new article in database: {new_article.title}")
            print(f"[CONSUMER] Article stored in PostgreSQL database")
            print("=" * 50)  # Separator line
            sys.stdout.flush()
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"[CONSUMER] Error processing article: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            # Acknowledge the message even if there was an error
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def start_consuming(self):
        """Start consuming messages from the queue."""
        if not self.channel:
            print("[CONSUMER] Setting up RabbitMQ connection...")
            sys.stdout.flush()
            success = asyncio.run(self.setup())
            if not success:
                print("[CONSUMER] Failed to set up RabbitMQ connection. Consumer not started.")
                sys.stdout.flush()
                return
        
        # Set up consumer prefetch (quality of service)
        self.channel.basic_qos(prefetch_count=1)
        
        # Start consuming from the queue
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self.callback
        )
        
        print(f"[CONSUMER] Waiting for messages. Press CTRL+C to exit.")
        sys.stdout.flush()
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("[CONSUMER] Stopping consumer...")
            sys.stdout.flush()
            self.channel.stop_consuming()
        except Exception as e:
            print(f"[CONSUMER] Error in consumer: {e}")
            sys.stdout.flush()
        finally:
            self.close()