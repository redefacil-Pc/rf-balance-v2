import { Alert, Badge, Button, Card, Group, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { BkoEntryModal, FinalizationEntryModal } from '@/features/settlements/components/BkoEntryModal';
import { SettlementActionModal } from '@/features/settlements/components/SettlementActionModal';
import { SettlementSummary } from '@/features/settlements/components/SettlementSummary';
import { useGenerateSettlements, useSettlements, type Period } from '@/features/settlements/queries/useSettlements';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import type { CommissionSettlement } from '@/shared/types/commissions';

function currentPeriod(): Period {
  const dateValue = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  const today = new Date(`${dataLocalHoje()}T12:00:00`);
  const sinceFriday = (today.getDay() + 2) % 7;
  const start = new Date(today); start.setDate(today.getDate() - sinceFriday);
  const end = new Date(start); end.setDate(start.getDate() + 6);
  return { period_start: dateValue(start), period_end: dateValue(end) };
}

const labels = { PENDING: 'Pendente', DEFERRED: 'Adiado', PAID: 'Pago' };

const roleLabels: Record<string, string> = {
  CONSULTOR: 'Consultor padrão',
  CONSULTOR_MEI_ESCALONADO: 'Consultor escalonado',
  FINALIZACAO: 'Finalização',
  BKO: 'BKO',
  LIDER: 'Líder comercial',
  LIDER_MEI_GERAL: 'Líder MEI geral',
  LIDER_FINALIZACAO: 'Líder de finalização',
};
const leaderRoles = new Set(['LIDER', 'LIDER_MEI_GERAL', 'LIDER_FINALIZACAO']);
const consultantRoles = new Set(['CONSULTOR', 'CONSULTOR_MEI_ESCALONADO']);
type Sector = 'CONSULTANTS' | 'FINALIZATION' | 'BKO' | 'LEADERS' | 'OTHER';

export function classificarSetorFechamento(item: CommissionSettlement): Sector {
  if (item.roles.some((role) => leaderRoles.has(role))) return 'LEADERS';
  if (item.roles.some((role) => consultantRoles.has(role))) return 'CONSULTANTS';
  if (item.roles.includes('FINALIZACAO')) return 'FINALIZATION';
  if (item.roles.includes('BKO')) return 'BKO';
  return 'OTHER';
}

function SettlementSector({ title, description, items, canWrite, onAction }: {
  title: string;
  description: string;
  items: CommissionSettlement[];
  canWrite: boolean;
  onAction: (item: CommissionSettlement, action: 'ADJUST' | 'PAY') => void;
}) {
  return <Card withBorder padding={0}>
    <Group justify="space-between" px="md" py="sm">
      <div><Title order={3} size="h5">{title}</Title><Text size="xs" c="dimmed">{description}</Text></div>
      <Badge color="gray" variant="light">{items.length} colaborador(es)</Badge>
    </Group>
    {items.length === 0
      ? <Text size="sm" c="dimmed" px="md" pb="md">Nenhum fechamento neste setor.</Text>
      : <Table.ScrollContainer minWidth={1150}><Table striped verticalSpacing="sm">
        <Table.Thead><Table.Tr><Table.Th>Beneficiário</Table.Th><Table.Th>Função</Table.Th>
          <Table.Th ta="right">Bruto</Table.Th><Table.Th ta="right">Acumulado anterior</Table.Th>
          <Table.Th ta="right">Bônus</Table.Th><Table.Th ta="right">Desconto</Table.Th>
          <Table.Th ta="right">Adiado</Table.Th><Table.Th ta="right">Pago</Table.Th>
          <Table.Th ta="right">A pagar</Table.Th><Table.Th>Status</Table.Th><Table.Th>Ações</Table.Th>
        </Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}>
          <Table.Td><Text size="sm" fw={600}>{item.beneficiary_name}</Text></Table.Td>
          <Table.Td>{item.roles.map((role) => <Badge key={role} variant="light" mr={4}>
            {roleLabels[role] ?? role}
          </Badge>)}</Table.Td>
          {[item.gross_amount, item.carryover_amount, item.bonus_amount, item.discount_amount,
            item.deferred_amount, item.paid_amount, item.payable_amount]
            .map((value, index) => <Table.Td key={index} ta="right">{formatarMoeda(value)}</Table.Td>)}
          <Table.Td><Badge variant="light">{labels[item.status]}</Badge></Table.Td>
          <Table.Td>{canWrite && item.status !== 'PAID' && <Group gap="xs">
            <Button size="xs" variant="default" onClick={() => onAction(item, 'ADJUST')}>Ajustar</Button>
            {item.payable_amount !== '0.00' && <Button size="xs" onClick={() => onAction(item, 'PAY')}>Pagar</Button>}
          </Group>}</Table.Td>
        </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
  </Card>;
}

export function SettlementsPage() {
  const { pode } = useAuth();
  const canWrite = pode('settlements:write');
  const [period, setPeriod] = useState(currentPeriod);
  const query = useSettlements(period);
  const items = query.data?.items ?? [];
  const generate = useGenerateSettlements(period);
  const [selected, setSelected] = useState<CommissionSettlement | null>(null);
  const [action, setAction] = useState<'ADJUST' | 'PAY'>('ADJUST');
  const [bkoOpened, setBkoOpened] = useState(false);
  const [finalizationOpened, setFinalizationOpened] = useState(false);
  const open = (item: CommissionSettlement, next: 'ADJUST' | 'PAY') => { setSelected(item); setAction(next); };
  const sectors = {
    CONSULTANTS: items.filter((item) => classificarSetorFechamento(item) === 'CONSULTANTS'),
    FINALIZATION: items.filter((item) => classificarSetorFechamento(item) === 'FINALIZATION'),
    BKO: items.filter((item) => classificarSetorFechamento(item) === 'BKO'),
    LEADERS: items.filter((item) => classificarSetorFechamento(item) === 'LEADERS'),
    OTHER: items.filter((item) => classificarSetorFechamento(item) === 'OTHER'),
  };
  return <Stack gap="lg">
    <Group justify="space-between"><div><Title order={2} size="h3">Fechamentos de comissão</Title>
      <Text size="sm" c="dimmed">Comissão bruta, acumulado anterior, ajustes e pagamento por beneficiário.</Text></div>
      {canWrite && <Group><Button variant="default" onClick={() => setBkoOpened(true)}>Lançar BKO</Button>
        <Button variant="default" onClick={() => setFinalizationOpened(true)}>Lançar Finalização</Button>
        <Button onClick={() => generate.mutate()} loading={generate.isPending}>Gerar / atualizar</Button></Group>}
    </Group>
    <Card withBorder><Group align="end"><TextInput type="date" label="Início" value={period.period_start}
      onChange={(event) => setPeriod({ ...period, period_start: event.currentTarget.value })} />
      <TextInput type="date" label="Fim" value={period.period_end}
        onChange={(event) => setPeriod({ ...period, period_end: event.currentTarget.value })} /></Group></Card>
    <SettlementSummary items={items} />
    <Alert color="blue" title="Como o saldo é formado">
      A pagar = comissão bruta + acumulado anterior + bônus − desconto − adiado − pago.
      O acumulado anterior é o valor adiado no último fechamento.
      A tabela abaixo mantém cada componente separado para conferência.
    </Alert>
    <EstadoDaLista carregando={query.isPending} erro={query.error ?? generate.error ?? null}
      vazio={items.length === 0} mensagemVazio="Nenhum fechamento gerado para o período.">
      <Stack gap="md">
        <SettlementSector title="Consultores" description="Consultor padrão e consultor escalonado"
          items={sectors.CONSULTANTS} canWrite={canWrite} onAction={open} />
        <SettlementSector title="Finalização" description="Comissão automática e bônus de Finalização"
          items={sectors.FINALIZATION} canWrite={canWrite} onAction={open} />
        <SettlementSector title="BKO" description="Comissões manuais dos colaboradores de BKO"
          items={sectors.BKO} canWrite={canWrite} onAction={open} />
        <SettlementSector title="Lideranças" description="Líder comercial, MEI geral e de Finalização"
          items={sectors.LEADERS} canWrite={canWrite} onAction={open} />
        {sectors.OTHER.length > 0 && <SettlementSector title="Outros fechamentos"
          description="Colaboradores sem função identificada no período"
          items={sectors.OTHER} canWrite={canWrite} onAction={open} />}
      </Stack>
    </EstadoDaLista>
    <SettlementActionModal settlement={selected} action={action} period={period} onClose={() => setSelected(null)} />
    <BkoEntryModal opened={bkoOpened} onClose={() => setBkoOpened(false)} />
    <FinalizationEntryModal opened={finalizationOpened} onClose={() => setFinalizationOpened(false)} />
  </Stack>;
}
