import { Alert, Badge, Button, Card, Group, Modal, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useCloseCommissionPeriod, useCommissionPeriods, useCreateCommissionPeriod, useReopenCommissionPeriod } from '@/features/periods/queries/useCommissionPeriods';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import type { CommissionPeriod } from '@/shared/types/commissions';

function defaults() {
  const dateValue = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  const dateTimeValue = (value: Date) => `${dateValue(value)}T${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`;
  const today = new Date();
  const sinceFriday = (today.getDay() + 2) % 7;
  const start = new Date(today); start.setDate(today.getDate() - sinceFriday);
  const end = new Date(start); end.setDate(start.getDate() + 6); end.setHours(23, 59, 0, 0);
  return { start: dateValue(start), end: dateValue(end), cutoff: dateTimeValue(end) };
}

export function PeriodsPage() {
  const { pode } = useAuth(); const query = useCommissionPeriods();
  const create = useCreateCommissionPeriod(); const close = useCloseCommissionPeriod();
  const reopen = useReopenCommissionPeriod();
  const initial = defaults();
  const [creating, setCreating] = useState(false); const [closing, setClosing] = useState<CommissionPeriod | null>(null);
  const [reopening, setReopening] = useState<CommissionPeriod | null>(null);
  const [start, setStart] = useState(initial.start); const [end, setEnd] = useState(initial.end);
  const [cutoff, setCutoff] = useState(initial.cutoff); const [reason, setReason] = useState('Fechamento semanal');
  const submit = async () => { await create.mutateAsync({ period_start: start, period_end: end,
    cutoff_at: new Date(cutoff).toISOString(), reason }); setCreating(false); };
  const confirmClose = async () => { if (!closing) return; await close.mutateAsync({ id: closing.id, reason }); setClosing(null); };
  const confirmReopen = async () => { if (!reopening) return; await reopen.mutateAsync({ id: reopening.id, reason }); setReopening(null); };
  return <Stack gap="lg"><Group justify="space-between"><div><Title order={2} size="h3">Períodos de comissão</Title>
    <Text size="sm" c="dimmed">Calendário, cutoff e congelamento dos cálculos financeiros.</Text></div>
    {pode('periods:close') && <Button onClick={() => setCreating(true)}>Novo período</Button>}</Group>
    <Alert color="blue">Após o fechamento, comissão bruta e ajustes do período ficam imutáveis. Pagamentos do fechamento continuam permitidos.</Alert>
    <Card withBorder padding={0}><EstadoDaLista carregando={query.isPending} erro={query.error ?? null}
      vazio={(query.data?.length ?? 0) === 0} mensagemVazio="Nenhum período cadastrado.">
      <Table striped verticalSpacing="sm"><Table.Thead><Table.Tr><Table.Th>Período</Table.Th><Table.Th>Cutoff</Table.Th><Table.Th>Status</Table.Th><Table.Th>Motivo</Table.Th><Table.Th>Ações</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{query.data?.map((item) => <Table.Tr key={item.id}><Table.Td>{item.period_start.split('-').reverse().join('/')} a {item.period_end.split('-').reverse().join('/')}</Table.Td>
          <Table.Td>{new Date(item.cutoff_at).toLocaleString('pt-BR')}</Table.Td><Table.Td><Badge color={item.status === 'OPEN' ? 'green' : 'gray'}>{item.status === 'OPEN' ? 'Aberto' : 'Fechado'}</Badge></Table.Td>
          <Table.Td>{item.reopen_reason ?? item.reason}</Table.Td><Table.Td><Group gap="xs">
            {item.status === 'OPEN' && pode('periods:close') && <Button size="xs" variant="default" onClick={() => { setClosing(item); setReason('Conferência concluída'); }}>Fechar período</Button>}
            {item.status === 'CLOSED' && pode('periods:reopen') && <Button size="xs" variant="default" onClick={() => { setReopening(item); setReason(''); }}>Reabrir período</Button>}
            {item.reopened_at !== null && <Badge color="orange" variant="light">Reaberto</Badge>}</Group></Table.Td></Table.Tr>)}</Table.Tbody></Table>
    </EstadoDaLista></Card>
    <Modal opened={creating} onClose={() => setCreating(false)} title="Novo período" centered><Stack>
      <Group grow><TextInput type="date" label="Início" value={start} onChange={(event) => setStart(event.currentTarget.value)} />
        <TextInput type="date" label="Fim" value={end} onChange={(event) => setEnd(event.currentTarget.value)} /></Group>
      <TextInput type="datetime-local" label="Cutoff" value={cutoff} onChange={(event) => setCutoff(event.currentTarget.value)} />
      <TextInput label="Motivo" value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
      {create.error && <Text size="sm" c="red">{create.error.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={() => setCreating(false)}>Cancelar</Button><Button onClick={() => void submit()} loading={create.isPending}>Criar período</Button></Group>
    </Stack></Modal>
    <Modal opened={closing !== null} onClose={() => setClosing(null)} title="Fechar período" centered><Stack>
      <Alert color="yellow">Essa ação congela os cálculos e ajustes deste período.</Alert>
      <TextInput label="Motivo" value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
      {close.error && <Text size="sm" c="red">{close.error.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={() => setClosing(null)}>Cancelar</Button><Button color="red" onClick={() => void confirmClose()} loading={close.isPending}>Confirmar fechamento</Button></Group>
    </Stack></Modal>
    <Modal opened={reopening !== null} onClose={() => setReopening(null)} title="Reabrir período" centered><Stack>
      <Alert color="orange">Reabertura é ato excepcional e fica registrada na auditoria com o seu nome. Fechamento já pago não pode ser reaberto: nesse caso, corrija por compensação no período atual.</Alert>
      <TextInput label="Motivo" description="Descreva o que justifica a reabertura (mínimo de 10 caracteres)." value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
      {reopen.error && <Text size="sm" c="red">{reopen.error.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={() => setReopening(null)}>Cancelar</Button><Button color="orange" disabled={reason.trim().length < 10} onClick={() => void confirmReopen()} loading={reopen.isPending}>Confirmar reabertura</Button></Group>
    </Stack></Modal>
  </Stack>;
}
