import pika
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
from send2queue import publish_processed_article

# Load environment variables from .env file
load_dotenv()

# Establish connection to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
channel = connection.channel()

# Declare the same queue
channel.queue_declare(queue="news_queue", durable=True)

# Initialize OpenAI API
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # Use environment variable

def clean_text(text):
    """Clean the input text by removing HTML tags."""
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    return text

def truncate_text(text, max_length=512):
    """Truncate the text to the maximum number of tokens."""
    words = text.split()
    if len(words) > max_length:
        return ' '.join(words[:max_length])
    return text

def assign_urgency_score(text):
    """Assign an urgency score to the text using OpenAI's GPT-4o API."""
    truncated_text = truncate_text(text)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Rate the urgency of the following news article on a scale of 1 to 10, considering its importance as well, but with a heavier weight on urgency:\n\n{truncated_text}\n\nPlease respond with just a number indicating the urgency level:"}
        ],
        max_tokens=2,
        temperature=0.5,
    )
    score = response.choices[0].message.content.strip()
    try:
        score = int(score)
    except ValueError:
        score = -1  # Default to -1 score if parsing fails

    return score

def create_embedding(text):
    """Create an embedding for the text using OpenAI's API."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    embedding = response.data[0].embedding
    return embedding

def callback(ch, method, properties, body):
    """Process and print messages in a structured format."""
    article = json.loads(body)

    # Clean the article content
    cleaned_content = clean_text(article['content'])

    # Assign an urgency score
    urgency_score = assign_urgency_score(cleaned_content)

    # Create an embedding for the article
    try:
        embedding = create_embedding(cleaned_content)
        embedding_status = "Embedding created successfully"
    except Exception as e:
        embedding = None
        embedding_status = f"Failed to create embedding: {e}"

    # Prepare processed article data
    processed_article_data = {
        "title": article['title'],
        "pub_date": article['pub_date'],
        "link": article['link'],
        "image": article['image'],
        "source": article['source'],
        "urgency_score": urgency_score,
        "embedding": embedding,
        "content": cleaned_content
    }

    # Send processed article to RabbitMQ
    publish_processed_article(processed_article_data)

    print("\n===== New Article Processed =====")
    print(f"Title: {article['title']}")
    print(f"Urgency Score: {urgency_score}/10")
    print(f"Embedding Status: {embedding_status}")
    print("=" * 50)  # Separator line

    ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge message

channel.basic_consume(queue="news_queue", on_message_callback=callback)

print("Waiting for messages. Press CTRL+C to exit.")
channel.start_consuming()