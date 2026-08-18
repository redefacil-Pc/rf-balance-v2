import { Badge, Card, Group, Modal, SimpleGrid, Stack, Table, Text } from '@mantine/core';

import { useFinancialReportDetails } from '@/features/reports/queries/useFinancialReport';
import type { Period } from '@/features/settlements/queries/useSettlements';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import type { FinancialReportBeneficiary } from '@/shared/types/commissions';

interface Props {
  beneficiary: FinancialReportBeneficiary | null;
  period: Period;
  onClose: () => void;
}

const strategyLabels: Record<string, string> = {
  STANDARD_CONSULTANT: 'Consultor padrão',
  SCALED_CONSULTANT: 'Consultor escalonado',
  COMMERCIAL_LEADER: 'Líder comercial',
  GENERAL_MEI_LEADER: 'Líder MEI geral',
  FINALIZER: 'Finalização',
  FINALIZATION_LEADER: 'Líder de finalização',
  BKO: 'BKO',
};

const metricColors = {
  production: 'var(--mantine-color-teal-6)',
  received: 'var(--mantine-color-blue-6)',
  commission: 'var(--mantine-color-orange-6)',
  deferred: 'var(--mantine-color-yellow-6)',
};

function percentage(value: string | null): string {
  if (value === null) return '—';
  return `${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function Metric({ label, value, detail, color }: {
  label: string;
  value: string;
  detail: string;
  color: string;
}) {
  return <Card withBorder radius="md" padding="md" style={{ borderLeft: `5px solid ${color}` }}>
    <Text size="xs" fw={700} tt="uppercase" c="dimmed">{label}</Text>
    <Text size="xl" fw={700} mt={3}>{formatarMoeda(value)}</Text>
    <Text size="xs" c="dimmed" mt={2}>{detail}</Text>
  </Card>;
}

export function FinancialReportDetailModal({ beneficiary, period, onClose }: Props) {
  const query = useFinancialReportDetails(beneficiary?.beneficiary_id ?? null, period);
  const items = query.data?.items ?? [];
  const summary = query.data?.summary;
  const roles = beneficiary?.strategies.map((item) => strategyLabels[item] ?? item).join(' · ');
  return <Modal opened={beneficiary !== null} onClose={onClose}
    title={<div><Text fw={700} size="lg">{beneficiary?.beneficiary_name ?? ''}</Text>
      <Text size="xs" c="dimmed" tt="uppercase">{roles}</Text></div>}
    size="min(1180px, calc(100vw - 32px))" centered>
    <EstadoDaLista carregando={query.isPending} erro={query.error ?? null}
      vazio={items.length === 0} mensagemVazio="Nenhum lançamento encontrado no período.">
      <Stack gap="lg">
        {summary && <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="sm">
          <Metric label="Produção reconhecida" value={summary.recognized_production}
            detail="Produção liberada pelos recebimentos" color={metricColors.production} />
          <Metric label="Recebido no período" value={summary.received_amount}
            detail="Valor elegível reconhecido" color={metricColors.received} />
          <Metric label="Comissão" value={summary.commission_amount}
            detail="Créditos menos estornos" color={metricColors.commission} />
          <Metric label="Valor adiado" value={summary.deferred_amount}
            detail={summary.deferred_amount === '0.00' ? 'Sem adiamento no período' : 'Vai para o próximo fechamento'}
            color={metricColors.deferred} />
        </SimpleGrid>}

        <div><Text fw={700} size="lg" mb="sm">Vendas e lançamentos do período</Text>
          <Table striped verticalSpacing="sm" layout="fixed">
            <Table.Thead><Table.Tr><Table.Th>Cliente / origem</Table.Th>
              <Table.Th w={150} ta="right">Produção</Table.Th>
              <Table.Th w={145} ta="right">Recebido</Table.Th>
              <Table.Th w={105} ta="right">% recebido</Table.Th>
              <Table.Th w={90} ta="right">TPS</Table.Th>
              <Table.Th w={130} ta="right">Comissão</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{items.map((item, index) => <Table.Tr key={`${item.source}-${index}`}>
              <Table.Td><Group gap="xs" wrap="nowrap"><div>
                <Text size="sm" fw={600}>{item.customer_name ?? item.description}</Text>
                <Text size="xs" c="dimmed">
                  {item.proposal_id === null
                    ? `${item.competence_date.split('-').reverse().join('/')} · lançamento manual`
                    : `Proposta #${item.proposal_id}${item.proposal_external_id ? ` · ${item.proposal_external_id}` : ''} · recebimento #${item.receipt_id}`}
                </Text>
                <Group gap={5} mt={4}><Badge size="xs" variant="light"
                  color={item.source === 'MANUAL' ? 'orange' : 'blue'}>
                  {item.source === 'MANUAL' ? 'Manual' : 'Automática'}
                </Badge><Text size="xs" c="dimmed">{strategyLabels[item.strategy] ?? item.strategy}</Text></Group>
              </div></Group></Table.Td>
              <Table.Td ta="right">{item.source === 'MANUAL' ? '—' : formatarMoeda(item.recognized_production)}</Table.Td>
              <Table.Td ta="right">{item.source === 'MANUAL' ? '—' : <>
                <Text size="sm" fw={600} c={item.entry_type === 'DEBIT' ? 'red' : 'teal'}>
                  {formatarMoeda(item.received_amount)}
                </Text><Text size="xs" c="dimmed">Recebimento #{item.receipt_id}</Text>
              </>}</Table.Td>
              <Table.Td ta="right">{percentage(item.received_percentage)}</Table.Td>
              <Table.Td ta="right">{percentage(item.tps_percentage)}</Table.Td>
              <Table.Td ta="right"><Text fw={700} c={item.entry_type === 'DEBIT' ? 'red' : 'violet'}>
                {formatarMoeda(item.amount)}
              </Text></Table.Td>
            </Table.Tr>)}</Table.Tbody>
          </Table>
        </div>
      </Stack>
    </EstadoDaLista>
  </Modal>;
}
