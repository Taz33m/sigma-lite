# Architecture

SigmaLite is a two-service web app:

- `backend/`: FastAPI API, SQLAlchemy models, Alembic migrations, data
  processing, authentication, and WebSocket collaboration.
- `frontend/`: React/Vite/MUI workspace UI, data grid, chart rendering,
  comment UI, export UX, and E2E tests.

## Backend Responsibilities

The backend owns:

- JWT authentication, refresh-token rotation, logout revocation, and WebSocket
  ticket issuance.
- Dataset upload validation and storage metadata.
- CSV reading, schema inference, DB-backed row/cell ingest, pagination,
  filtering, sorting, aggregation, formulas, and conflict-aware cell updates.
- Sheet, chart, comment, share, and audit persistence.
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
- Full CSV/XLSX/PDF export for filtered/sorted sheet data.
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
  -> grid fetches /api/sheets/:id/query through sheet permissions

User edits cell
  -> PATCH /api/sheets/:id/cell with expected_version
  -> backend rejects stale versions with 409 or commits a new cell version
  -> backend evaluates supported formula if needed
  -> WebSocket event broadcasts committed update activity
```

## Persistence Model

Relational data is stored in SQL tables:

- `users`
- `datasets`
- `sheets`
- `charts`
- `comments`
- `dataset_columns`
- `dataset_rows`
- `dataset_cells`
- `sheet_shares`
- `audit_events`
- `refresh_tokens`
- `websocket_tickets`

Uploaded CSV files are retained as source artifacts. After ingest, normalized
row/cell tables are the authoritative store for query, edit, sort, aggregate,
formula, and export behavior.

## Realtime Model

The WebSocket layer uses `POST /api/sheets/{sheet_id}/ws-ticket` to issue a
60-second, single-use ticket. The browser connects to
`/ws/collaborate/{sheet_id}?ticket=...`; bearer, access, and refresh tokens are
not placed in WebSocket URLs.

After ticket validation, the WebSocket layer broadcasts collaboration events for
a sheet:

- connection/presence changes
- cursor movement
- cell update activity
- comments

Connections are capped per user per sheet, and presence fanout messages are
validated, size-limited, and rate-limited in-process for public-beta abuse
resistance.

The system does not yet implement CRDTs or operational transforms. Cell edits
use optimistic version checks; stale writes return `409 Conflict` with the
current value/version so the frontend can reload or explicitly overwrite.

## Security Boundaries

- REST endpoints are scoped to authenticated owners or explicit sheet shares.
- Dataset row/query/aggregate endpoints are owner-scoped compatibility surfaces;
  collaborative workspace reads go through sheet-scoped routes.
- `DISABLE_AUTH` is local-only and rejected in staging/production mode.
- Staging/production mode rejects weak secrets, wildcard CORS, and non-Redis
  rate limiting.
- Uploads are limited by size and CSV extension.
- CSV export neutralizes formula-like values.
- Redis-backed sliding-window rate limiting is used when configured, with
  local/test in-memory fallback.

## Operational Notes

For production, use:

- PostgreSQL instead of local SQLite.
- Durable upload storage.
- HTTPS.
- Cloudflare-proxied API domain with WAF/rate limiting.
- Regular database and upload backups.
- `alembic upgrade head` as a release step.

See [`OPERATIONS.md`](OPERATIONS.md) for monitoring, backup/restore, Cloudflare,
and load-test runbooks.
