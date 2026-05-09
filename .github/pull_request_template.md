## Summary

What changed and why?

## Verification

- [ ] Backend tests: `cd backend && uv run python -m pytest -q`
- [ ] Migration smoke: fresh SQLite `alembic upgrade head`
- [ ] Frontend tests: `cd frontend && npm test -- --run`
- [ ] Frontend build: `cd frontend && npm run build`
- [ ] E2E: `cd frontend && npm run test:e2e -- --project=chromium`
- [ ] Production audit gate: `cd frontend && npm audit --omit=dev --audit-level=high`

## Screenshots

Add screenshots or short clips for UI changes.

## Risk And Rollback

What could break? How should this be rolled back?

## Notes

Known limits, follow-up work, or migration/deployment notes.
