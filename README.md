# LabReport AI (PTUT-PRJ-058)

Educational web app that helps patients understand blood, lipid and urine lab reports and
prepare questions for their doctor. It does **not** diagnose or give treatment advice.

**Core design rule:** code decides low / normal / high; the AI only explains values already flagged.

## Technology
| Part | Language and tools |
|---|---|
| Web client | TypeScript, Next.js 14 (React), plain CSS |
| API server | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL on Supabase (SQLite for automated tests) |
| Security | bcrypt password hashes, signed JWT sessions |
| AI (later weeks) | Gemini API, PyMuPDF |
| Quality | pytest, ruff, GitHub Actions |

## Status
| Component | State |
|---|---|
| Rule engine, name normalizer, `/api/v1/analyze`, synthetic report generator | Done, tested |
| Users table + migration, register, login, logout, current user, admin guard | Done, tested (Week 5) |
| Web client: landing, register, login, dashboard | Done, builds and lints (Week 5) |
| Upload, extraction, explanations, checklist, admin pages, deployment | Planned (Weeks 6 to 11) |

## Run the API (Windows PowerShell or Command Prompt)
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
copy ..\.env.example .env        (then open backend\.env and fill in the real values)
alembic upgrade head              (creates the users table)
uvicorn app.main:app --reload     (API docs: http://127.0.0.1:8000/docs, database check: /health/db)
python -m pytest --cov=app        (tests)
ruff check .                      (lint)
```

## Run the web client
```
cd frontend
copy .env.local.example .env.local
npm install
npm run dev                       (http://localhost:3000)
```

## Data policy
No real patient data is used or committed. Test data is synthetic (`data/synthetic`).
Never commit `.env` or API keys.

Design documents: `docs/ARCHITECTURE.md` (decisions), `docs/AUTH.md` (authentication), `docs/diagrams/`.
