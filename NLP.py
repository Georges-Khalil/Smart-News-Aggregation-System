import pika
import json
import re
from transformers import pipeline

# Establish connection to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

# Declare the same queue
channel.queue_declare(queue="news_queue", durable=True)

# Initialize the transformers pipeline for text classification
classifier = pipeline("text-classification", model="bert-base-uncased")

def clean_text(text):
    """Clean the input text by removing HTML tags."""
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    return text

def truncate_text(text, max_length=512):
    """Truncate the text to the maximum sequence length."""
    return text[:max_length]

def assign_urgency_score(text):
    """Assign an urgency score to the text using a pre-trained classifier."""
    truncated_text = truncate_text(text)
    result = classifier(truncated_text)[0]
    score = int(result['score'] * 10)  # Convert the score to a scale of 1 to 10
    return score

def callback(ch, method, properties, body):
    """Process and print messages in a structured format."""
    article = json.loads(body)

    # Clean the article content
    cleaned_content = clean_text(article['content'])

    # Assign an urgency score
    urgency_score = assign_urgency_score(cleaned_content)

    print("\n===== New Article Received =====")
    print(f"Title: {article['title']}")
    print(f"Date: {article['pub_date']}")
    print(f"Link: {article['link']}")
    print(f"Image: {article['image']}")
    print(f"Source: {article['source']}")
    print(f"Urgency Score: {urgency_score}/10")
    print("\nContent:\n" + cleaned_content)
    print("=" * 50)  # Separator line

    ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge message

channel.basic_consume(queue="news_queue", on_message_callback=callback)

print("Waiting for messages. Press CTRL+C to exit.")
channel.start_consuming()