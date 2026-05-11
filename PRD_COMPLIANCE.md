# PRD Compliance Report

SigmaLite is past demo-only status. The core MVP loop and current public-beta
hardening pass are implemented and covered by backend, frontend, build,
migration, staging-smoke, and Playwright smoke checks. Remaining work is live
deployment validation, measured staging benchmarks, and deeper enterprise
controls.

## Current Feature Matrix

| Area | Status | Notes |
| --- | --- | --- |
| Authentication & users | Complete | Register/login, refresh rotation/replay revocation, logout, `/me`, JWT isolation, bcrypt hashing, optional local `DISABLE_AUTH`. |
| Dataset upload | Complete | CSV upload, file size limit, safe display filename, unique stored filename, schema inference. |
| Data grid | Beta | Paginated MUI grid, editable cells, DB-backed row/cell persistence, comment markers, sheet-scoped server-side sorting. |
| Filtering | Beta | Sheet-scoped backend validation plus frontend visual filter builder with saved view config. |
| Aggregation/formulas | Beta | Aggregate formulas plus arithmetic, direct cell refs, same-column ranges, whole-column refs, and `ROUND`. Complex spreadsheet compatibility remains out of scope. |
| Charts | Beta | Bar/line/scatter/pie chart builder, saved charts, PNG export. Drag-and-drop builder is future work. |
| Export | Beta | Full filtered/sorted CSV, XLSX, and PDF export with CSV formula-injection neutralization. |
| Collaboration | Beta | WebSocket presence/cursor events with connection and fanout limits, persisted comments, role-based sharing, and optimistic cell conflict handling. |
| Persistence | Public beta | Users, datasets, normalized row/cell tables, sheets, charts, comments, shares, audit events with Alembic migrations. SQLite local/test; Postgres production target. |
| Security hardening | Beta | Public-environment config guards, CORS allow-list, JWT auth, refresh rotation, one-time WebSocket tickets, route validation, Redis-backed sliding-window app limits, protected metrics/docs defaults, Cloudflare WAF runbook, Render Blueprint. |
| QA | Beta | Backend tests including 10k-row smoke, deployed-API smoke utility, load-tool checks, OpenAPI 3.0 export checks, and deployment config checks; frontend unit tests, lint, production build, and Playwright product-loop smoke. |

## Implemented PRD Requirements

- **FR-1 Data Upload:** CSV upload, schema inference, validation, storage.
- **FR-2 Data Grid:** Display, pagination, editable cells, persisted updates.
- **FR-3 Filtering:** Sheet-scoped backend query API and visual filter UI.
- **FR-4 Visualization:** Chart API, chart builder UI, chart rendering, PNG export.
- **FR-5 Persistence:** Saved datasets, sheets, chart configs, comments.
- **FR-6 Realtime Infrastructure:** WebSocket collaboration endpoint, connection limits, presence validation, and fanout throttling.
- **FR-7 Collaboration UI:** Active user count, cursor activity, anchored comments.
- **FR-8 Authentication:** JWT access/refresh auth and user isolation.
- **FR-9 REST API:** Dataset, sheet-scoped query/aggregate, chart, auth, comments, filtering, aggregation.
- **FR-10 Export:** CSV export and chart image export.

## Known Beta Limits

- Cell edits use optimistic conflicts, not CRDTs or operational transforms.
- DB row/cell storage is authoritative after ingest; uploaded CSVs remain source artifacts.
- Formula support is richer but still not Excel-compatible.
- PDF export is a report-style summary with capped row preview, not pixel-perfect dashboard rendering.
- Redis-backed app rate limits should still be paired with Cloudflare/API-domain controls.
- Cloudflare API Shield schema validation should use the generated OpenAPI 3.0 artifact in log mode before block mode.

## Readiness Summary

| Readiness Dimension | Status |
| --- | --- |
| MVP demo | Cleared |
| Internal beta | Ready after deployment env verification |
| Public beta | Ready for Render Blueprint apply, staging verification behind Cloudflare, and benchmark capture |
| Enterprise/production | Needs advanced governance, CRDT/OT-style collaboration, warehouse-scale storage strategy, and formal SLOs |
