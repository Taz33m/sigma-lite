<h1 align="center">SigmaLite</h1>

<p align="center">
  <strong>Spreadsheet-style data exploration that turns CSV files into editable, chartable, collaborative workspaces.</strong>
</p>

<p align="center">
  <a href="https://github.com/Taz33m/sigma-lite/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Taz33m/sigma-lite/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green" /></a>
  <img alt="Backend: FastAPI" src="https://img.shields.io/badge/backend-FastAPI-009688" />
  <img alt="Frontend: React + Vite" src="https://img.shields.io/badge/frontend-React%20%2B%20Vite-646CFF" />
  <img alt="Data: pandas + SQLAlchemy" src="https://img.shields.io/badge/data-pandas%20%2B%20SQLAlchemy-1E88E5" />
  <a href="https://youtu.be/aDMvTl-uKQ0"><img alt="Demo video" src="https://img.shields.io/badge/demo-video-red" /></a>
  <img alt="Claims: bounded" src="https://img.shields.io/badge/claims-bounded-important" />
</p>

<p align="center">
  <a href="https://youtu.be/aDMvTl-uKQ0">
    <img src="https://img.youtube.com/vi/aDMvTl-uKQ0/maxresdefault.jpg" alt="SigmaLite demo video" width="820" />
  </a>
</p>

<p align="center">
  <strong>Demo video:</strong>
  <a href="https://youtu.be/aDMvTl-uKQ0">youtu.be/aDMvTl-uKQ0</a>
</p>

> **TL;DR:** SigmaLite is a full-stack CSV workspace: upload a dataset, infer its schema, inspect and edit rows in a paginated grid, filter and aggregate values, save charts, attach comments, and see realtime collaboration signals. It is intentionally smaller than a BI platform and more structured than a raw spreadsheet.

## Why This Exists

CSV files are everywhere, but a CSV is not a workspace. It has rows, columns,
and values, but it does not carry schema context, saved analysis, chart
configuration, comments, user ownership, or team activity.

SigmaLite turns a raw file into a working data surface. The goal is not to
recreate Excel or ship a giant BI suite. The goal is a focused, inspectable
reference implementation of a modern spreadsheet-style analytics loop:

1. Upload a CSV.
2. Infer structure and preview rows.
3. Work in an editable grid.
4. Filter, aggregate, and calculate.
5. Save visualizations.
6. Discuss the numbers in context.
7. Keep the implementation honest with tests, migrations, CI, and E2E coverage.

## Best Way To Review

1. Watch the short demo video above.
2. Run the backend test suite and migration smoke.
3. Run the frontend unit tests and production build.
4. Run the Playwright product loop.
5. Open the app locally, upload a sample CSV, create a sheet, edit a cell,
   apply a filter, save a chart, add a comment, and export the visible rows.

```bash
# Backend
cd backend
uv run python -m pytest -q

# Frontend
cd ../frontend
npm test -- --run
npm run build
npm run test:e2e -- --project=chromium
```

## Product Walkthrough

### 1. Upload

Users upload a CSV from the dashboard. The backend validates the extension and
size, stores the file under a safe unique server-side name, records the original
display filename, and infers schema metadata with pandas.

### 2. Inspect

The dataset opens as a paginated MUI Data Grid with inferred columns, source row
indexes, dataset metadata, and editable cells.

### 3. Analyze

Users can apply validated filters, run aggregate operations, and enter supported
spreadsheet-style formulas such as:

```text
=SUM(age)
=AVG(B:B)
=MEDIAN(C1:C25)
```

Supported aggregate operations are `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, and
`MEDIAN` over named columns, whole-column references, and single-column A1
ranges.

### 4. Visualize

Selected columns can be turned into saved chart configurations. The frontend
renders bar, line, scatter, and pie charts with Chart.js, and supports PNG
export from the chart preview.

### 5. Collaborate

Sheets support persisted comments attached to the sheet or to a specific cell.
The WebSocket layer broadcasts presence, cursor activity, cell-update activity,
and comment activity for collaborators viewing the same sheet.

## What It Implements

| Area | Capability | Why it matters |
| --- | --- | --- |
| Authentication | Register, login, refresh tokens, current-user profile, bcrypt password hashing, JWT user isolation | Keeps datasets scoped to their owners |
| Dataset intake | CSV upload, file-size guard, safe display filename, unique stored filename, schema inference | Turns loose files into managed data assets |
| Grid workspace | Paginated MUI Data Grid, editable cells, persisted updates, comment markers | Makes the file usable as a working surface |
| Filters | Validated filter API plus frontend filter builder | Lets users narrow data without writing code |
| Formulas | Aggregate formulas over named columns, A1 ranges, and whole-column references | Gives spreadsheet-style calculation without pretending to be a full Excel engine |
| Charts | Saved chart configs, bar/line/scatter/pie rendering, PNG export | Converts selected data into reusable visual output |
| Comments | Sheet and cell comments with owner and timestamp metadata | Keeps discussion attached to the analysis |
| Realtime | WebSocket presence, cursors, cell updates, and comments | Shows collaborative activity in context |
| Export | Current-page CSV export with formula-injection neutralization | Makes the working view portable without spreadsheet security footguns |
| Operations | Alembic migrations, production config guardrails, CI, Playwright E2E | Makes the repo reviewable as an engineered product |

## Current Artifact Proof

The repository includes automated proof surfaces for the implemented product
loop.

| Proof surface | Verified scope |
| --- | --- |
| Backend pytest suite | `60` tests across auth, datasets, sheets, charts, WebSockets, config hardening, and a 10k-row product smoke |
| Frontend unit tests | `10` Vitest tests for auth state, API auth headers, grid row identity, and CSV export safety |
| E2E product loop | Playwright test for auth, upload, sheet creation, edit, filter, chart, comment, and export |
| Migration smoke | Fresh Alembic upgrade checks expected tables: `users`, `datasets`, `sheets`, `charts`, `comments`, `alembic_version` |
| Production build | TypeScript plus Vite build in CI |
| Dependency audit | `npm audit --omit=dev --audit-level=high` in CI |

See [`PRD_COMPLIANCE.md`](PRD_COMPLIANCE.md) for the current feature matrix and
beta limits.

## Architecture

```mermaid
flowchart LR
    A["React + TypeScript + Vite"] --> B["REST API"]
    A --> C["WebSocket collaboration"]
    B --> D["FastAPI application"]
    C --> D
    D --> E["pandas data processor"]
    D --> F["SQLAlchemy models"]
    F --> G["SQLite local / PostgreSQL production"]
    E --> H["Uploaded CSV files"]
    I["Alembic migrations"] --> G
    J["Playwright + pytest + Vitest"] --> A
    J --> D
```

Core responsibilities:

- `frontend/`: authentication UI, dashboard, sheet workspace, MUI grid, filters,
  aggregate controls, chart preview, saved chart cards, comments, CSV export,
  and Playwright product-loop coverage.
- `backend/`: FastAPI routes, JWT auth, owner-scoped resources, upload
  validation, pandas data processing, cell persistence, sheet/chart/comment
  models, Alembic migrations, config guardrails, and WebSocket broadcasts.

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Quick Start

### Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.11+ | Backend runtime and tests |
| Node.js | 22 recommended | Matches CI and Playwright setup |
| npm | Bundled with Node | Frontend dependency manager |
| SQLite | Bundled with Python | Default local database |
| PostgreSQL | 14+ optional | Recommended production database |

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set SECRET_KEY before exposing the server beyond localhost.

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend URLs:

| Surface | URL |
| --- | --- |
| API root | <http://localhost:8000> |
| Health | <http://localhost:8000/health> |
| Swagger | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>, register an account, upload a CSV, and create a
sheet from the dataset.

## Sample CSV

Use this if you want a quick product loop without finding a dataset:

```bash
cat > sample.csv <<'EOF'
name,age,city,salary,department
Alice,28,New York,75000,Engineering
Bob,35,San Francisco,95000,Engineering
Charlie,42,Chicago,68000,Sales
Diana,31,Boston,82000,Marketing
Noor,29,Austin,90000,Operations
EOF
```

Try these in an editable cell:

```text
=AVG(salary)
=SUM(D:D)
=COUNT(A1:A5)
```

## Command Surface

| Command | Purpose |
| --- | --- |
| `cd backend && uv run python -m pytest -q` | Run backend tests |
| `cd backend && alembic upgrade head` | Apply database migrations |
| `cd backend && uvicorn app.main:app --reload --port 8000` | Start the API locally |
| `cd frontend && npm test -- --run` | Run frontend unit tests once |
| `cd frontend && npm run build` | Typecheck and build the frontend |
| `cd frontend && npm run test:e2e -- --project=chromium` | Run the Playwright product loop |
| `cd frontend && npm run dev` | Start the Vite app |

## API Surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | `GET` | Service health |
| `/api/auth/register` | `POST` | Create user |
| `/api/auth/login` | `POST` | Issue access and refresh tokens |
| `/api/auth/refresh` | `POST` | Rotate tokens |
| `/api/auth/me` | `GET` | Return current user |
| `/api/datasets` | `GET`, `POST` | List or upload datasets |
| `/api/datasets/{id}` | `GET`, `PUT`, `DELETE` | Read, update, or delete dataset metadata |
| `/api/datasets/{id}/data` | `GET` | Return paginated rows |
| `/api/datasets/{id}/filter` | `POST` | Return filtered rows |
| `/api/datasets/{id}/aggregate` | `POST` | Aggregate a column |
| `/api/datasets/{id}/cell` | `PATCH` | Persist one cell update |
| `/api/sheets` | `GET`, `POST` | List or create sheets |
| `/api/sheets/{id}` | `GET`, `PUT`, `DELETE` | Read, update, or delete sheet metadata |
| `/api/sheets/{id}/comments` | `GET`, `POST` | List or create comments |
| `/api/charts` | `GET`, `POST` | List or create charts |
| `/api/charts/{id}` | `GET`, `PUT`, `DELETE` | Read, update, or delete charts |
| `/ws/collaborate/{sheet_id}` | `WS` | Presence, cursor, cell-update, and comment activity |

## Configuration

Backend configuration lives in `backend/.env`.

```env
DATABASE_URL=sqlite:///./sigmalite.db
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_ORIGINS=http://localhost:5173
DISABLE_AUTH=False
ENVIRONMENT=development
```

Frontend configuration lives in `frontend/.env`.

```env
VITE_API_URL=http://localhost:8000
VITE_DISABLE_AUTH=false
```

Production mode rejects unsafe combinations such as weak/default secrets,
wildcard CORS, and `DISABLE_AUTH=True`.

## Production Posture

For production, run SigmaLite as separate frontend and backend services:

- PostgreSQL for `DATABASE_URL`.
- Durable upload storage or a mounted persistent disk for uploaded CSVs.
- Strong `SECRET_KEY` managed by the hosting platform.
- Explicit `ALLOWED_ORIGINS`.
- HTTPS termination at the platform or load balancer.
- Platform/WAF rate limiting in front of the API.
- Database and upload backups.
- Release step: `alembic upgrade head`.
- Smoke check: register, upload, create sheet, edit, filter, aggregate, save
  chart, comment, connect WebSocket, export CSV.

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for migrations, deployment,
and troubleshooting.

## Repository Layout

```text
backend/                    FastAPI app, SQLAlchemy models, Alembic migrations, pytest suite
frontend/                   React/Vite app, MUI workspace, Vitest tests, Playwright E2E
docs/                       Architecture, development, roadmap, PRD, auth-bypass notes
.github/workflows/          CI for backend, frontend, migration smoke, and E2E
CONTRIBUTING.md             Contributor workflow
SECURITY.md                 Vulnerability reporting policy
CODE_OF_CONDUCT.md          Community expectations
SUPPORT.md                  Support expectations
GOVERNANCE.md               Maintainer and release model
CHANGELOG.md                Release history
PRD_COMPLIANCE.md           Implemented feature matrix and beta limits
LICENSE                     MIT license
```

## Claims And Non-Claims

| Claims | Non-claims |
| --- | --- |
| SigmaLite implements authenticated CSV upload, schema inference, paginated grid viewing, editable cell persistence, filtering, aggregate formulas, saved charts, comments, WebSocket activity, CSV export, migrations, CI, and E2E smoke coverage. | SigmaLite is not a full Excel-compatible formula engine. |
| Dataset, sheet, chart, and comment routes are scoped to the authenticated owner. | SigmaLite is not a complete BI platform or warehouse-native semantic layer. |
| Supported formulas are bounded aggregate formulas over named columns, whole-column references, and single-column A1 ranges. | SigmaLite does not yet implement CRDTs, operational transforms, or advanced merge resolution. |
| Production config guards reject disabled auth, weak secrets, and wildcard CORS in production mode. | The current CSV-backed row store is not a large-scale columnar analytics engine. |
| CI exercises backend tests, frontend tests, migration smoke, production build, dependency audit, and Playwright E2E. | Local benchmark or smoke behavior should not be treated as a universal performance claim. |

## Known Limits

- Cell edits are last-write-wins.
- Dataset rows are currently backed by uploaded CSV files.
- Server-side sorting is still future work.
- Formula support is aggregate-focused.
- CSV export covers the current visible/page-level grid rows, not a full
  workbook export.
- Rate limiting is in-process and should be paired with platform controls.
- WebSocket collaboration covers presence, cursors, cell updates, and comments,
  not full sharing roles or permissions.

## Roadmap

Near-term beta hardening:

- Server-side sorting and richer saved view state.
- Larger dataset performance profiling and storage strategy.
- Full-dataset export and richer chart export options.
- Role-based sharing and permission controls.
- Audit log for edits, comments, and exports.
- Conflict handling beyond last-write-wins.
- Production runbook for backups, restore, monitoring, and incident response.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the longer plan.

## Project Health

- Contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Support guide: [`SUPPORT.md`](SUPPORT.md)
- Governance: [`GOVERNANCE.md`](GOVERNANCE.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)

Pull requests should keep claims bounded, include tests for behavior changes,
and update docs when user-visible workflows change.

## License

SigmaLite is released under the MIT License. See [`LICENSE`](LICENSE).
