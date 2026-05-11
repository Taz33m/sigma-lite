# Security Policy

## Supported Versions

SigmaLite is currently a beta-candidate project. Security fixes are accepted
against `main`.

## Reporting A Vulnerability

Please do not open a public issue for a suspected vulnerability.

Preferred reporting path:

1. Use GitHub private vulnerability reporting if it is enabled for the
   repository.
2. If private reporting is unavailable, contact maintainer
   [@Taz33m](https://github.com/Taz33m) privately. If no private channel is
   available, open a public issue titled `Security contact requested` without
   technical details.

Useful report details:

- Affected endpoint, page, or workflow.
- Steps to reproduce.
- Impact and prerequisites.
- Relevant logs, screenshots, or proof-of-concept input.
- Whether the issue is already being exploited.

## Security Posture

Current protections include:

- JWT access and refresh tokens.
- Refresh-token rotation, replay detection, and logout revocation.
- Single-use, short-lived WebSocket tickets instead of bearer tokens in
  WebSocket URLs.
- Password hashing with bcrypt.
- Pydantic request validation.
- SQLAlchemy ORM usage.
- CORS allow-list configuration.
- Public-environment guards for weak secrets, wildcard CORS, disabled auth, and
  non-Redis rate limiting.
- Redis-backed sliding-window rate limiting when `RATE_LIMIT_BACKEND=redis`,
  with in-memory fallback only for local/test.
- Sheet-level sharing roles plus owner-managed share lists.
- Audit logs with IP/private metadata redaction for non-superusers.
- CSV export neutralization for spreadsheet-formula injection values.
- Formula and export row caps.

Known beta limits:

- Redis rate limiting should still be paired with Cloudflare WAF/rate-limit
  rules or equivalent API-edge protection for public deployments.
- Uploaded CSV files remain as source artifacts; DB-backed rows/cells are
  authoritative after ingest and both DB plus uploads need backup coverage.
- Collaboration uses optimistic cell versions, not CRDTs or operational
  transforms.
- This is a public-beta posture, not a SOC2/enterprise security program.

## Disclosure

Maintainers will acknowledge valid reports when possible, triage impact, and
coordinate a fix before public disclosure.
