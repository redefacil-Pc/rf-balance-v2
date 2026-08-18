import {
  Badge,
  Button,
  Card,
  Group,
  Progress,
  RingProgress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core';
import {
  IconArrowRight,
  IconBriefcase,
  IconCash,
  IconChartBar,
  IconCoin,
  IconFileInvoice,
  IconPercentage,
  IconTrendingUp,
  type Icon,
} from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '@/app/providers/AuthProvider';
import { useDashboard, type DashboardPeriod } from '@/features/dashboard/queries/useDashboard';
import type { DashboardSummary } from '@/features/dashboard/types';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import { dataLocalHoje } from '@/shared/formatters/local-date';

type Preset = 'WEEK' | 'MONTH' | 'CUSTOM';

function iso(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function periodFor(preset: Exclude<Preset, 'CUSTOM'>): DashboardPeriod {
  const today = new Date(`${dataLocalHoje()}T12:00:00`);
  const start = new Date(today);
  if (preset === 'WEEK') {
    start.setDate(today.getDate() - ((today.getDay() + 2) % 7));
  } else {
    start.setDate(1);
  }
  return { period_start: iso(start), period_end: iso(today) };
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

function formatPercent(value: string): string {
  return `${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function MetricCard({
  label,
  value,
  detail,
  icon: IconComponent,
  color,
}: {
  label: string;
  value: string;
  detail: string;
  icon: Icon;
  color: string;
}) {
  return (
    <Card withBorder padding="lg" h="100%">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <div>
          <Text size="xs" c="dimmed" fw={700} tt="uppercase">{label}</Text>
          <Text size="xl" fw={750} mt={5} style={{ fontVariantNumeric: 'tabular-nums' }}>
            {value}
          </Text>
          <Text size="xs" c="dimmed" mt={3}>{detail}</Text>
        </div>
        <ThemeIcon color={color} variant="light" size={42} radius="lg">
          <IconComponent size={21} stroke={1.7} />
        </ThemeIcon>
      </Group>
    </Card>
  );
}

function ProposalStatus({ summary }: { summary: DashboardSummary }) {
  const total = Math.max(summary.proposal_count, 1);
  const sections = [
    { label: 'Abertas', value: summary.open_count, color: 'blue' },
    { label: 'Parciais', value: summary.partially_paid_count, color: 'yellow' },
    { label: 'Quitadas', value: summary.paid_count, color: 'teal' },
    { label: 'Canceladas', value: summary.cancelled_count, color: 'red' },
  ];
  return (
    <Card withBorder padding="lg" h="100%">
      <Group justify="space-between" mb="md">
        <div>
          <Title order={3} size="h5">Situação das propostas</Title>
          <Text size="xs" c="dimmed">Carteira visível no período</Text>
        </div>
        <RingProgress
          size={92}
          thickness={9}
          roundCaps
          sections={sections.map((item) => ({
            value: (item.value / total) * 100,
            color: item.color,
          }))}
          label={<Text ta="center" fw={700}>{summary.proposal_count}</Text>}
        />
      </Group>
      <SimpleGrid cols={2} spacing="xs">
        {sections.map((item) => (
          <Group key={item.label} gap="xs" wrap="nowrap">
            <ThemeIcon color={item.color} size={10} radius="xl" />
            <Text size="sm" c="dimmed">{item.label}</Text>
            <Text size="sm" fw={700} ml="auto">{item.value}</Text>
          </Group>
        ))}
      </SimpleGrid>
      {summary.pending_approval_count > 0 && (
        <Badge color="orange" variant="light" mt="md">
          {summary.pending_approval_count} aguardando aprovação
        </Badge>
      )}
    </Card>
  );
}

export function DashboardPage() {
  const { usuario, pode } = useAuth();
  const [preset, setPreset] = useState<Preset>('MONTH');
  const [period, setPeriod] = useState<DashboardPeriod>(() => periodFor('MONTH'));
  const query = useDashboard(period);
  const summary = query.data?.summary;
  const maxProduction = useMemo(
    () => Math.max(...(query.data?.trend ?? []).map((item) => Number(item.production_amount)), 1),
    [query.data?.trend],
  );

  const changePreset = (value: string) => {
    const next = value as Preset;
    setPreset(next);
    if (next !== 'CUSTOM') setPeriod(periodFor(next));
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={2} size="h3">Olá, {usuario?.full_name.split(' ')[0]}</Title>
          <Text c="dimmed" size="sm">Visão consolidada da operação dentro do seu acesso.</Text>
        </div>
        <SegmentedControl
          value={preset}
          onChange={changePreset}
          data={[
            { value: 'WEEK', label: 'Semana' },
            { value: 'MONTH', label: 'Mês' },
            { value: 'CUSTOM', label: 'Personalizado' },
          ]}
        />
      </Group>

      <Card withBorder padding="md">
        <Group align="end">
          <TextInput
            type="date"
            label="Início"
            value={period.period_start}
            onChange={(event) => {
              setPreset('CUSTOM');
              setPeriod({ ...period, period_start: event.currentTarget.value });
            }}
          />
          <TextInput
            type="date"
            label="Fim"
            value={period.period_end}
            onChange={(event) => {
              setPreset('CUSTOM');
              setPeriod({ ...period, period_end: event.currentTarget.value });
            }}
          />
          <Text size="sm" c="dimmed" ml="auto">
            Dados de {formatDate(period.period_start)} a {formatDate(period.period_end)}
          </Text>
        </Group>
      </Card>

      <EstadoDaLista
        carregando={query.isPending}
        erro={query.error ?? null}
        vazio={!summary}
        onTentarNovamente={() => void query.refetch()}
        mensagemVazio="Ainda não existem indicadores para este período."
      >
        {summary && (
          <Stack gap="lg">
            <SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }}>
              <MetricCard label="Produção aprovada" value={formatarMoeda(summary.approved_production)}
                detail={`${summary.proposal_count} proposta(s) no período`} icon={IconBriefcase} color="blue" />
              <MetricCard label="Faturamento reconhecido" value={formatarMoeda(summary.recognized_revenue)}
                detail="Recebimentos aprovados menos estornos" icon={IconCash} color="teal" />
              <MetricCard label="Comissões" value={formatarMoeda(summary.total_commissions)}
                detail="Créditos e débitos materializados" icon={IconCoin} color="violet" />
              <MetricCard label="Faturamento líquido" value={formatarMoeda(summary.net_revenue)}
                detail="Reconhecido menos comissões" icon={IconTrendingUp} color="marca" />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }}>
              <MetricCard label="Comissão da empresa" value={formatarMoeda(summary.company_commission)}
                detail="Valor previsto nas propostas aprovadas" icon={IconFileInvoice} color="cyan" />
              <MetricCard label="Pendência financeira" value={formatarMoeda(summary.outstanding_amount)}
                detail="Saldo das propostas aprovadas" icon={IconChartBar} color="orange" />
              <MetricCard label="TPS médio" value={formatPercent(summary.average_tps)}
                detail="Média das propostas aprovadas" icon={IconPercentage} color="grape" />
              <ProposalStatus summary={summary} />
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, lg: 2 }}>
              <Card withBorder padding="lg">
                <Group justify="space-between" mb="md">
                  <div><Title order={3} size="h5">Evolução diária</Title>
                    <Text size="xs" c="dimmed">Produção aprovada e faturamento reconhecido</Text></div>
                  <IconChartBar size={20} />
                </Group>
                {(query.data?.trend ?? []).length === 0 ? (
                  <Text size="sm" c="dimmed">Nenhuma movimentação no período.</Text>
                ) : (
                  <Stack gap="sm">
                    {(query.data?.trend ?? []).slice(-10).map((item) => (
                      <div key={item.business_date}>
                        <Group justify="space-between" mb={4}>
                          <Text size="xs" fw={600}>{formatDate(item.business_date)}</Text>
                          <Text size="xs" c="dimmed">
                            {formatarMoeda(item.production_amount)} · recebido {formatarMoeda(item.recognized_revenue)}
                          </Text>
                        </Group>
                        <Progress value={(Number(item.production_amount) / maxProduction) * 100}
                          color="marca" size="sm" radius="xl" />
                      </div>
                    ))}
                  </Stack>
                )}
              </Card>

              <Card withBorder padding={0}>
                <Group justify="space-between" px="lg" py="md">
                  <div><Title order={3} size="h5">Ranking de produção</Title>
                    <Text size="xs" c="dimmed">Cinco consultores com maior produção aprovada</Text></div>
                  <IconTrendingUp size={20} />
                </Group>
                {(query.data?.ranking ?? []).length === 0 ? (
                  <Text size="sm" c="dimmed" px="lg" pb="lg">Nenhum consultor no período.</Text>
                ) : (
                  <Table verticalSpacing="sm" highlightOnHover>
                    <Table.Thead><Table.Tr><Table.Th>#</Table.Th><Table.Th>Consultor</Table.Th>
                      <Table.Th ta="right">Propostas</Table.Th><Table.Th ta="right">Produção</Table.Th>
                    </Table.Tr></Table.Thead>
                    <Table.Tbody>{query.data?.ranking.map((item, index) => (
                      <Table.Tr key={item.collaborator_id}>
                        <Table.Td><Badge variant="light" circle>{index + 1}</Badge></Table.Td>
                        <Table.Td><Text size="sm" fw={600}>{item.collaborator_name}</Text></Table.Td>
                        <Table.Td ta="right">{item.proposal_count}</Table.Td>
                        <Table.Td ta="right">{formatarMoeda(item.production_amount)}</Table.Td>
                      </Table.Tr>
                    ))}</Table.Tbody>
                  </Table>
                )}
              </Card>
            </SimpleGrid>
          </Stack>
        )}
      </EstadoDaLista>

      <Card withBorder padding="lg">
        <Group justify="space-between" mb="md">
          <div><Title order={3} size="h5">Acessos rápidos</Title>
            <Text size="xs" c="dimmed">Continue o trabalho nas áreas liberadas para seu perfil.</Text></div>
        </Group>
        <Group gap="sm">
          {pode('proposals:read') && <Button component={Link} to="/proposals" variant="light"
            rightSection={<IconArrowRight size={15} />}>Propostas</Button>}
          {pode('receipts:read') && <Button component={Link} to="/receipts" variant="light"
            rightSection={<IconArrowRight size={15} />}>Recebimentos</Button>}
          {pode('settlements:read') && <Button component={Link} to="/settlements" variant="light"
            rightSection={<IconArrowRight size={15} />}>Fechamentos</Button>}
          {pode('settlements:read') && <Button component={Link} to="/reports" variant="light"
            rightSection={<IconArrowRight size={15} />}>Relatório financeiro</Button>}
        </Group>
      </Card>
    </Stack>
  );
}
