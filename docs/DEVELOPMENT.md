# Development Guide

This document covers the deeper setup, migration, deployment, and
troubleshooting steps for SigmaLite. For a 5-minute getting-started guide,
see the top-level [`README.md`](../README.md).

## Local environment

### Prerequisites

| Tool      | Version | Notes                                                 |
| --------- | ------- | ----------------------------------------------------- |
| Node.js   | 18+     | For the Vite/React frontend                           |
| Python    | 3.11+   | For the FastAPI backend                               |
| SQLite    | bundled | Default local DB — no install required                |
| PostgreSQL | 14+    | Optional; recommended for production                  |
| Redis     | any     | Optional; used for caching when `REDIS_URL` is wired in |

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# At minimum, set SECRET_KEY to a random value. The default DATABASE_URL
# uses SQLite (sqlite:///./sigmalite.db) so no DB install is needed.

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                          # http://localhost:5173
```

Vite proxies `/api` and `/ws` to the backend at `localhost:8000`, so no CORS
config changes are needed for the default local ports. If you set
`VITE_API_URL` to a different origin, add that exact origin to
`ALLOWED_ORIGINS`.

## Switching to PostgreSQL

SQLite is great for local work but lacks the concurrency story you want in
production. To switch:

1. Provision a Postgres database (locally with `createdb sigmalite` or via a
   managed service).
2. Update `DATABASE_URL` in `backend/.env`:

   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/sigmalite
   ```

3. Re-run migrations:

   ```bash
   alembic upgrade head
   ```

The application code is database-agnostic; no other changes should be required.

## Database migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "Add foo to bar"

# Apply the latest migrations
alembic upgrade head

# Roll back the most recent migration
alembic downgrade -1
```

## Testing

### Backend

```bash
cd backend
uv run python -m pytest                  # runs the full suite
uv run python -m pytest --cov=app        # coverage
uv run python -m pytest tests/test_auth.py::test_login -x   # single test
```

The test suite spins up an in-memory SQLite database via fixtures in
`tests/conftest.py`; no external services are required. It includes a 10k-row
API smoke test for upload, pagination, filtering, aggregation, and chart
creation.

### Frontend

```bash
cd frontend
npm test                # vitest in watch mode
npx vitest run          # one-shot
npm run test:coverage   # coverage report
npm run build           # production build
npm run test:e2e        # Playwright product-loop smoke
```

The Playwright smoke starts its own backend on `127.0.0.1:8001` with an
isolated SQLite DB and its own Vite frontend on `127.0.0.1:5174`.

### Migration smoke

```bash
cd backend
DATABASE_URL=sqlite:///./migration_smoke.db SECRET_KEY=local-migration-secret alembic upgrade head
```

Expected tables after a fresh upgrade: `users`, `datasets`, `sheets`,
`charts`, `comments`, and `alembic_version`.

## Production deployment

### Backend (Render or similar)

1. Build command: `pip install -r requirements.txt`
2. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Required env vars:
   - `DATABASE_URL` — production Postgres URL
   - `SECRET_KEY` — long random string, at least 32 characters
   - `ALLOWED_ORIGINS` — comma-separated list of frontend origins
   - `DISABLE_AUTH=False` (or omit; the default is `False`)
4. Run `alembic upgrade head` as a release task on each deploy.

Production mode rejects weak/default `SECRET_KEY`, wildcard CORS, and
`DISABLE_AUTH=True`.

### Frontend (Vercel or similar)

```bash
cd frontend
npm run build           # outputs to dist/
```

Set `VITE_API_URL` to the production backend origin in the host's environment
settings, then deploy.

## Troubleshooting

### `DATABASE_URL` not set

Pydantic-settings will refuse to start if required vars are missing. Ensure
you've copied `.env.example` to `.env` and populated `DATABASE_URL` and
`SECRET_KEY`.

### Port already in use

```bash
lsof -ti:8000 | xargs kill -9     # backend
lsof -ti:5173 | xargs kill -9     # frontend
```

### Module not found

```bash
# backend
cd backend && pip install -r requirements.txt

# frontend
cd frontend && rm -rf node_modules package-lock.json && npm install
```

### CORS errors

The backend reads `ALLOWED_ORIGINS` as a comma-separated list. Make sure the
exact origin (scheme + host + port) of your frontend is included.

### bcrypt warnings

The project pins `bcrypt==4.0.1` to avoid passlib's newer bcrypt metadata
warning. If you upgrade bcrypt, re-run the auth tests and expect possible
cosmetic warning changes.

## Deployment smoke checklist

- `alembic upgrade head` succeeds against the production database.
- `/health` returns healthy.
- Register/login/refresh works with production `SECRET_KEY`.
- Upload a CSV and open the dataset page.
- Create a sheet, edit a cell, apply a filter, run an aggregation, save a chart.
- Add a comment and reload to confirm persistence.
- Confirm `/ws/collaborate/{sheet_id}` connects from the deployed frontend.
- Export CSV and verify formula-like values are neutralized.

## Tooling tips

- **API docs:** <http://localhost:8000/docs> (Swagger) and `/redoc`.
- **DB GUI:** any SQLite browser for local; pgAdmin/DBeaver/TablePlus for
  Postgres.
- **VS Code:** Pylance, ESLint, and Prettier are recommended.

## Sample CSV

If you don't have a dataset to upload:

```bash
cat > sample.csv <<'EOF'
name,age,city,salary,department
Alice,28,New York,75000,Engineering
Bob,35,San Francisco,95000,Engineering
Charlie,42,Chicago,68000,Sales
Diana,31,Boston,82000,Marketing
EOF
```

Upload `sample.csv` from the dashboard to exercise the full flow.
