import { defineConfig, devices } from '@playwright/test';

const frontendPort = process.env.E2E_FRONTEND_PORT ?? '5174';
const backendPort = process.env.E2E_BACKEND_PORT ?? '8001';
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const backendEnv =
  'DATABASE_URL=sqlite:///./test_e2e_sigmalite.db ' +
  'SECRET_KEY=e2e-secret-key-with-enough-entropy ' +
  'ENVIRONMENT=test ' +
  'UPLOAD_DIR=./uploads-e2e ' +
  `ALLOWED_ORIGINS=${frontendUrl},http://localhost:${frontendPort}`;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  use: {
    baseURL: frontendUrl,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        `cd ../backend && rm -f test_e2e_sigmalite.db && ${backendEnv} uv run alembic upgrade head && ${backendEnv} uv run uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `${backendUrl}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `VITE_API_URL=${backendUrl} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: frontendUrl,
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
