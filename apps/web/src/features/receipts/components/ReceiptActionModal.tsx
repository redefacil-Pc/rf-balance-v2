import { Alert, Button, Group, Modal, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { useDecideReceipt, useReverseReceipt } from '../mutations/useReceiptActions';
import type { Receipt } from '../types';

interface Props { receipt: Receipt | null; action: 'DECIDE' | 'REVERSE'; onClose: () => void }
const TODAY = new Date().toISOString().slice(0, 10);

export function ReceiptActionModal({ receipt, action, onClose }: Props) {
  const decide = useDecideReceipt();
  const reverse = useReverseReceipt();
  const [reason, setReason] = useState('');
  const [date, setDate] = useState(TODAY);
  useEffect(() => { setReason(''); setDate(TODAY); }, [receipt, action]);
  const error = decide.error ?? reverse.error;

  const approve = async () => {
    if (!receipt) return;
    await decide.mutateAsync({ id: receipt.id, decision: 'APPROVE' });
    notifications.show({ color: 'positivo', title: 'Recebimento aprovado',
      message: 'O valor foi consolidado na proposta.' }); onClose();
  };
  const reject = async () => {
    if (!receipt || reason.trim().length < 3) return;
    await decide.mutateAsync({ id: receipt.id, decision: 'REJECT', reason });
    notifications.show({ color: 'yellow', title: 'Recebimento devolvido', message: reason });
    onClose();
  };
  const doReverse = async () => {
    if (!receipt || reason.trim().length < 3) return;
    await reverse.mutateAsync({ id: receipt.id, reason, businessDate: date });
    notifications.show({ color: 'positivo', title: 'Estorno registrado',
      message: 'O histórico original foi preservado e a proposta foi recalculada.' }); onClose();
  };

  return <Modal opened={receipt !== null} onClose={onClose}
    title={action === 'DECIDE' ? 'Analisar recebimento' : 'Estornar recebimento'} centered>
    <Stack>
      {error && <Alert color="red" title={error.problem.title}>{error.problem.detail}</Alert>}
      <Text size="sm">{receipt ? `#${receipt.id} · ${receipt.customer_name}` : ''}</Text>
      {action === 'REVERSE' && <TextInput type="date" label="Data do estorno" withAsterisk
        value={date} onChange={(event) => setDate(event.currentTarget.value)} />}
      <Textarea label={action === 'DECIDE' ? 'Motivo da devolução' : 'Motivo do estorno'}
        placeholder={action === 'DECIDE' ? 'Obrigatório apenas para devolver' : 'Obrigatório'}
        value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>Cancelar</Button>
        {action === 'DECIDE' ? <>
          <Button color="red" variant="light" onClick={() => void reject()}
            disabled={reason.trim().length < 3} loading={decide.isPending}>Devolver</Button>
          <Button onClick={() => void approve()} loading={decide.isPending}>Aprovar</Button>
        </> : <Button color="red" onClick={() => void doReverse()}
          disabled={reason.trim().length < 3} loading={reverse.isPending}>Confirmar estorno</Button>}
      </Group>
    </Stack>
  </Modal>;
}
