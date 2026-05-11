# SigmaLite PRD

## Public-Beta Scope

SigmaLite is an independent CSV workspace for spreadsheet-style data
exploration. It is not affiliated with Sigma Computing and does not claim to be
a full BI platform, warehouse semantic layer, or Excel-compatible workbook
engine.

The current product target is public beta: credible, bounded, testable, and safe
to review publicly without overstating production readiness.

## Product Goal

Users should be able to upload a CSV, inspect inferred schema, open a sheet,
filter/sort/query rows, edit cells with optimistic conflict handling, run safe
formulas and aggregates, save charts, comment in context, share sheets with
viewer/editor roles, and export filtered data or a PDF report.

## Implemented Capabilities

| Area | Public-beta behavior |
| --- | --- |
| Upload | CSV upload only; original CSV is retained as a source artifact |
| Storage | Normalized DB-backed columns, rows, and cells are authoritative after ingest |
| Querying | Server-side filters, sort, pagination, and aggregation through sheet and legacy dataset routes |
| Editing | Per-cell versions; stale edits return `409 Conflict`; formulas store formula text separately from computed value |
| Formulas | Bounded `SUM`, `AVG`/`AVERAGE`, `MIN`, `MAX`, `COUNT`, `MEDIAN`, `ROUND`, arithmetic, direct refs, whole-column refs, and same-column ranges |
| Collaboration | WebSocket presence/cursor/comment/cell-update activity through single-use tickets |
| Sharing | Sheet roles: owner, editor, viewer; share lists and mutations are owner-only |
| Audit | Uploads, auth, sharing, edits, comments, charts, exports, deletes, and rate-limit blocks are audited with non-superuser redaction |
| Export | Full filtered CSV/XLSX export up to the configured row cap; PDF report with schema/filter/comment/chart context and capped preview |
| Operations | Structured request logs, health/live/ready checks, protected metrics, Render/Vercel config, Redis rate limiting, and runbooks |

## Non-Goals For This Beta

- Public API ingestion beyond CSV upload.
- `/visualize` API route.
- Full Excel formula compatibility.
- CRDT/OT collaboration.
- Warehouse-scale storage or columnar execution.
- Formal enterprise governance, SSO, SOC2, or advanced audit retention.
- Claimed hosted deployment unless an actual deployment URL is published.

## Key Interfaces

| Interface | Purpose |
| --- | --- |
| `POST /api/datasets/{dataset_id}/query` | Legacy owner-scoped filtered/sorted/paginated query |
| `POST /api/sheets/{sheet_id}/query` | Sheet-permissioned query used by the grid, charts, and exports |
| `POST /api/sheets/{sheet_id}/aggregate` | Filter-aware sheet aggregation |
| `PATCH /api/sheets/{sheet_id}/cell` | Versioned cell update with formula persistence |
| `POST /api/sheets/{sheet_id}/formula-preview` | Validate and evaluate formulas before save |
| `POST /api/sheets/{sheet_id}/export` | CSV, XLSX, or PDF export |
| `POST /api/sheets/{sheet_id}/ws-ticket` | 60-second single-use WebSocket ticket |
| `WS /ws/collaborate/{sheet_id}?ticket=...` | Presence and committed collaboration events |
| `GET/POST/DELETE /api/sheets/{sheet_id}/shares` | Owner-managed collaborator access |
| `GET /api/audit` | Visible audit log query with redaction for non-superusers |

## Public-Beta Success Criteria

- Auth is enabled by default; staging/production reject disabled auth, weak
  secrets, wildcard CORS, and non-Redis rate limiting.
- No bearer, access, or refresh token is placed in a WebSocket URL.
- Old refresh tokens cannot be reused after rotation.
- Viewers cannot edit cells, manage shares, or enumerate collaborator emails.
- Revoked collaborators lose REST access and cannot obtain WebSocket tickets.
- Sheet and dataset aggregate endpoints respect active filters.
- Saved charts query their saved filter/sort scope independently from the
  current grid page.
- Export and formula paths enforce explicit row/length/resource caps.
- CI covers SQLite fast tests plus a focused Postgres/Redis integration subset.

## Load Targets

CI keeps a 10k-row smoke path. Staging/manual runs should use generated 10k,
100k, and 250k datasets. Public-beta targets are:

| Operation | Target |
| --- | --- |
| 100k-row page query | p95 under 500ms |
| 100k-row sort/filter | p95 under 1.5s |
| Aggregation | p95 under 2s |
| 10 concurrent users for 5 minutes | No 5xx responses |

These are targets to verify in staging, not universal claims for every local
machine or deployment plan.
