import { Button, Card, Group, Stack, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconFileText, IconPlus } from '@tabler/icons-react';
import { useCallback, useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { CancelProposalModal } from '@/features/proposals/components/CancelProposalModal';
import { ProposalApprovalModal } from '@/features/proposals/components/ProposalApprovalModal';
import { ProposalEditModal } from '@/features/proposals/components/ProposalEditModal';
import { ProposalFilters } from '@/features/proposals/components/ProposalFilters';
import { ProposalFormModal } from '@/features/proposals/components/ProposalFormModal';
import { ProposalTable } from '@/features/proposals/components/ProposalTable';
import {
  useProposals,
  type ProposalFilters as Filtros,
} from '@/features/proposals/queries/useProposals';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { PageHeader } from '@/shared/components/PageHeader';
import { useFiltrosNaUrl } from '@/shared/hooks/useFiltrosNaUrl';
import type { Proposal, StatusDaProposta } from '@/shared/types/commercial';

function lerFiltros(params: URLSearchParams): Filtros {
  const consultor = params.get('consultant_id');

  return {
    status: (params.get('status') as StatusDaProposta | null) ?? undefined,
    consultant_id: consultor ? Number(consultor) : undefined,
    external_id: params.get('external_id') ?? undefined,
    customer_name: params.get('customer_name') ?? undefined,
    business_date_from: params.get('business_date_from') ?? undefined,
    business_date_to: params.get('business_date_to') ?? undefined,
  };
}

export function ProposalsPage() {
  const { pode, usuario } = useAuth();
  const [filtros, aplicarFiltros] = useFiltrosNaUrl<Filtros>(useCallback(lerFiltros, []));
  const [modalAberto, modal] = useDisclosure(false);
  const [emEdicao, setEmEdicao] = useState<Proposal | null>(null);
  const [emCancelamento, setEmCancelamento] = useState<Proposal | null>(null);
  const [emAprovacao, setEmAprovacao] = useState<Proposal | null>(null);

  const consulta = useProposals({ ...filtros, exclude_approval_status: 'SUBMITTED' });
  const propostas = (consulta.data?.pages ?? []).flatMap((pagina) => pagina.items);
  const podeEscrever = pode('proposals:write');
  const podeAprovar = pode('proposals:approve');
  const podeDeclararPagamento =
    pode('receipts:write') && !(usuario?.roles.includes('ADMIN') ?? false);

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Operação comercial"
        icon={IconFileText}
        title="Propostas"
        description="Cadastre operações, acompanhe seus valores e mantenha cada etapa financeira organizada."
        actions={podeEscrever ? (
          <Button leftSection={<IconPlus size={16} />} onClick={modal.open}>
            Nova proposta
          </Button>
        ) : undefined}
      />

      <Card withBorder padding="md" className="rf-toolbar">
        <ProposalFilters valor={filtros} onChange={aplicarFiltros} />
      </Card>

      <Card withBorder padding={0} className="rf-data-card">
        <EstadoDaLista
          carregando={consulta.isPending}
          erro={consulta.error ?? null}
          vazio={propostas.length === 0}
          onTentarNovamente={() => void consulta.refetch()}
          mensagemVazio="Nenhuma proposta encontrada. Ajuste os filtros ou cadastre a primeira."
        >
          <ProposalTable
            propostas={propostas}
            podeEscrever={podeEscrever}
            podeVerPii={pode('proposals:read_pii')}
            podeAprovar={podeAprovar}
            onEditar={setEmEdicao}
            onCancelar={setEmCancelamento}
            onAprovacao={setEmAprovacao}
          />
        </EstadoDaLista>
      </Card>

      {consulta.hasNextPage && (
        <Group justify="center">
          <Button
            variant="default"
            onClick={() => void consulta.fetchNextPage()}
            loading={consulta.isFetchingNextPage}
          >
            Carregar mais
          </Button>
        </Group>
      )}

      {propostas.length > 0 && (
        <Text size="xs" c="dimmed" ta="center">
          {propostas.length} proposta(s) carregada(s)
          {consulta.hasNextPage ? ' — há mais registros' : ''}
        </Text>
      )}

      <ProposalFormModal
        aberto={modalAberto}
        podeDeclararPagamento={podeDeclararPagamento}
        onFechar={modal.close}
      />
      <ProposalEditModal proposta={emEdicao} onFechar={() => setEmEdicao(null)} />
      <CancelProposalModal
        proposta={emCancelamento}
        onFechar={() => setEmCancelamento(null)}
      />
      <ProposalApprovalModal proposta={emAprovacao} onFechar={() => setEmAprovacao(null)} />
    </Stack>
  );
}
