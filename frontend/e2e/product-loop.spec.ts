import { expect, test } from '@playwright/test';

test('core product loop: auth, upload, sheet, edit, filter, chart, comment, export', async ({
  page,
  request,
}) => {
  const apiUrl = `http://127.0.0.1:${process.env.E2E_BACKEND_PORT ?? '8001'}`;
  const suffix = Date.now();
  const username = `e2e_${suffix}`;
  const password = 'e2epass123';

  const register = await request.post(`${apiUrl}/api/auth/register`, {
    data: {
      email: `${username}@example.com`,
      username,
      password,
      full_name: 'E2E User',
    },
  });
  expect(register.ok()).toBeTruthy();

  const login = await request.post(`${apiUrl}/api/auth/login`, {
    form: { username, password },
  });
  expect(login.ok()).toBeTruthy();
  const tokens = await login.json();
  const me = await request.get(`${apiUrl}/api/auth/me`, {
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
  const upload = await request.post(`${apiUrl}/api/datasets`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
    multipart: {
      name: 'E2E People',
      description: 'Full loop smoke dataset',
      file: {
        name: 'people.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from('name,age,city\nAlice,30,NYC\nBob,25,LA\nCarol,40,SF\n'),
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

  const cityCell = page.getByRole('cell', { name: 'LA' }).first();
  await cityCell.dblclick();
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.keyboard.type('=SUM(B1:B3)');
  await page.keyboard.press('Enter');
  await expect(page.getByText(/cell saved/i)).toBeVisible();

  await page.reload();
  await expect(page.getByRole('cell', { name: '95' }).first()).toBeVisible();

  await page.getByLabel('Column').first().click();
  await page.getByRole('option', { name: 'age' }).click();
  await page.getByLabel('Operator').click();
  await page.getByRole('option', { name: 'gt', exact: true }).click();
  await page.getByLabel('Value').fill('35');
  await page.getByRole('button', { name: /^add$/i }).click();
  await expect(page.getByText(/1 active filter/i)).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Carol' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Alice' })).toHaveCount(0);
  await page.getByRole('button', { name: /^clear$/i }).click();

  await page.getByLabel('Column').first().click();
  await page.getByRole('option', { name: 'city' }).click();
  await page.getByLabel('Operator').click();
  await page.getByRole('option', { name: 'eq' }).click();
  await page.getByLabel('Value').fill('95');
  await page.getByRole('button', { name: /^add$/i }).click();
  await expect(page.getByText(/1 active filter/i)).toBeVisible();

  await page.getByRole('tab', { name: 'Summary' }).click();
  await page.getByLabel('Column').click();
  await page.getByRole('option', { name: 'age' }).click();
  await page.getByRole('button', { name: /^run$/i }).click();
  await expect(page.getByRole('heading', { name: '25' })).toBeVisible();

  await page.getByRole('tab', { name: 'Charts' }).click();
  await page.getByRole('textbox', { name: 'Name' }).fill('Age by city');
  await page.getByLabel('X field').click();
  await page.getByRole('option', { name: 'city' }).click();
  await page.getByLabel('Y field').click();
  await page.getByRole('option', { name: 'age' }).click();
  await page.getByRole('button', { name: /save chart/i }).click();
  await expect(page.getByText('Chart saved')).toBeVisible();
  await expect(page.getByText('Age by city')).toBeVisible();

  await page.getByRole('cell', { name: '95' }).first().click();
  await page.getByRole('tab', { name: 'Comments' }).click();
  await page.getByLabel('Comment').fill('Check this filtered cell');
  await page.getByRole('button', { name: /^send$/i }).click();
  await expect(page.getByText('Check this filtered cell')).toBeVisible();

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /export csv/i }).click();
  const file = await download;
  expect(file.suggestedFilename()).toContain('export.csv');

  await page.reload();
  await page.getByRole('tab', { name: 'Comments' }).click();
  await expect(page.getByText('Check this filtered cell')).toBeVisible();
});
