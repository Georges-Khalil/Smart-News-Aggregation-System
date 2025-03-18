import pika
import json

# Establish connection to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

# Declare the new queue
channel.queue_declare(queue="processed_articles_queue", durable=True)

def callback(ch, method, properties, body):
    """Process and print messages in a structured format."""
    processed_article = json.loads(body)

    embedding_present = "Yes" if processed_article['embedding'] else "No"

    print("\n===== Processed Article Received =====")
    print(f"Title: {processed_article['title']}")
    print(f"Date: {processed_article['pub_date']}")
    print(f"Link: {processed_article['link']}")
    print(f"Image: {processed_article['image']}")
    print(f"Source: {processed_article['source']}")
    print(f"Urgency Score: {processed_article['urgency_score']}/10")
    print(f"Embedding Present: {embedding_present}")
    print("\nContent:\n" + processed_article['content'])
    print("=" * 50)  # Separator line

    ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge message

channel.basic_consume(queue="processed_articles_queue", on_message_callback=callback)

print("Waiting for messages. Press CTRL+C to exit.")
channel.start_consuming()