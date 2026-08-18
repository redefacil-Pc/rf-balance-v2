import { Alert, Button, Group, Loader, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { useEffect, useState } from 'react';

import { useCollaborators } from '@/features/collaborators/queries/useCollaborators';
import { useCreateBkoEntry, useCreateFinalizationEntry } from '@/features/settlements/queries/useSettlements';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import { mascararMoeda, moedaParaDecimal } from '@/shared/formatters/money-mask';

interface Props { opened: boolean; onClose: () => void }

interface ManualEntryModalProps extends Props {
  kind: 'BKO' | 'FINALIZACAO';
}

function ManualEntryModal({ opened, onClose, kind }: ManualEntryModalProps) {
  const isBko = kind === 'BKO';
  const collaborators = useCollaborators({
    role: kind,
    ...(isBko ? { tax_regime: 'MEI' as const } : {}),
    only_active: true,
  });
  const options = (collaborators.data?.pages ?? []).flatMap((page) => page.items)
    .map((item) => ({ value: String(item.id), label: item.full_name }));
  const { refetch } = collaborators;
  useEffect(() => {
    if (opened) void refetch();
  }, [opened, refetch]);
  const bkoMutation = useCreateBkoEntry();
  const finalizationMutation = useCreateFinalizationEntry();
  const mutation = isBko ? bkoMutation : finalizationMutation;
  const [beneficiary, setBeneficiary] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const [effectiveDate, setEffectiveDate] = useState(dataLocalHoje);
  const [description, setDescription] = useState(
    isBko ? 'Comissão manual de BKO' : 'Bônus manual de Finalização',
  );
  const submit = async () => {
    if (!beneficiary) return;
    await mutation.mutateAsync({ beneficiary_id: Number(beneficiary), amount: moedaParaDecimal(amount), effective_date: effectiveDate, description });
    onClose();
  };
  const roleLabel = isBko ? 'BKO MEI' : 'Finalização';
  return <Modal opened={opened} onClose={onClose}
    title={isBko ? 'Lançar comissão de BKO' : 'Lançar bônus de Finalização'} centered>
    <Stack>
      {collaborators.error && <Alert color="red" title="Não foi possível carregar os BKO">
        {collaborators.error.problem.detail}
      </Alert>}
      {!collaborators.isPending && !collaborators.error && options.length === 0 &&
        <Alert color="yellow" title={`Nenhum colaborador de ${roleLabel} elegível`}>
          {isBko
            ? 'Cadastre ou altere um colaborador ativo com regime MEI e função BKO vigente. BKO CLT não recebe comissão manual.'
            : 'Cadastre um colaborador ativo com a função FINALIZAÇÃO vigente. O regime pode ser MEI ou CLT.'}
        </Alert>}
      <Select label={roleLabel} searchable data={options} value={beneficiary}
        onChange={setBeneficiary} disabled={collaborators.isPending || options.length === 0}
        nothingFoundMessage={`Nenhum colaborador de ${roleLabel} encontrado`}
        rightSection={collaborators.isPending ? <Loader size={16} /> : undefined} />
      <TextInput label="Valor" placeholder="0,00" value={amount}
        onChange={(event) => setAmount(mascararMoeda(event.currentTarget.value))} />
      <TextInput label="Data efetiva" type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.currentTarget.value)} />
      <TextInput label="Descrição" value={description} onChange={(event) => setDescription(event.currentTarget.value)} />
      {mutation.error && <Text size="sm" c="red">{mutation.error.problem.detail}</Text>}
      <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => void submit()} loading={mutation.isPending} disabled={!beneficiary || !amount}>Lançar</Button></Group>
    </Stack>
  </Modal>;
}

export function BkoEntryModal(props: Props) {
  return <ManualEntryModal {...props} kind="BKO" />;
}

export function FinalizationEntryModal(props: Props) {
  return <ManualEntryModal {...props} kind="FINALIZACAO" />;
}
