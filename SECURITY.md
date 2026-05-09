# Security Policy

## Supported Versions

SigmaLite is currently a beta-candidate project. Security fixes are accepted
against `main`.

## Reporting A Vulnerability

Please do not open a public issue for a suspected vulnerability.

Preferred reporting path:

1. Use GitHub private vulnerability reporting if it is enabled for the
   repository.
2. If private reporting is unavailable, contact the project maintainers through
   a private channel and include enough detail to reproduce the issue.

Useful report details:

- Affected endpoint, page, or workflow.
- Steps to reproduce.
- Impact and prerequisites.
- Relevant logs, screenshots, or proof-of-concept input.
- Whether the issue is already being exploited.

## Security Posture

Current protections include:

- JWT access and refresh tokens.
- Password hashing with bcrypt.
- Pydantic request validation.
- SQLAlchemy ORM usage.
- CORS allow-list configuration.
- Production guards for weak secrets, wildcard CORS, and disabled auth.
- Basic in-process rate limiting for auth and upload routes.
- CSV export neutralization for spreadsheet-formula injection values.

Known beta limits:

- In-process rate limiting is not a replacement for a production WAF or
  platform-level rate limit.
- CSV-backed datasets require careful deployment storage and backup planning.
- Cell edits are last-write-wins.
- Collaboration is not yet a full permissions/sharing system.

## Disclosure

Maintainers will acknowledge valid reports when possible, triage impact, and
coordinate a fix before public disclosure.
