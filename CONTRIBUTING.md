# Contributing

Thanks for taking the time to improve SigmaLite. This project values focused,
well-tested changes that keep the product understandable and operable.

## Development Workflow

1. Fork the repository and create a branch from `main`.
2. Keep the branch scoped to one fix or feature.
3. Add tests for behavior changes.
4. Run the verification commands before opening a PR.
5. Open a PR with a clear description, screenshots for UI changes, and notes on
   any tradeoffs.

## Local Setup

Use the quick start in [`README.md`](README.md#quick-start). Deeper setup,
migrations, troubleshooting, and deployment notes are in
[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Verification Commands

```bash
cd backend && uv run python -m pytest -q
cd frontend && npm test -- --run
cd frontend && npm run build
cd frontend && npm run test:e2e -- --project=chromium
cd frontend && npm audit --omit=dev --audit-level=high
```

For backend migrations, also run a fresh SQLite migration smoke:

```bash
cd backend
rm -f migration_smoke.db
DATABASE_URL=sqlite:///./migration_smoke.db \
  SECRET_KEY=migration-smoke-secret-with-enough-entropy \
  uv run alembic upgrade head
```

## Pull Request Expectations

A good PR includes:

- The problem being solved.
- The user-visible behavior change.
- Tests run locally.
- Screenshots or short clips for UI changes.
- Any known limitations or follow-up work.

Avoid bundling unrelated refactors with product changes. If a refactor is
needed to safely implement a feature, explain why in the PR.

## Code Style

- Backend: prefer explicit FastAPI/Pydantic/SQLAlchemy patterns already used in
  the codebase.
- Frontend: prefer existing MUI, React Query, Zustand, and local helper
  patterns.
- Keep APIs backward compatible unless the PR explicitly proposes a breaking
  change.
- Keep comments focused on non-obvious logic.

## Security-Sensitive Changes

Authentication, upload handling, CORS, token handling, CSV export, and
WebSocket changes should include tests and should call out security impact in
the PR description.

Do not include secrets, local databases, uploaded datasets, build output, or
Playwright traces in commits.
