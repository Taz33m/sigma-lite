# Changelog

All notable changes to SigmaLite will be documented in this file.

The project follows a practical changelog format inspired by Keep a Changelog.
Semantic versioning will be used once the public API stabilizes.

## Unreleased

## 0.2.0-beta.1

### Added

- Public-beta hardening track with DB-backed row/cell storage, sheet sharing,
  audit events, health/readiness/metrics surfaces, operations runbooks, and
  load-test tooling.
- Refresh-token persistence, rotation, replay-family revocation, and logout.
- Single-use WebSocket tickets for collaboration sockets.
- Owner/editor/viewer sheet roles, owner-only share management, and redacted
  non-superuser audit responses.
- Full filtered CSV/XLSX/PDF export with row caps and safe filenames.
- Formula preview and persisted formula validation with length, row-count,
  arithmetic, magnitude, self-reference, and circular-reference guards.
- CI coverage for backend dependency audit and a focused Postgres/Redis
  integration job.
- Playwright product-loop E2E coverage.
- GitHub Actions CI for backend tests, migration smoke, frontend tests/build,
  and E2E.
- Persisted sheet/cell comments.
- Selected-cell comment anchoring and grid comment markers.
- CSV export with spreadsheet-formula injection neutralization.
- A1 and whole-column aggregate formulas.
- Production configuration guards.
- In-process rate limiting for auth and upload routes.
- Open-source project artifacts: contributing guide, security policy, support
  policy, governance notes, issue templates, PR template, architecture doc, and
  roadmap.

### Changed

- Reworked README and project docs for beta-candidate status.
- Upgraded frontend runtime dependencies for security advisories.
- Split sheet workspace chart/socket/summary/grid concerns into smaller
  modules.
- Versioned the project as `0.2.0-beta.1`.

### Known Limits

- Cell edits use optimistic per-cell versions, not CRDTs or operational
  transforms.
- Uploaded CSVs remain source artifacts, but normalized DB rows/cells are
  authoritative after ingest.
- Formula support is aggregate-focused.
- CSV/XLSX export covers full filtered data up to the configured row cap.
- Rate limiting requires Redis for staging/production and should be paired with
  Cloudflare/WAF rules for public API domains.
