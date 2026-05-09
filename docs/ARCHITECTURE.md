# Architecture

SigmaLite is a two-service web app:

- `backend/`: FastAPI API, SQLAlchemy models, Alembic migrations, data
  processing, authentication, and WebSocket collaboration.
- `frontend/`: React/Vite/MUI workspace UI, data grid, chart rendering,
  comment UI, export UX, and E2E tests.

## Backend Responsibilities

The backend owns:

- JWT authentication and refresh.
- Dataset upload validation and storage metadata.
- CSV reading, schema inference, pagination, filtering, aggregation, formulas,
  and cell updates.
- Sheet, chart, and comment persistence.
- WebSocket connection management and collaboration event broadcast.
- Production configuration guardrails.

## Frontend Responsibilities

The frontend owns:

- Authentication screens and token persistence.
- Dataset dashboard and upload workflow.
- Sheet workspace layout.
- Data grid display and edit submission.
- Filter builder and aggregation controls.
- Chart preview, saved chart rendering, and PNG export.
- Selected-cell comment workflow.
- CSV export for visible rows.
- Playwright product-loop smoke coverage.

## Data Flow

```text
User uploads CSV
  -> POST /api/datasets
  -> backend stores file and metadata
  -> schema inferred with pandas
  -> dashboard lists dataset

User creates sheet
  -> POST /api/sheets
  -> frontend opens /sheet/:id
  -> grid fetches /api/datasets/:id/data

User edits cell
  -> PATCH /api/datasets/:id/cell
  -> backend evaluates supported formula if needed
  -> CSV backing file is rewritten
  -> schema metadata is refreshed
  -> WebSocket event broadcasts update activity
```

## Persistence Model

Relational data is stored in SQL tables:

- `users`
- `datasets`
- `sheets`
- `charts`
- `comments`

Dataset row values are currently stored in uploaded CSV files. This keeps the
system simple for beta-scale datasets, but larger production deployments should
measure performance and consider a row/cell storage model or columnar storage.

## Realtime Model

The WebSocket layer broadcasts collaboration events for a sheet:

- connection/presence changes
- cursor movement
- cell update activity
- comments

The system does not yet implement CRDTs, operational transforms, or multi-user
merge resolution. Cell edits are last-write-wins.

## Security Boundaries

- REST endpoints are scoped to the authenticated owner.
- `DISABLE_AUTH` is local-only and rejected in production mode.
- Production mode rejects weak secrets and wildcard CORS.
- Uploads are limited by size and CSV extension.
- CSV export neutralizes formula-like values.

## Operational Notes

For production, use:

- PostgreSQL instead of local SQLite.
- Durable upload storage.
- HTTPS.
- Platform/WAF rate limiting.
- Regular database and upload backups.
- `alembic upgrade head` as a release step.
