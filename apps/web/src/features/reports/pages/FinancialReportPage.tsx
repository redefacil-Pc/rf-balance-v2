import { Alert, Badge, Button, Card, Group, SimpleGrid, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { IconFileSpreadsheet, IconFileTypePdf } from '@tabler/icons-react';
import { useState } from 'react';

import { FinancialReportDetailModal } from '@/features/reports/components/FinancialReportDetailModal';
import { useFinancialReport } from '@/features/reports/queries/useFinancialReport';
import type { Period } from '@/features/settlements/queries/useSettlements';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import type { FinancialReportBeneficiary } from '@/shared/types/commissions';

function currentPeriod(): Period {
  const value = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const today = new Date(`${dataLocalHoje()}T12:00:00`);
  const start = new Date(today);
  start.setDate(today.getDate() - ((today.getDay() + 2) % 7));
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { period_start: value(start), period_end: value(end) };
}

function Indicator({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <Card withBorder><Text size="xs" c="dimmed" tt="uppercase" fw={700}>{label}</Text>
    <Text size="xl" fw={700} mt={4}>{formatarMoeda(value)}</Text>
    <Text size="xs" c="dimmed">{detail}</Text></Card>;
}

const strategyLabels: Record<string, string> = {
  STANDARD_CONSULTANT: 'Consultor padrão', SCALED_CONSULTANT: 'Consultor escalonado',
  COMMERCIAL_LEADER: 'Líder comercial', GENERAL_MEI_LEADER: 'Líder MEI geral',
  FINALIZER: 'Finalização', FINALIZATION_LEADER: 'Líder finalização', BKO: 'BKO',
};
const statusLabels = { PENDING: 'Pendente', DEFERRED: 'Adiado', PAID: 'Pago' };

const leaderStrategies = new Set(['COMMERCIAL_LEADER', 'GENERAL_MEI_LEADER', 'FINALIZATION_LEADER']);
const consultantStrategies = new Set(['STANDARD_CONSULTANT', 'SCALED_CONSULTANT']);

type Sector = 'CONSULTANTS' | 'FINALIZATION' | 'BKO' | 'LEADERS' | 'OTHER';

function sectorOf(item: FinancialReportBeneficiary): Sector {
  if (item.strategies.some((strategy) => leaderStrategies.has(strategy))) return 'LEADERS';
  if (item.strategies.some((strategy) => consultantStrategies.has(strategy))) return 'CONSULTANTS';
  if (item.strategies.includes('FINALIZER')) return 'FINALIZATION';
  if (item.strategies.includes('BKO')) return 'BKO';
  return 'OTHER';
}

function BeneficiarySector({ title, description, items, onDetail }: {
  title: string;
  description: string;
  items: FinancialReportBeneficiary[];
  onDetail: (item: FinancialReportBeneficiary) => void;
}) {
  return <Card withBorder padding={0}>
    <Group justify="space-between" px="md" py="sm">
      <div><Title order={3} size="h5">{title}</Title><Text size="xs" c="dimmed">{description}</Text></div>
      <Badge variant="light" color="gray">{items.length} colaborador(es)</Badge>
    </Group>
    {items.length === 0
      ? <Text size="sm" c="dimmed" px="md" pb="md">Nenhum valor neste setor para o período.</Text>
      : <Table.ScrollContainer minWidth={1250}><Table striped verticalSpacing="sm">
        <Table.Thead><Table.Tr><Table.Th>Beneficiário</Table.Th><Table.Th>Função/regra</Table.Th>
          <Table.Th ta="right">Automática</Table.Th><Table.Th ta="right">Manual</Table.Th>
          <Table.Th ta="right">Calculada</Table.Th><Table.Th ta="right">Acum. anterior</Table.Th>
          <Table.Th ta="right">Desconto</Table.Th><Table.Th ta="right">Adiado</Table.Th>
          <Table.Th ta="right">Pago</Table.Th><Table.Th ta="right">A pagar</Table.Th>
          <Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead>
        <Table.Tbody>{items.map((item) => <Table.Tr key={item.beneficiary_id}>
          <Table.Td><Text size="sm" fw={600}>{item.beneficiary_name}</Text></Table.Td>
          <Table.Td>{item.strategies.map((strategy) => <Badge key={strategy} variant="light" mr={4}>
            {strategyLabels[strategy] ?? strategy}
          </Badge>)}</Table.Td>
          {[item.automatic_amount, item.manual_amount, item.calculated_amount, item.carryover_amount,
            item.discount_amount, item.deferred_amount, item.paid_amount, item.payable_amount]
            .map((value, index) => <Table.Td key={index} ta="right">{formatarMoeda(value)}</Table.Td>)}
          <Table.Td>{item.status
            ? <Badge variant="light">{statusLabels[item.status]}</Badge>
            : <Badge color="gray" variant="light">Não gerado</Badge>}</Table.Td>
          <Table.Td><Button size="xs" variant="subtle" onClick={() => onDetail(item)}>Detalhar</Button></Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer>}
  </Card>;
}

export function FinancialReportPage() {
  const [period, setPeriod] = useState(currentPeriod);
  const [selected, setSelected] = useState<FinancialReportBeneficiary | null>(null);
  const query = useFinancialReport(period);
  const summary = query.data?.summary;
  const beneficiaries = query.data?.beneficiaries ?? [];
  const sectors = {
    CONSULTANTS: beneficiaries.filter((item) => sectorOf(item) === 'CONSULTANTS'),
    FINALIZATION: beneficiaries.filter((item) => sectorOf(item) === 'FINALIZATION'),
    BKO: beneficiaries.filter((item) => sectorOf(item) === 'BKO'),
    LEADERS: beneficiaries.filter((item) => sectorOf(item) === 'LEADERS'),
    OTHER: beneficiaries.filter((item) => sectorOf(item) === 'OTHER'),
  };
  const exportParams = new URLSearchParams({
    period_start: period.period_start,
    period_end: period.period_end,
  }).toString();
  return <Stack gap="lg">
    <Group justify="space-between" align="flex-end"><div><Title order={2} size="h3">Relatório financeiro de comissões</Title>
      <Text size="sm" c="dimmed">Recebimentos, produção, comissões e resultado líquido no mesmo período.</Text></div>
      <Group gap="xs"><Button component="a" variant="default" leftSection={<IconFileTypePdf size={16} />}
        href={`/api/v1/commission-financial-report/export.pdf?${exportParams}`} download>Baixar PDF</Button>
        <Button component="a" variant="default" leftSection={<IconFileSpreadsheet size={16} />}
          href={`/api/v1/commission-financial-report/export.xlsx?${exportParams}`} download>Exportar XLSX</Button></Group>
    </Group>
    <Card withBorder><Group align="end"><TextInput type="date" label="Início" value={period.period_start}
      onChange={(event) => setPeriod({ ...period, period_start: event.currentTarget.value })} />
      <TextInput type="date" label="Fim" value={period.period_end}
        onChange={(event) => setPeriod({ ...period, period_end: event.currentTarget.value })} />
    </Group></Card>
    {summary && <>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <Indicator label="Faturamento reconhecido" value={summary.recognized_revenue}
          detail={`${formatarMoeda(summary.gross_revenue)} bruto − ${formatarMoeda(summary.receipt_reversals)} estornado`} />
        <Indicator label="Produção reconhecida" value={summary.recognized_production}
          detail="Operações liberadas proporcionalmente" />
        <Indicator label="Comissões calculadas" value={summary.total_commissions}
          detail="Automáticas + lançamentos manuais" />
        <Indicator label="Faturamento líquido" value={summary.net_billing}
          detail="Faturamento reconhecido − comissões" />
      </SimpleGrid>
      <Card withBorder><Title order={3} size="h5" mb="md">Composição das comissões</Title>
        <SimpleGrid cols={{ base: 2, md: 5 }}>
          <Indicator label="Consultores" value={summary.consultant_commissions} detail="Padrão e escalonado" />
          <Indicator label="Liderança" value={summary.leader_commissions} detail="Comercial e MEI geral" />
          <Indicator label="Finalização" value={summary.finalization_commissions} detail="Automática + bônus manual" />
          <Indicator label="Líder finalização" value={summary.finalization_leader_commissions} detail="Comissão da equipe" />
          <Indicator label="BKO" value={summary.bko_commissions} detail="Lançamentos manuais" />
        </SimpleGrid>
      </Card>
      <Card withBorder><Title order={3} size="h5" mb="md">Situação dos fechamentos</Title>
        <SimpleGrid cols={{ base: 2, md: 5 }}>
          <Indicator label="Bônus" value={summary.bonuses} detail="Acréscimos nos fechamentos" />
          <Indicator label="Descontos" value={summary.discounts} detail="Reduções definitivas" />
          <Indicator label="Adiado" value={summary.deferred} detail="Vai ao próximo período" />
          <Indicator label="Pago" value={summary.paid} detail="Pagamento já registrado" />
          <Indicator label="A pagar" value={summary.payable} detail="Saldo pendente atual" />
        </SimpleGrid>
      </Card>
    </>}
    <Alert color="blue" title="Critério financeiro">
      O faturamento reconhecido considera recebimentos aprovados menos estornos do período.
      O faturamento líquido deduz as comissões calculadas, independentemente de já terem sido pagas.
    </Alert>
    <EstadoDaLista carregando={query.isPending} erro={query.error ?? null}
      vazio={beneficiaries.length === 0} mensagemVazio="Nenhum valor encontrado no período.">
      <Stack gap="md">
        <BeneficiarySector title="Consultores" description="Consultor padrão e consultor escalonado"
          items={sectors.CONSULTANTS} onDetail={setSelected} />
        <BeneficiarySector title="Finalização" description="Comissão automática e bônus de Finalização"
          items={sectors.FINALIZATION} onDetail={setSelected} />
        <BeneficiarySector title="BKO" description="Lançamentos manuais dos colaboradores de BKO"
          items={sectors.BKO} onDetail={setSelected} />
        <BeneficiarySector title="Lideranças" description="Líder comercial, MEI geral e de Finalização"
          items={sectors.LEADERS} onDetail={setSelected} />
        {sectors.OTHER.length > 0 && <BeneficiarySector title="Outros valores"
          description="Fechamentos sem estratégia identificada no período"
          items={sectors.OTHER} onDetail={setSelected} />}
      </Stack>
    </EstadoDaLista>
    <FinancialReportDetailModal beneficiary={selected} period={period} onClose={() => setSelected(null)} />
  </Stack>;
}
