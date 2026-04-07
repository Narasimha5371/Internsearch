<<<<<<< HEAD
# Autonomous Job Application Agent

A greenfield FastAPI + Next.js stack for parsing resumes, aggregating internships, matching candidates, and automating ATS applications with a human-in-the-loop option.

## Structure
- backend: FastAPI API, SQLAlchemy models, background workers
- frontend: Next.js app with Clerk authentication and dashboard UI
- shared: JSON schemas that act as data contracts
- infra: Local dev infra via Docker Compose

## Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop

## Quick start (local)
1) Start databases
```
docker compose up -d
```

2) Backend
```
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

3) Frontend
```
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

4) Worker (background tasks)
```
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

5) Smoke test
```
cd backend
python app/scripts/smoke_test.py
```

## Usage
- Profile editor: http://localhost:3000/profile
- Dashboard: http://localhost:3000/dashboard (scrape + queue + match)

## Notes
- The LLM adapter defaults to local inference (Ollama) with an optional Groq fallback.
- This is a prototype intended for local use and testing.
=======
# Internsearch
>>>>>>> 22fce51a310c682b82f0769ad2231077c04038b8
