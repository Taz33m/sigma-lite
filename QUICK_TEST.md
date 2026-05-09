# Quick Test

The maintained test commands now live in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md#testing).

Current release-candidate verification:

```bash
cd backend && uv run python -m pytest -q
cd frontend && npm test -- --run
cd frontend && npm run build
cd frontend && npm run test:e2e -- --project=chromium
```

For local auth-bypass demos, see [`docs/DISABLE_AUTH.md`](docs/DISABLE_AUTH.md).
