import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eDir = path.dirname(fileURLToPath(import.meta.url));

test('core product loop: auth, upload, sheet, edit, filter, chart, comment, export', async ({
  page,
  request,
}) => {
  const suffix = Date.now();
  const username = `e2e_${suffix}`;
  const password = 'e2epass123';

  const register = await request.post('http://127.0.0.1:8001/api/auth/register', {
    data: {
      email: `${username}@example.com`,
      username,
      password,
      full_name: 'E2E User',
    },
  });
  expect(register.ok()).toBeTruthy();

  const login = await request.post('http://127.0.0.1:8001/api/auth/login', {
    form: { username, password },
  });
  expect(login.ok()).toBeTruthy();
  const tokens = await login.json();
  const me = await request.get('http://127.0.0.1:8001/api/auth/me', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const user = await me.json();

  await page.addInitScript(
    ({ accessToken, refreshToken, currentUser }) => {
      window.localStorage.setItem('access_token', accessToken);
      window.localStorage.setItem('refresh_token', refreshToken);
      window.localStorage.setItem(
        'auth-storage',
        JSON.stringify({
          state: { user: currentUser, isAuthenticated: true },
          version: 0,
        })
      );
    },
    {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      currentUser: user,
    }
  );

  await page.goto('/');

  await expect(page.getByRole('heading', { name: /my datasets/i })).toBeVisible();
  const csvPath = path.resolve(e2eDir, 'fixtures/people.csv');
  const upload = await request.post('http://127.0.0.1:8001/api/datasets', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
    multipart: {
      name: 'E2E People',
      description: 'Full loop smoke dataset',
      file: {
        name: 'people.csv',
        mimeType: 'text/csv',
        buffer: fs.readFileSync(csvPath),
      },
    },
  });
  expect(upload.ok()).toBeTruthy();
  await page.reload();

  await expect(page.getByText('E2E People')).toBeVisible();
  await page.getByRole('button', { name: /view/i }).click();
  await expect(page.getByRole('button', { name: /create sheet/i })).toBeVisible();
  await page.getByRole('button', { name: /create sheet/i }).click();

  await expect(page.getByText('Alice')).toBeVisible();
  await expect(page.getByText('Saved sheet')).toBeVisible();

  const ageCell = page.getByRole('cell', { name: '25' }).first();
  await ageCell.dblclick();
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.keyboard.type('=SUM(B1:B3)');
  await page.keyboard.press('Enter');
  await expect(page.getByText(/cell saved/i)).toBeVisible();

  await page.reload();
  await expect(page.getByRole('cell', { name: '95' }).first()).toBeVisible();

  await page.getByLabel('Column').first().click();
  await page.getByRole('option', { name: 'city' }).click();
  await page.getByLabel('Value').fill('LA');
  await page.getByRole('button', { name: /^add$/i }).click();
  await expect(page.getByText(/1 active filter/i)).toBeVisible();

  await page.getByLabel('Column').nth(1).click();
  await page.getByRole('option', { name: 'age' }).click();
  await page.getByRole('button', { name: /^run$/i }).click();
  await expect(page.getByText('95')).toBeVisible();

  await page.getByRole('textbox', { name: 'Name' }).fill('Age by city');
  await page.getByLabel('X field').click();
  await page.getByRole('option', { name: 'city' }).click();
  await page.getByLabel('Y field').click();
  await page.getByRole('option', { name: 'age' }).click();
  await page.getByRole('button', { name: /save chart/i }).click();
  await expect(page.getByText('Chart saved')).toBeVisible();
  await expect(page.getByText('Age by city')).toBeVisible();

  await page.getByRole('cell', { name: 'LA' }).first().click();
  await page.getByLabel('Comment').fill('Check this filtered cell');
  await page.getByRole('button', { name: /^send$/i }).click();
  await expect(page.getByText('Check this filtered cell')).toBeVisible();

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /export csv/i }).click();
  const file = await download;
  expect(file.suggestedFilename()).toContain('current-page.csv');

  await page.reload();
  await expect(page.getByText('Check this filtered cell')).toBeVisible();
});
