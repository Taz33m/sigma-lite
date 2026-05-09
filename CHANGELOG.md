# Changelog

All notable changes to SigmaLite will be documented in this file.

The project follows a practical changelog format inspired by Keep a Changelog.
Semantic versioning will be used once the public API stabilizes.

## Unreleased

### Added

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

### Known Limits

- Cell edits are last-write-wins.
- Dataset rows are CSV-backed.
- Formula support is aggregate-focused.
- CSV export is current-page only.
- Rate limiting is single-process.
