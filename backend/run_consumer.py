import sys
import os
import argparse
import time
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.rabbitmq_consumer import RabbitMQConsumer

def start_consumer(daemon_mode=False):
    """Start the RabbitMQ consumer process"""
    # Create DB session
    db = SessionLocal()
    
    try:
        # Initialize and start the consumer
        print("Initializing RabbitMQ consumer...")
        consumer = RabbitMQConsumer(db)
        
        if daemon_mode:
            # If running as a daemon, retry connection if it fails
            while True:
                try:
                    print("Starting consumer in daemon mode...")
                    sys.stdout.flush()  # Ensure output is flushed immediately
                    consumer.start_consuming()
                except Exception as e:
                    print(f"Consumer error: {e}")
                    print("Restarting consumer in 5 seconds...")
                    sys.stdout.flush()  # Ensure output is flushed immediately
                    time.sleep(5)
        else:
            # Single run mode
            consumer.start_consuming()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RabbitMQ Consumer for processed articles")
    parser.add_argument(
        "--daemon", 
        action="store_true", 
        help="Run in daemon mode (automatically restart on failure)"
    )
    
    args = parser.parse_args()
    
    print("Starting RabbitMQ consumer for processed articles...")
    sys.stdout.flush()  # Ensure output is flushed immediately
    start_consumer(daemon_mode=args.daemon)