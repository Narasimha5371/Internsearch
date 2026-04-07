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
1) Optional: start Docker services (Postgres + Redis)
```
docker compose up -d
```

If you skip Docker, the backend now defaults to SQLite and in-memory Celery for local development.

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

If running without Docker, you can skip `alembic upgrade head`; SQLite schema is created automatically on startup.

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

If `CELERY_TASK_ALWAYS_EAGER=true` (default in local `.env`), queued tasks run in-process and this worker is optional.

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
- Clerk token validation requires `CLERK_JWKS_URL`, `CLERK_ISSUER`, and `CLERK_AUDIENCE`.
