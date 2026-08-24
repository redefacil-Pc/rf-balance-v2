import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  globalTeardown: './tests/e2e/global-teardown.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'docker compose -f ../../infrastructure/compose/docker-compose.yml --env-file ../../.env run --rm --name rfbalance-e2e-api -p 127.0.0.1:8001:8000 -e APP_ENV=local -e COOKIE_SECURE=false -e DATABASE_URL=mysql+asyncmy://rfbalance:rfbalance@db:3306/rfbalance_test -e MIGRATION_DATABASE_URL=mysql+asyncmy://rfbalance_migrator:rfbalance_migrator@db:3306/rfbalance_test -e REDIS_URL=redis://redis:6379/10 -e SEED_ADMIN_PASSWORD=e2e-admin-password-2026 api sh -c "alembic upgrade head && python -m app.platform.db.prepare_e2e && uvicorn app.main:app --host 0.0.0.0 --port 8000"',
      url: 'http://127.0.0.1:8001/health/ready',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev:e2e',
      url: 'http://127.0.0.1:5174/login',
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
});
