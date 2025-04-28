# Smart News Aggregation System

A modern, AI-powered news aggregation system that collects articles from multiple sources, processes them using NLP to determine urgency and relevance, and delivers personalized news feeds to users through a TikTok/Twitter-like scrolling interface.

## System Architecture

The system is built as a decoupled, modular architecture with the following components:

### 1. RSS Feed Scrapers
- Located in `/RSS_Feeds/`
- Separate scripts for each news source (Guardian, FOX, Al Jazeera, LBC)
- Fetches articles periodically and pushes them to RabbitMQ's "news_queue"

### 2. NLP Processor
- Located in `/NLP-Embeddings.py`
- Consumes articles from "news_queue"
- Uses OpenAI's GPT-4o to assign urgency scores
- Creates embeddings using OpenAI's text-embedding-3-small model
- Sends processed articles to "processed_articles_queue"

### 3. Backend
- Located in `/backend/`
- FastAPI-based RESTful API
- PostgreSQL database with pgvector for vector similarity search
- Recommendation engine using cosine similarity between article embeddings and user preferences
- Authentication system with JWT tokens
- Push notification service for urgent news

### 4. Frontend
- Located in `/frontend/`
- Next.js-based React application
- TikTok/Twitter-like vertical scrolling feed
- Material UI for responsive, modern UI components
- Real-time notifications for urgent news
- User preference management

## Data Flow

1. RSS scrapers collect articles from news sources
2. Articles are sent to RabbitMQ "news_queue"
3. NLP processor consumes articles, analyzes them, and creates embeddings
4. Processed articles are sent to "processed_articles_queue"
5. Backend RabbitMQ consumer stores articles in PostgreSQL
6. Users access personalized news through the frontend
7. User interactions (likes, reads) update their preference embeddings
8. Recommendation engine provides increasingly relevant content

## Requirements

### Backend
- Python 3.8+
- PostgreSQL 14+ with pgvector extension
- RabbitMQ
- OpenAI API key

### Frontend
- Node.js 14+
- npm or yarn

## Installation

### 1. Set up environment variables
Create a `.env` file in the root directory with:

```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://username:password@localhost:5432/news_aggregator
RABBITMQ_HOST=localhost
SECRET_KEY=your_secret_key_for_jwt
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the database

```bash
cd backend
python init_db.py
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

## Running the System

### 1. Start RabbitMQ

Ensure RabbitMQ is running on your system.

### 2. Start the RSS scrapers

```bash
python RSS_Feeds/Guardian-RSS.py &
python RSS_Feeds/FOX-RSS.py &
python RSS_Feeds/Al-Jazeera-RSS.py &
python RSS_Feeds/LBC-RSS.py &
```

### 3. Start the NLP processor

```bash
python NLP-Embeddings.py
```

### 4. Start the backend

```bash
cd backend
python run_backend.py
```

### 5. Start the frontend

```bash
cd frontend
npm run dev
```

### 6. Access the application

Open your browser and navigate to `http://localhost:3000`

## Architecture Diagram

```
+------------+    +------------+    +------------+
| RSS        |    | RSS        |    | RSS        |
| Scraper 1  |--> | Scraper 2  |--> | Scraper N  |
+------------+    +------------+    +------------+
       |                |                |
       v                v                v
+------------------------------------------+
|             news_queue (RabbitMQ)        |
+------------------------------------------+
                     |
                     v
+------------------------------------------+
|           NLP Processor (GPT-4o)         |
|           + Embedding Generation         |
+------------------------------------------+
                     |
                     v
+------------------------------------------+
|     processed_articles_queue (RabbitMQ)  |
+------------------------------------------+
                     |
                     v
+------------------------------------------+
|        Backend (FastAPI + PostgreSQL)    |
|        + Recommendation Engine           |
+------------------------------------------+
                     |
                     v
+------------------------------------------+
|        Frontend (Next.js/React)          |
|        TikTok-style Scrolling Feed       |
+------------------------------------------+
```

## Features

- Real-time news collection from multiple sources
- AI-powered urgency scoring and content analysis
- Personalized news feeds based on user interactions
- Vector similarity search for content recommendations
- Push notifications for high-urgency news
- TikTok/Twitter-like vertical scrolling interface
- JWT-based authentication
- User preference management for sources and notification thresholds

## License

MIT License