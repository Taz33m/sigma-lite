import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        'cd ../backend && rm -f test_e2e_sigmalite.db && DATABASE_URL=sqlite:///./test_e2e_sigmalite.db SECRET_KEY=e2e-secret-key-with-enough-entropy ENVIRONMENT=test UPLOAD_DIR=./uploads-e2e ALLOWED_ORIGINS=http://127.0.0.1:5174,http://localhost:5174 uv run alembic upgrade head && DATABASE_URL=sqlite:///./test_e2e_sigmalite.db SECRET_KEY=e2e-secret-key-with-enough-entropy ENVIRONMENT=test UPLOAD_DIR=./uploads-e2e ALLOWED_ORIGINS=http://127.0.0.1:5174,http://localhost:5174 uv run uvicorn app.main:app --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/health',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command:
        'VITE_API_URL=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5174',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
