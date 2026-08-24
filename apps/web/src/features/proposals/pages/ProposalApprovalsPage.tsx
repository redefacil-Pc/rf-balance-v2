import {
  Badge,
  Button,
  Card,
  Group,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { IconClipboardCheck, IconRefresh } from '@tabler/icons-react';
import { useState } from 'react';

import { ProposalApprovalModal } from '@/features/proposals/components/ProposalApprovalModal';
import { useProposals } from '@/features/proposals/queries/useProposals';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { PageHeader } from '@/shared/components/PageHeader';
import { formatarMoeda } from '@/shared/formatters/currency';
import type { Proposal } from '@/shared/types/commercial';

function formatarData(data: string): string {
  return data.split('-').reverse().join('/');
}

export function proximaProposta(
  propostas: Proposal[],
  decididaId: number,
): Proposal | null {
  const indice = propostas.findIndex((item) => item.id === decididaId);
  const restantes = propostas.filter((item) => item.id !== decididaId);
  return restantes[indice] ?? restantes[0] ?? null;
}

/** Fila de trabalho do Financeiro: exibe apenas propostas enviadas e ainda não decididas. */
export function ProposalApprovalsPage() {
  const consulta = useProposals({ approval_status: 'SUBMITTED' });
  const [selecionada, setSelecionada] = useState<Proposal | null>(null);
  const propostas = (consulta.data?.pages ?? []).flatMap((pagina) => pagina.items);
  const avancar = (decididaId: number) => {
    setSelecionada(proximaProposta(propostas, decididaId));
  };

  return (
    <Stack gap="lg">
      <PageHeader
        eyebrow="Financeiro"
        icon={IconClipboardCheck}
        title="Fila de aprovação"
        description="Confira a operação e o comprovante antes de reconhecer os valores financeiros."
        badge={!consulta.isPending
          ? `${propostas.length} pendente${propostas.length === 1 ? '' : 's'}`
          : undefined}
        badgeColor={propostas.length > 0 ? 'orange' : 'gray'}
        actions={
          <Button
            variant="default"
            leftSection={<IconRefresh size={16} />}
            loading={consulta.isFetching}
            onClick={() => void consulta.refetch()}
          >
            Atualizar fila
          </Button>
        }
      />

      <Card withBorder padding={0} className="rf-data-card">
        <EstadoDaLista
          carregando={consulta.isPending}
          erro={consulta.error ?? null}
          vazio={propostas.length === 0}
          onTentarNovamente={() => void consulta.refetch()}
          mensagemVazio="Nenhuma proposta aguardando aprovação."
        >
          <Table.ScrollContainer minWidth={850}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Data</Table.Th>
                  <Table.Th>Proposta / cliente</Table.Th>
                  <Table.Th>Consultor</Table.Th>
                  <Table.Th ta="right">Operação</Table.Th>
                  <Table.Th ta="right">Comissão da empresa</Table.Th>
                  <Table.Th>Situação</Table.Th>
                  <Table.Th>Ação</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {propostas.map((proposta) => (
                  <Table.Tr key={proposta.id}>
                    <Table.Td>{formatarData(proposta.business_date)}</Table.Td>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        #{proposta.id} · {proposta.customer_name}
                      </Text>
                      {proposta.external_id && (
                        <Text size="xs" c="dimmed">
                          {proposta.external_id}
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>{proposta.consultant_name}</Table.Td>
                    <Table.Td ta="right">{formatarMoeda(proposta.operation_amount)}</Table.Td>
                    <Table.Td ta="right">
                      <Text fw={500} size="sm">
                        {formatarMoeda(proposta.company_commission_amount)}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color="yellow" variant="light">
                        Aguardando financeiro
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconClipboardCheck size={15} />}
                        onClick={() => setSelecionada(proposta)}
                      >
                        Analisar
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </EstadoDaLista>
      </Card>

      {consulta.hasNextPage && (
        <Group justify="center">
          <Button
            variant="default"
            loading={consulta.isFetchingNextPage}
            onClick={() => void consulta.fetchNextPage()}
          >
            Carregar mais
          </Button>
        </Group>
      )}

      <ProposalApprovalModal
        proposta={selecionada}
        onFechar={() => setSelecionada(null)}
        onDecidida={avancar}
      />
    </Stack>
  );
}
