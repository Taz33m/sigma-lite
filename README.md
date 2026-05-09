# SigmaLite

Collaborative spreadsheet-style data exploration for CSV datasets.

SigmaLite combines a FastAPI backend with a React/MUI frontend to provide
dataset upload, grid editing, filtering, aggregate formulas, charts, comments,
and realtime collaboration signals in a small, inspectable codebase.

![Status](https://img.shields.io/badge/status-beta_candidate-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-646CFF)

## Why SigmaLite Exists

Most teams eventually need a lightweight place to inspect tabular data, save a
view, chart the result, and discuss the numbers. SigmaLite is a focused
open-source implementation of that workflow:

- Upload a CSV.
- Explore rows in a paginated, editable grid.
- Apply filters and aggregate calculations.
- Save sheets and charts.
- Add comments to a sheet or a selected cell.
- Collaborate through WebSocket presence and cursor activity.

It is intentionally smaller than a BI platform and more structured than a raw
spreadsheet.

## Project Status

SigmaLite is an MVP-plus beta candidate. The core product loop is implemented
and covered by backend tests, frontend tests, production build, migration smoke,
and Playwright E2E.

Current beta limits:

- Cell edits are last-write-wins.
- Dataset rows are still backed by CSV files.
- Formulas are aggregate-focused, not a full spreadsheet calculation engine.
- CSV export covers the current grid page.
- Rate limiting is in-process and should be paired with platform/WAF controls.
- Collaboration covers presence, cursors, and comments, not full sharing roles.

See [`PRD_COMPLIANCE.md`](PRD_COMPLIANCE.md) for the current feature matrix.

## Features

| Area | Capability |
| --- | --- |
| Authentication | Register, login, refresh tokens, current-user profile, JWT isolation |
| Datasets | CSV upload, safe stored filenames, schema inference, pagination |
| Grid | MUI Data Grid, editable cells, persisted updates, comment markers |
| Filters | Visual filter builder backed by validated API filters |
| Formulas | `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `MEDIAN` over columns and A1 ranges |
| Charts | Bar, line, scatter, pie charts with saved configs and PNG export |
| Collaboration | WebSocket presence, cursor activity, persisted comments |
| Export | CSV export with spreadsheet-formula injection neutralization |
| Operations | Alembic migrations, production config guards, CI, E2E smoke |

## Architecture

```text
frontend/ React + TypeScript + Vite + MUI + Chart.js
    |
    | REST API + WebSocket
    v
backend/ FastAPI + SQLAlchemy + Alembic + Pydantic + pandas
    |
    | local: SQLite + CSV upload directory
    | prod: PostgreSQL recommended + durable upload storage
    v
database / uploaded dataset files
```

The backend owns data validation, schema inference, filters, aggregation, cell
updates, comments, charts, and authentication. The frontend owns the workspace
experience, grid editing, chart rendering, export UX, and realtime UI state.

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 22 recommended for CI parity; Node 20+ should work locally
- npm
- SQLite, bundled with Python

PostgreSQL is recommended for production but not required for local
development.

### 1. Start The Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit SECRET_KEY before exposing the server beyond local development.

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Health: <http://localhost:8000/health>

### 2. Start The Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>, register an account, and upload a CSV.

### 3. Try A Formula

After creating a sheet, edit a numeric cell with one of:

```text
=SUM(age)
=AVG(B:B)
=COUNT(A1:A5)
```

The backend evaluates supported aggregate formulas and persists the result to
the CSV backing file.

## Verification

Run the same checks expected before opening a PR:

```bash
# Backend
cd backend
uv run python -m pytest -q

# Fresh migration smoke
rm -f migration_smoke.db
DATABASE_URL=sqlite:///./migration_smoke.db \
  SECRET_KEY=migration-smoke-secret-with-enough-entropy \
  uv run alembic upgrade head

# Frontend
cd ../frontend
npm test -- --run
npm run build
npm run test:e2e -- --project=chromium
npm audit --omit=dev --audit-level=high
```

The Playwright E2E test starts an isolated backend on `127.0.0.1:8001` and a
Vite frontend on `127.0.0.1:5174`.

## API Surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Service health |
| `/api/auth/register` | POST | Create user |
| `/api/auth/login` | POST | Issue access and refresh tokens |
| `/api/auth/refresh` | POST | Rotate tokens |
| `/api/auth/me` | GET | Current user profile |
| `/api/datasets` | GET, POST | List or upload datasets |
| `/api/datasets/{id}` | GET, PUT, DELETE | Dataset metadata |
| `/api/datasets/{id}/data` | GET | Paginated rows |
| `/api/datasets/{id}/filter` | POST | Filter rows |
| `/api/datasets/{id}/aggregate` | POST | Aggregate a column |
| `/api/datasets/{id}/cell` | PATCH | Persist one cell update |
| `/api/sheets` | GET, POST | List or create sheets |
| `/api/sheets/{id}` | GET, PUT, DELETE | Sheet metadata/config |
| `/api/sheets/{id}/comments` | GET, POST | Sheet/cell comments |
| `/api/charts` | GET, POST | List or create charts |
| `/api/charts/{id}` | GET, PUT, DELETE | Chart metadata/config |
| `/ws/collaborate/{sheet_id}` | WS | Realtime presence and activity |

## Configuration

Backend configuration lives in `backend/.env`.

Required for any non-local deployment:

```env
DATABASE_URL=postgresql://user:password@host:5432/sigmalite
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_ORIGINS=https://your-frontend.example
DISABLE_AUTH=False
ENVIRONMENT=production
```

Frontend configuration lives in `frontend/.env`.

```env
VITE_API_URL=http://localhost:8000
VITE_DISABLE_AUTH=false
```

`DISABLE_AUTH=True` is only for local demos. Production mode rejects disabled
auth, weak secrets, and wildcard CORS.

## Repository Layout

```text
.
|-- backend/                 FastAPI app, Alembic migrations, pytest suite
|-- frontend/                React/Vite app, Vitest tests, Playwright E2E
|-- docs/                    Architecture, development, roadmap, PRD docs
|-- .github/workflows/       CI
|-- .github/ISSUE_TEMPLATE/  Issue forms
|-- CONTRIBUTING.md          Contributor workflow
|-- SECURITY.md              Vulnerability reporting policy
|-- CODE_OF_CONDUCT.md       Community expectations
|-- SUPPORT.md               Support expectations
|-- GOVERNANCE.md            Maintainer and release model
|-- CHANGELOG.md             Release history
`-- LICENSE                  MIT license
```

## Production Notes

SigmaLite can be deployed as separate frontend and backend services.

Recommended production posture:

- PostgreSQL for `DATABASE_URL`.
- Durable upload storage or mounted persistent disk for uploaded CSVs.
- Strong `SECRET_KEY`, managed as a secret.
- Explicit `ALLOWED_ORIGINS`.
- HTTPS termination at the platform/load balancer.
- Platform or WAF-level rate limiting in front of the app.
- Backups for the database and uploaded files.
- Migration release step: `alembic upgrade head`.

Deployment checklist: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md#deployment-smoke-checklist).

## Documentation

- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md): setup, testing, migrations, deployment.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): system design and data flow.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): planned beta and production work.
- [`docs/DISABLE_AUTH.md`](docs/DISABLE_AUTH.md): local auth bypass behavior and risks.
- [`PRD_COMPLIANCE.md`](PRD_COMPLIANCE.md): current implementation status.

## Contributing

Contributions are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md).

Before opening a PR:

1. Keep changes scoped.
2. Add or update tests for behavior changes.
3. Run backend tests, frontend tests, build, and E2E smoke.
4. Include screenshots for UI changes.

## Security

Do not open public issues for vulnerabilities. Follow [`SECURITY.md`](SECURITY.md)
for private reporting expectations.

## Support

Use GitHub Issues for reproducible bugs and feature requests. See
[`SUPPORT.md`](SUPPORT.md) for what to include.

## License

SigmaLite is released under the MIT License. See [`LICENSE`](LICENSE).
