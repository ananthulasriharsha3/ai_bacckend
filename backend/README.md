# Topics Q&A Backend

Production-ready backend that generates interview questions and answers for topics using **FastAPI**, **Supabase (PostgreSQL)**, and **OpenAI**, and exposes APIs for the UI.

## Features

- **Create topic** – POST a topic, generate 8–10 Q&A via GPT, store in DB
- **List topics** – GET all topics
- **Get Q&A by topic** – GET all questions and answers for a topic
- **Bulk upload** – POST a list of topics; each is processed in the background (create topic, generate Q&A, store)
- **Rate limiting** – Semaphore limits concurrent OpenAI requests
- **Structured logging** – JSON-friendly log format
- **Error handling** – OpenAI failures, DB errors, invalid input

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy (async with asyncpg)
- Supabase (PostgreSQL)
- OpenAI API
- Pydantic
- python-dotenv

## Setup

### 1. Clone and enter project

```bash
cd backend
```

### 2. Create virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/macOS
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Copy the example env file and set your values:

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Edit `.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string. Use async driver: `postgresql+asyncpg://user:password@host:port/database` or `postgresql://...` (app will convert to async). From Supabase: Project Settings → Database → Connection string (URI). |
| `OPENAI_API_KEY` | Your OpenAI API key. |
| `OPENAI_MAX_CONCURRENT` | (Optional) Max concurrent OpenAI requests. Default: `5`. |

Example:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxx.supabase.co:5432/postgres
OPENAI_API_KEY=sk-your-key
OPENAI_MAX_CONCURRENT=5
```

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`.

- **Docs:** http://127.0.0.1:8000/docs  
- **Health:** http://127.0.0.1:8000/health  

## API Reference

### Create topic (single)

**POST** `/topics`

Request:

```json
{
  "topic_name": "Machine Learning"
}
```

Creates the topic, calls OpenAI to generate 8–10 Q&A, stores topic and questions. Returns the created topic.

### List topics

**GET** `/topics`

Returns all topics.

### Get Q&A for a topic

**GET** `/topics/{topic_id}/qa`

Returns the topic and all its questions and answers.

### Bulk topic upload

**POST** `/topics/bulk`

Request:

```json
{
  "topics": ["Python", "Machine Learning", "FastAPI"]
}
```

Starts background processing: for each topic, creates the topic, generates Q&A via OpenAI, and stores them. Response is immediate; processing continues in the background.

For **1900+ topics**, consider splitting into smaller batches (e.g. 50–100 per request) to avoid long-running background tasks and to improve observability.

## Database schema

- **topics** – `id` (uuid), `topic_name` (text), `created_at` (timestamp)
- **questions** – `id` (uuid), `topic_id` (fk → topics.id), `question` (text), `answer` (text), `created_at` (timestamp)

Tables are created automatically on startup if they do not exist.

## Project structure

```
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   ├── openai_service.py
│   │   └── topic_service.py
│   └── routes/
│       ├── topic_routes.py
│       └── qa_routes.py
├── requirements.txt
├── .env.example
└── README.md
```

## Scaling for 1900+ topics

- **Bulk endpoint** – Processes topics sequentially in one background task. Use multiple bulk requests with smaller batches (e.g. 50 topics each) for better control and resilience.
- **Rate limiting** – `OPENAI_MAX_CONCURRENT` limits concurrent OpenAI calls; single-topic and bulk flows respect this.
- **Database** – Connection pool is configured in `database.py` (`pool_size`, `max_overflow`). Adjust for your Supabase plan.
- For very large runs, consider a job queue (e.g. Celery, ARQ) and worker processes instead of in-process background tasks.
