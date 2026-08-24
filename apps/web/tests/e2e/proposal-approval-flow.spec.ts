import { expect, request as createRequest, test, type Page } from '@playwright/test';

const apiBase = 'http://127.0.0.1:8001/api/v1/';

async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('E-mail').fill(email);
  await page.getByLabel('Senha').fill(password);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('link', { name: 'Ir para o dashboard' })).toBeVisible();
}

test('cadastro, comprovante, envio, fila, preview e aprovação financeira', async ({ page }) => {
  const api = await createRequest.newContext({ baseURL: apiBase });
  const loginResponse = await api.post('auth/login', {
    data: { email: 'admin@rfbalance.local', password: 'e2e-admin-password-2026' },
  });
  expect(loginResponse.ok()).toBeTruthy();
  const state = await api.storageState();
  const csrf = state.cookies.find((cookie) => cookie.name === 'rfb_csrf')?.value;
  expect(csrf).toBeTruthy();
  const headers = { 'X-CSRF-Token': csrf as string };

  const company = await api.post('companies', {
    headers,
    data: { legal_name: 'Empresa E2E', trade_name: 'Empresa E2E' },
  });
  const companyId = (await company.json()).id as number;
  const consultant = await api.post('collaborators', {
    headers,
    data: {
      company_id: companyId,
      unit_id: null,
      full_name: 'Consultora E2E',
      document: '529.982.247-25',
      tax_regime: 'CLT',
      roles: [{ role: 'CONSULTOR', valid_from: '2026-01-01' }],
    },
  });
  expect(consultant.ok()).toBeTruthy();
  const finalizer = await api.post('users', {
    headers,
    data: {
      email: 'finalizacao-e2e@rfbalance.local',
      full_name: 'Finalização E2E',
      roles: ['OPERACIONAL'],
      collaborator: {
        company_id: companyId,
        unit_id: null,
        document: '390.533.447-05',
        tax_regime: 'CLT',
        function: 'FINALIZACAO',
        valid_from: '2026-01-01',
      },
    },
  });
  const finalizerBody = await finalizer.json();
  const finance = await api.post('users', {
    headers,
    data: {
      email: 'financeiro-e2e@rfbalance.local',
      full_name: 'Financeiro E2E',
      roles: ['FINANCEIRO'],
    },
  });
  const financeBody = await finance.json();
  const account = await api.post('receiving-accounts', {
    headers,
    data: { label: 'Conta E2E' },
  });
  expect(account.ok()).toBeTruthy();
  await api.dispose();

  await login(page, 'finalizacao-e2e@rfbalance.local', finalizerBody.temporary_password);
  await page.goto('/proposals');
  await page.getByRole('button', { name: 'Nova proposta' }).click();
  const proposalDialog = page.getByRole('dialog', { name: 'Nova proposta' });
  await proposalDialog.getByLabel('Consultor').click();
  await page.getByRole('option', { name: 'Consultora E2E' }).click();
  await proposalDialog.getByLabel('Cliente *', { exact: true }).fill('Cliente E2E Aprovação');
  await proposalDialog.getByLabel('CPF ou CNPJ do cliente').fill('11144477735');
  await proposalDialog.getByLabel('Valor da operação').fill('1000000');
  await proposalDialog.getByLabel('TPS (%)').fill('10');
  await proposalDialog.getByLabel('Valor pago').fill('100000');
  await proposalDialog.getByLabel('Conta que recebeu').click();
  await page.getByRole('option', { name: 'Conta E2E' }).click();
  await proposalDialog.locator('input[type="file"]').setInputFiles({
    name: 'comprovante-e2e.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 comprovante E2E'),
  });
  await proposalDialog.getByRole('button', { name: 'Cadastrar' }).click();
  await expect(page.getByText('Proposta cadastrada')).toBeVisible();

  await page.getByLabel('Aprovação da proposta de Cliente E2E Aprovação').click();
  await page.getByRole('button', { name: 'Enviar para aprovação' }).click();
  await expect(page.getByText('Proposta enviada')).toBeVisible();

  await page.getByRole('button', { name: 'Menu do usuário' }).click();
  await page.getByRole('menuitem', { name: 'Sair' }).click();
  await login(page, 'financeiro-e2e@rfbalance.local', financeBody.temporary_password);

  await page.goto('/proposals');
  await expect(page.getByText('Cliente E2E Aprovação')).toHaveCount(0);
  await page.goto('/proposal-approvals');
  await expect(page.getByText(/Cliente E2E Aprovação/)).toBeVisible();
  await page.getByRole('button', { name: 'Analisar' }).click();
  await page.getByLabel('Visualizar comprovante').click();
  const preview = page.getByTitle('Pré-visualização de comprovante-e2e.pdf');
  await expect(preview).toHaveAttribute('src', /preview=true/);
  const proofResponse = await page.request.get(await preview.getAttribute('src') as string);
  expect(proofResponse.status()).toBe(200);
  expect(proofResponse.headers()['content-type']).toContain('application/pdf');
  await page.getByRole('button', { name: 'Fechar pré-visualização' }).click();
  await expect(preview).toBeHidden();
  await page.getByRole('button', { name: 'Aprovar e reconhecer valores' }).click();
  await page.getByRole('button', { name: 'Confirmar aprovação' }).click();
  await expect(page.getByText('Proposta aprovada')).toBeVisible();
  await expect(page.getByText('Nenhuma proposta aguardando aprovação.')).toBeVisible();

  await page.getByRole('link', { name: 'Ir para o dashboard' }).click();
  await expect(page).toHaveURL(/\/$/);
});
