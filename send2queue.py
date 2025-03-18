import pika
import json

def publish_article(article_data):
    """Send scraped article data to RabbitMQ queue."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
    channel = connection.channel()

    # Declare queue (ensures it exists)
    channel.queue_declare(queue="news_queue", durable=True)

    # Convert article dictionary to JSON
    message = json.dumps(article_data)

    # Publish article to RabbitMQ queue
    channel.basic_publish(
        exchange="",
        routing_key="news_queue",
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)  # Makes message persistent
    )

    print(f"Sent article: {article_data['title']}")
    connection.close()

def publish_processed_article(processed_article_data):
    """Send processed article data to a new RabbitMQ queue."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
    channel = connection.channel()

    # Declare new queue (ensures it exists)
    channel.queue_declare(queue="processed_articles_queue", durable=True)

    # Convert processed article dictionary to JSON
    message = json.dumps(processed_article_data)

    # Publish processed article to RabbitMQ queue
    channel.basic_publish(
        exchange="",
        routing_key="processed_articles_queue",
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)  # Makes message persistent
    )

    connection.close()
