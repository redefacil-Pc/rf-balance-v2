import { Alert, Button, Card, Checkbox, Group, Modal, Select, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useEffect, useMemo, useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useCollaborators } from '@/features/collaborators/queries/useCollaborators';
import { useBeneficiaryPolicies, useCreateBeneficiaryPolicy } from '@/features/commission-rules/queries/useBeneficiaryPolicies';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { decimalParaPercentual, mascararPercentual, percentualParaDecimal } from '@/shared/formatters/percent-mask';

export function BeneficiaryPoliciesCard() {
  const { pode } = useAuth();
  const query = useBeneficiaryPolicies();
  const policies = (query.data ?? []).filter((item) => item.collaborator_name && item.valid_from);
  const create = useCreateBeneficiaryPolicy();
  const collaborators = useCollaborators({ only_active: true });
  useEffect(() => {
    if (collaborators.hasNextPage && !collaborators.isFetchingNextPage) {
      void collaborators.fetchNextPage();
    }
  }, [collaborators.hasNextPage, collaborators.isFetchingNextPage, collaborators.fetchNextPage]);
  const options = useMemo(() => {
    const eligible = (collaborators.data?.pages ?? [])
      .flatMap((page) => Array.isArray(page.items) ? page.items : [])
      .filter((item) => item.roles?.includes('CONSULTOR') || item.roles?.includes('CONSULTOR_MEI_ESCALONADO'));
    return Array.from(new Map(eligible.map((item) => [item.id, item])).values())
      .map((item) => ({
        value: String(item.id),
        label: `${item.full_name} — ${item.roles.includes('CONSULTOR_MEI_ESCALONADO') ? 'Escalonado' : 'Padrão'} · ${item.tax_regime}`,
      }));
  }, [collaborators.data]);
  const [opened, setOpened] = useState(false);
  const [collaborator, setCollaborator] = useState<string | null>(null);
  const [validFrom, setValidFrom] = useState(new Date().toISOString().slice(0, 10));
  const [excluded, setExcluded] = useState(false);
  const [override, setOverride] = useState('');
  const [reason, setReason] = useState('');
  const submit = async () => {
    if (!collaborator) return;
    await create.mutateAsync({ collaborator_id: Number(collaborator), valid_from: validFrom,
      excluded, override_tps_35_percentage: excluded || !override ? null : percentualParaDecimal(override), reason });
    setOpened(false);
  };
  return <Card withBorder><Stack>
    <Group justify="space-between"><div><Title order={3} size="h4">Exceções individuais</Title>
      <Text size="sm" c="dimmed">Exclusão de comissão ou percentual próprio para TPS a partir de 35%, sempre com vigência.</Text></div>
      {pode('commission_rules:write') && <Button variant="default" onClick={() => setOpened(true)}>Nova exceção</Button>}</Group>
    <EstadoDaLista carregando={query.isPending} erro={query.error ?? null} vazio={policies.length === 0}
      mensagemVazio="Nenhuma exceção individual configurada.">
      <Table striped><Table.Thead><Table.Tr><Table.Th>Consultor</Table.Th><Table.Th>Vigência</Table.Th><Table.Th>Regra</Table.Th><Table.Th>Motivo</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{policies.map((item) => <Table.Tr key={item.id}><Table.Td>{item.collaborator_name}</Table.Td>
          <Table.Td>{item.valid_from.split('-').reverse().join('/')} até {item.valid_to?.split('-').reverse().join('/') ?? 'sem término'}</Table.Td>
          <Table.Td>{item.excluded ? 'Sem comissão' : `TPS ≥ 35%: ${decimalParaPercentual(item.override_tps_35_percentage ?? '0')}%`}</Table.Td>
          <Table.Td>{item.reason}</Table.Td></Table.Tr>)}</Table.Tbody></Table>
    </EstadoDaLista>
    <Modal opened={opened} onClose={() => setOpened(false)} title="Nova exceção individual" centered><Stack>
      <Alert color="blue">Uma nova vigência encerra automaticamente a exceção anterior no dia precedente.</Alert>
      <Select label="Consultor" description="Consultores padrão e escalonados, MEI ou CLT." searchable data={options} value={collaborator} onChange={setCollaborator}
        disabled={collaborators.isPending} placeholder={collaborators.isPending ? 'Carregando consultores...' : options.length ? 'Selecione' : 'Nenhum consultor elegível'} />
      <TextInput label="Início da vigência" type="date" value={validFrom} onChange={(event) => setValidFrom(event.currentTarget.value)} />
      <Checkbox label="Não recebe comissão" checked={excluded} onChange={(event) => setExcluded(event.currentTarget.checked)} />
      {!excluded && <TextInput label="Percentual próprio quando TPS ≥ 35%" rightSection="%" value={override}
        onChange={(event) => setOverride(mascararPercentual(event.currentTarget.value))} />}
      <TextInput label="Motivo" value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
      {create.error && <Text size="sm" c="red">{create.error.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={() => setOpened(false)}>Cancelar</Button>
        <Button disabled={!collaborator || reason.trim().length < 3 || (!excluded && !override)} loading={create.isPending}
          onClick={() => void submit()}>Salvar exceção</Button></Group>
    </Stack></Modal>
  </Stack></Card>;
}
