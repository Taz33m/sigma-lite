# PRD Compliance Report

SigmaLite is past demo-only status. The core MVP loop is implemented and now
covered by backend, frontend, build, migration, and Playwright smoke checks.
The remaining work is beta polish: larger-data performance, richer formula
coverage, collaborative conflict handling, and production operations.

## Current Feature Matrix

| Area | Status | Notes |
| --- | --- | --- |
| Authentication & users | Complete | Register/login, refresh, `/me`, JWT isolation, bcrypt hashing, optional local `DISABLE_AUTH`. |
| Dataset upload | Complete | CSV upload, file size limit, safe display filename, unique stored filename, schema inference. |
| Data grid | Beta | Paginated MUI grid, editable cells, CSV persistence, comment markers. Server-side sorting remains future work. |
| Filtering | Beta | Backend validation plus frontend visual filter builder with saved view config. |
| Aggregation/formulas | Beta | Column formulas and A1/whole-column aggregate formulas: `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `MEDIAN`. Complex spreadsheet formulas are out of scope. |
| Charts | Beta | Bar/line/scatter/pie chart builder, saved charts, PNG export. Drag-and-drop builder is future work. |
| Export | Beta | Current-page CSV export with spreadsheet-formula injection neutralization. Full workbook/PDF export remains future work. |
| Collaboration | Beta | WebSocket presence/cursor events, persisted sheet/cell comments, realtime comment broadcast. Multi-user edit conflict resolution is last-write-wins. |
| Persistence | Complete for MVP | Users, datasets, sheets, charts, comments with Alembic migrations. SQLite local/test; Postgres production target. |
| Security hardening | Beta | Production config guards, CORS allow-list, JWT auth, route validation, basic in-process rate limits. Needs external WAF/monitoring for production. |
| QA | Beta | 60 backend tests including 10k-row smoke, 10 frontend unit tests, production build, Playwright product-loop smoke. |

## Implemented PRD Requirements

- **FR-1 Data Upload:** CSV upload, schema inference, validation, storage.
- **FR-2 Data Grid:** Display, pagination, editable cells, persisted updates.
- **FR-3 Filtering:** Backend filter API and visual filter UI.
- **FR-4 Visualization:** Chart API, chart builder UI, chart rendering, PNG export.
- **FR-5 Persistence:** Saved datasets, sheets, chart configs, comments.
- **FR-6 Realtime Infrastructure:** WebSocket collaboration endpoint and presence.
- **FR-7 Collaboration UI:** Active user count, cursor activity, anchored comments.
- **FR-8 Authentication:** JWT access/refresh auth and user isolation.
- **FR-9 REST API:** Dataset, sheet, chart, auth, comments, filtering, aggregation.
- **FR-10 Export:** CSV export and chart image export.

## Known Beta Limits

- Cell edits are last-write-wins; there is no operational transform or merge UI.
- CSV files are still the backing store for dataset rows. This is acceptable for
  small/beta datasets but should be revisited after measured performance limits.
- Formula support is aggregate-focused, not a full spreadsheet calculation engine.
- CSV export covers current grid rows, not a full multi-sheet workbook.
- Rate limiting is single-process and should be paired with production platform
  protections.
- WebSocket collaboration is functional but not a full sharing/permissions system.

## Readiness Summary

| Readiness Dimension | Status |
| --- | --- |
| MVP demo | Cleared |
| Internal beta | Ready after deployment env verification |
| Public beta | Needs monitoring, production WAF/rate limits, load testing, and backup/restore runbook |
| Enterprise/production | Needs advanced permissions, audit logs, stronger collaboration semantics, and larger-data storage strategy |
