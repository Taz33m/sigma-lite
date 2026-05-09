# Roadmap

This roadmap describes the next meaningful work after the beta-candidate
release. It is not a promise of delivery dates.

## Beta Stabilization

- Staging deployment and smoke verification.
- Production logging and request tracing.
- Backup and restore runbook.
- Dependency audit cleanup for remaining transitive moderate advisories.
- More frontend component coverage for the sheet workspace.

## Collaboration

- Clearer remote edit notifications.
- Conflict detection for edits made against stale row data.
- Share links and view-only access.
- Role-based sheet permissions.

## Data Scale

- Measured upload/filter/aggregate benchmarks beyond 10k rows.
- Server-side sorting.
- Full-dataset export.
- Storage strategy review for row/cell tables or columnar storage.

## Spreadsheet Features

- More formula functions.
- Formula preview and validation UX.
- Distinguish stored literal values from computed formula outputs.

## Production Operations

- Structured logs.
- Metrics and health/readiness split.
- External rate limiting guidance.
- Deployment templates after the target host is selected.
