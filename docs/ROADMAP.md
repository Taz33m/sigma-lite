# Roadmap

This roadmap describes the next meaningful work after the public-beta hardening
pass. It is not a promise of delivery dates.

## Beta Stabilization

- Self-hosted/staging deployment and smoke verification.
- More frontend component coverage for the sheet workspace.
- Capture self-hosted/staging benchmark results for 100k/250k rows before
  making public performance claims.

## Collaboration

- Shareable presence UX beyond current cursor and remote edit toasts.
- Share links in addition to named-user sharing.
- CRDT/operational-transform research for deeper multi-user editing.

## Data Scale

- Measured upload/filter/aggregate benchmarks at 100k and 250k rows.
- Postgres-specific indexing and ingest/export tuning for normalized row/cell
  storage.
- Columnar/warehouse strategy review if public-beta data sizes outgrow Postgres rows.

## Spreadsheet Features

- More formula functions.
- Formula dependency graph visualization.
- Broader recalculation coverage for complex dependency chains.

## Self-Hosted Operations

- Trial API-edge schema validation in log mode using the OpenAPI 3.0 export.
- Live self-hosted deployment validation after the final host/domain is selected.
- Alert policy definition after self-hosted/staging metrics are captured.
