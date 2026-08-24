import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { OperationsPage } from '@/features/operations/pages/OperationsPage';

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ pode: () => true }),
}));

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const operationStatus = {
  backup: {
    enabled: true,
    prefix: 'backups/database',
    retention_days: 30,
    schedule_hour_utc: 6,
    versioning_enabled: true,
    local_replica_enabled: true,
    last_backup: {
      key: 'backups/database/2026/08/21/database.sql.gz',
      created_at: '2026-08-21T13:47:00Z',
      compressed_bytes: 8192,
      sha256: 'a'.repeat(64),
      verified: true,
    },
  },
  integrity_checks: [{
    check_type: 'team_assignment_overlaps',
    status: 'PASS',
    count: 0,
    checked_at: '2026-08-21T13:46:00Z',
  }],
};

describe('OperationsPage', () => {
  afterEach(() => vi.restoreAllMocks());

  it('mostra continuidade real e permite executar backup manual', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((_url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve(json({
          key: 'backups/database/2026/08/21/manual.sql.gz',
          created_at: '2026-08-21T14:00:00Z',
          compressed_bytes: 9216,
          sha256: 'b'.repeat(64),
          removed_by_retention: 0,
          local_replica_created: true,
        }, 201));
      }
      return Promise.resolve(json(operationStatus));
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MantineProvider><Notifications /><QueryClientProvider client={client}>
      <OperationsPage />
    </QueryClientProvider></MantineProvider>);

    expect(await screen.findByText('Verificado após envio')).toBeInTheDocument();
    expect(screen.getByText('Sobreposição de equipes')).toBeInTheDocument();
    expect(screen.getByText('Íntegro')).toBeInTheDocument();
    expect(screen.getByText('Versionamento ativo')).toBeInTheDocument();
    expect(screen.getByText('Réplica local ativa')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Executar backup agora' }));
    expect(await screen.findByText('Backup concluído e verificado')).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/admin/operations/backups',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
