import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CommissionRulesPage } from '@/features/commission-rules/pages/CommissionRulesPage';

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ usuario: { id: 99 }, pode: () => true, carregando: false }),
}));

const VERSAO = {
  id: 1,
  strategy: 'STANDARD_CONSULTANT',
  version: '2026.1',
  name: 'Consultor padrão MEI',
  status: 'ACTIVE',
  valid_from: '2000-01-01',
  valid_to: null,
  reason: 'Configuração inicial',
  created_at: '2026-08-14T12:00:00Z',
  created_by: null,
  activated_at: null,
  activated_by: null,
  rules: [
    { id: 1, tax_regime: 'MEI', tps_min: '0.000000', tps_max: '25.000000', percentage: '6.000000', sort_order: 1 },
    { id: 2, tax_regime: 'MEI', tps_min: '25.000000', tps_max: '30.000000', percentage: '8.000000', sort_order: 2 },
    { id: 3, tax_regime: 'MEI', tps_min: '30.000000', tps_max: '35.000000', percentage: '10.000000', sort_order: 3 },
    { id: 4, tax_regime: 'MEI', tps_min: '35.000000', tps_max: null, percentage: '12.000000', sort_order: 4 },
  ],
};

const ESTRATEGIAS = [
  { id: 1, strategy: 'SCALED_CONSULTANT', version: '2026.1', name: 'Consultor MEI Escalonado', status: 'ACTIVE', valid_from: '2000-01-01', valid_to: null, reason: 'Inicial', created_at: '2026-08-14T12:00:00Z', created_by: null, activated_at: null, activated_by: null, config: { display_mode: 'WEEKLY', production_ranges: [{ min: '0', max: '75000', percentages: ['8', '6', '4', '2'] }, { min: '75000', max: '175000', percentages: ['10', '8', '6', '4'] }, { min: '175000', max: null, percentages: ['11.5', '9.5', '7.5', '5.5'] }] } },
  { id: 2, strategy: 'COMMERCIAL_LEADER', version: '2026.1', name: 'Líder comercial', status: 'ACTIVE', valid_from: '2000-01-01', valid_to: null, reason: 'Inicial', created_at: '2026-08-14T12:00:00Z', created_by: null, activated_at: null, activated_by: null, config: { mei_min_tps: '25', mei_percentage: '3', clt_percentage: '0' } },
  { id: 3, strategy: 'GENERAL_MEI_LEADER', version: '2026.1', name: 'Líder MEI geral', status: 'ACTIVE', valid_from: '2000-01-01', valid_to: null, reason: 'Inicial', created_at: '2026-08-14T12:00:00Z', created_by: null, activated_at: null, activated_by: null, config: { base_percentage: '35', tiers: [{ min: '0', max: '500000', percentage: '1.2' }] } },
  { id: 4, strategy: 'FINALIZER', version: '2026.1', name: 'Finalização', status: 'ACTIVE', valid_from: '2000-01-01', valid_to: null, reason: 'Inicial', created_at: '2026-08-14T12:00:00Z', created_by: null, activated_at: null, activated_by: null, config: { threshold_amount: '70000', fixed_amount: '500', excess_percentage: '0.45' } },
  { id: 5, strategy: 'FINALIZATION_LEADER', version: '2026.1', name: 'Líder de Finalização', status: 'ACTIVE', valid_from: '2000-01-01', valid_to: null, reason: 'Inicial', created_at: '2026-08-14T12:00:00Z', created_by: null, activated_at: null, activated_by: null, config: { mei_percentage: '0.9', clt_percentage: '0.9' } },
];

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } });
}

function renderizar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<MantineProvider><QueryClientProvider client={client}><CommissionRulesPage /></QueryClientProvider></MantineProvider>);
}

describe('CommissionRulesPage', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => Promise.resolve(json(String(url).includes('commission-strategy-configs') ? ESTRATEGIAS : [VERSAO])));
  });

  afterEach(() => vi.mocked(globalThis.fetch).mockRestore());

  it('mostra a versão ativa e suas faixas por regime', async () => {
    renderizar();
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByText(/2026\.1 — Consultor padrão/i));
    expect(await screen.findByText('Função Consultor padrão')).toBeInTheDocument();
    expect(screen.getByText(/independentemente do regime MEI ou CLT/i)).toBeInTheDocument();
    expect(screen.getByText('12%')).toBeInTheDocument();
  });

  it('copia a versão ativa para um novo rascunho editável', async () => {
    renderizar();
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByRole('button', { name: /nova versão/i }));
    expect(await screen.findByRole('dialog', { name: /nova versão das regras/i })).toBeInTheDocument();
    expect(screen.getAllByLabelText(/TPS mínimo MEI/i)).toHaveLength(4);
    expect(screen.queryByLabelText(/Percentual CLT/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar rascunho/i })).toBeDisabled();
  });

  it('mantém os limites vizinhos sincronizados', async () => {
    renderizar();
    const usuario = userEvent.setup();
    await usuario.click(await screen.findByRole('button', { name: /nova versão/i }));
    const maximos = await screen.findAllByLabelText(/TPS máximo MEI/i);
    await usuario.clear(maximos[0]!);
    await usuario.type(maximos[0]!, '26,5');
    const minimos = screen.getAllByLabelText(/TPS mínimo MEI/i) as HTMLInputElement[];
    expect(minimos[1]!.value).toBe('26,5');
  });

  it('apresenta os demais percentuais documentados por estratégia', async () => {
    renderizar();
    const usuario = userEvent.setup();
    expect(await screen.findByText('11,5%')).toBeInTheDocument();
    await usuario.click(screen.getByRole('tab', { name: /lideranças/i }));
    expect(screen.getByText(/35% da produção proporcional/i)).toBeInTheDocument();
    expect(screen.getByText('1,2%')).toBeInTheDocument();
    await usuario.click(screen.getByRole('tab', { name: /finalização e BKO/i }));
    expect(screen.getByText(/R\$ 500,00 \+ 0,45%/i)).toBeInTheDocument();
    expect(screen.getAllByText(/0,9%/i).length).toBeGreaterThan(0);
  });

  it('abre a correção versionada das faixas escalonadas com máscaras legíveis', async () => {
    renderizar();
    const usuario = userEvent.setup();
    const botoes = await screen.findAllByRole('button', { name: /corrigir em nova versão/i });
    await usuario.click(botoes[0]!);
    expect(await screen.findByRole('dialog', { name: /corrigir consultor MEI escalonado/i })).toBeInTheDocument();
    expect(screen.getAllByDisplayValue('75.000,00')).toHaveLength(2);
    expect(screen.getByDisplayValue('11,5')).toBeInTheDocument();
  });
});
