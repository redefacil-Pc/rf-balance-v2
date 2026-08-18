import {
  Badge,
  Button,
  Card,
  Code,
  Group,
  Modal,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconEye, IconFilter, IconRefresh } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuditEvents, useAuditOptions, type AuditFilters } from '@/features/audit/queries/useAuditEvents';
import type { AuditEvent } from '@/features/audit/types';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { dataLocalHoje } from '@/shared/formatters/local-date';

function initialFilters(): AuditFilters {
  const end = new Date(`${dataLocalHoje()}T12:00:00`);
  const start = new Date(end);
  start.setDate(end.getDate() - 29);
  const iso = (value: Date) =>
    `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  return { start_date: iso(start), end_date: iso(end) };
}

function label(value: string): string {
  return value.replaceAll('_', ' ').replaceAll('.', ' · ');
}

function timestamp(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'medium',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(value));
}

export function AuditPage() {
  const [draft, setDraft] = useState<AuditFilters>(initialFilters);
  const [filters, setFilters] = useState<AuditFilters>(initialFilters);
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const options = useAuditOptions();
  const query = useAuditEvents(filters);
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const update = (field: keyof AuditFilters, value: string | null) =>
    setDraft((current) => ({ ...current, [field]: value || undefined }));

  return (
    <Stack gap="lg">
      <div>
        <Title order={2} size="h3">Auditoria</Title>
        <Text size="sm" c="dimmed">
          Trilha imutável das alterações realizadas no sistema, com ator, entidade e contexto.
        </Text>
      </div>

      <Card withBorder padding="lg">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          <TextInput type="date" label="De" value={draft.start_date}
            onChange={(event) => update('start_date', event.currentTarget.value)} />
          <TextInput type="date" label="Até" value={draft.end_date}
            onChange={(event) => update('end_date', event.currentTarget.value)} />
          <Select clearable searchable label="Módulo" placeholder="Todos"
            data={options.data?.modules ?? []} value={draft.module ?? null}
            onChange={(value) => update('module', value)} />
          <Select clearable searchable label="Ação" placeholder="Todas"
            data={(options.data?.actions ?? []).map((value) => ({ value, label: label(value) }))}
            value={draft.action ?? null} onChange={(value) => update('action', value)} />
          <TextInput label="Ator" placeholder="Nome do usuário" value={draft.actor ?? ''}
            onChange={(event) => update('actor', event.currentTarget.value)} />
          <Select clearable searchable label="Tipo de entidade" placeholder="Todas"
            data={options.data?.aggregate_types ?? []} value={draft.aggregate_type ?? null}
            onChange={(value) => update('aggregate_type', value)} />
          <TextInput label="ID da entidade" placeholder="Ex.: 42" value={draft.aggregate_id ?? ''}
            onChange={(event) => update('aggregate_id', event.currentTarget.value)} />
          <TextInput label="Correlação" placeholder="Início do código" value={draft.correlation_id ?? ''}
            onChange={(event) => update('correlation_id', event.currentTarget.value)} />
        </SimpleGrid>
        <Group justify="flex-end" mt="md">
          <Button variant="default" leftSection={<IconRefresh size={16} />}
            onClick={() => { const initial = initialFilters(); setDraft(initial); setFilters(initial); }}>
            Limpar
          </Button>
          <Button leftSection={<IconFilter size={16} />} onClick={() => setFilters({ ...draft })}>
            Aplicar filtros
          </Button>
        </Group>
      </Card>

      <Card withBorder padding={0}>
        <EstadoDaLista carregando={query.isPending} erro={query.error ?? null} vazio={items.length === 0}
          onTentarNovamente={() => void query.refetch()}
          mensagemVazio="Nenhum evento de auditoria encontrado com esses filtros.">
          <Table.ScrollContainer minWidth={980}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead><Table.Tr><Table.Th>Data e hora</Table.Th><Table.Th>Ator</Table.Th>
                <Table.Th>Módulo</Table.Th><Table.Th>Ação</Table.Th><Table.Th>Entidade</Table.Th>
                <Table.Th>Correlação</Table.Th><Table.Th /></Table.Tr></Table.Thead>
              <Table.Tbody>{items.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td><Text size="sm" style={{ whiteSpace: 'nowrap' }}>{timestamp(item.occurred_at)}</Text></Table.Td>
                  <Table.Td><Text size="sm" fw={600}>{item.actor_name}</Text></Table.Td>
                  <Table.Td><Badge variant="light" color="gray">{item.module}</Badge></Table.Td>
                  <Table.Td><Text size="sm">{label(item.action)}</Text></Table.Td>
                  <Table.Td>{item.aggregate_type
                    ? <Text size="sm">{item.aggregate_type} #{item.aggregate_id ?? '—'}</Text>
                    : <Text size="sm" c="dimmed">—</Text>}</Table.Td>
                  <Table.Td><Code>{item.correlation_id?.slice(0, 8) ?? '—'}</Code></Table.Td>
                  <Table.Td><Button size="compact-xs" variant="subtle" leftSection={<IconEye size={14} />}
                    onClick={() => setSelected(item)}>Detalhar</Button></Table.Td>
                </Table.Tr>
              ))}</Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {query.hasNextPage && <Group justify="center" p="md">
            <Button variant="default" loading={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}>Carregar mais</Button>
          </Group>}
        </EstadoDaLista>
      </Card>

      <Modal opened={selected !== null} onClose={() => setSelected(null)} title="Detalhes do evento"
        size="lg" centered>
        {selected && <Stack gap="md">
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <div><Text size="xs" c="dimmed">Ator</Text><Text size="sm" fw={600}>{selected.actor_name}</Text></div>
            <div><Text size="xs" c="dimmed">Data e hora</Text><Text size="sm">{timestamp(selected.occurred_at)}</Text></div>
            <div><Text size="xs" c="dimmed">Ação</Text><Text size="sm">{label(selected.action)}</Text></div>
            <div><Text size="xs" c="dimmed">Entidade</Text><Text size="sm">{selected.aggregate_type ?? '—'} {selected.aggregate_id ? `#${selected.aggregate_id}` : ''}</Text></div>
          </SimpleGrid>
          <div><Text size="xs" c="dimmed" mb={5}>Correlação completa</Text>
            <Code block>{selected.correlation_id ?? 'Não informada'}</Code></div>
          <div><Text size="xs" c="dimmed" mb={5}>Contexto registrado</Text>
            <Code block style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(selected.payload, null, 2)}</Code></div>
        </Stack>}
      </Modal>
    </Stack>
  );
}
