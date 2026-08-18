import { MantineProvider } from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ActiveTeamsCard } from '@/features/teams/components/ActiveTeamsCard';

function json(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('ActiveTeamsCard', () => {
  afterEach(() => vi.restoreAllMocks());

  it('agrupa os integrantes por líder e tipo de vínculo', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(json([
      {
        id: 1, member_id: 10, member_name: 'Carla Consultora', leader_id: 20,
        leader_name: 'Bruno Líder', assignment_type: 'COMERCIAL',
        start_date: '2026-01-01', end_date: null,
      },
      {
        id: 2, member_id: 11, member_name: 'Diego Escalonado', leader_id: 20,
        leader_name: 'Bruno Líder', assignment_type: 'COMERCIAL',
        start_date: '2026-02-01', end_date: null,
      },
      {
        id: 3, member_id: 12, member_name: 'Ana Operacional', leader_id: 30,
        leader_name: 'Fábio Líder Final', assignment_type: 'FINALIZACAO',
        start_date: '2026-03-01', end_date: null,
      },
    ]));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={client}>
          <ActiveTeamsCard />
        </QueryClientProvider>
      </MantineProvider>,
    );

    expect(await screen.findByText('Bruno Líder')).toBeInTheDocument();
    expect(screen.getByText('Fábio Líder Final')).toBeInTheDocument();
    expect(screen.getByText('2 integrantes')).toBeInTheDocument();
    expect(screen.getByText('1 integrante')).toBeInTheDocument();
    expect(screen.getByText('Carla Consultora')).toBeInTheDocument();
    expect(screen.getByText('Diego Escalonado')).toBeInTheDocument();
    expect(screen.getByText('Ana Operacional')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/assignments/active?reference_date='),
      expect.anything(),
    );
  });
});
