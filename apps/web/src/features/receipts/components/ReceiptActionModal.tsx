import { Alert, Button, Group, Modal, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';
import { useDecideReceipt, useReverseReceipt } from '../mutations/useReceiptActions';
import type { Receipt } from '@/shared/types/receipts';

interface Props { receipt: Receipt | null; action: 'DECIDE' | 'REVERSE'; onClose: () => void }
const TODAY = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });

export function ReceiptActionModal({ receipt, action, onClose }: Props) {
  const decide = useDecideReceipt();
  const reverse = useReverseReceipt();
  const [reason, setReason] = useState('');
  const [date, setDate] = useState(TODAY);
  const [amount, setAmount] = useState('');
  useEffect(() => {
    setReason('');
    setDate(TODAY);
    setAmount(receipt?.amount ?? '');
  }, [receipt, action]);
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
    await reverse.mutateAsync({ id: receipt.id, reason, businessDate: date, amount });
    notifications.show({ color: 'positivo', title: 'Estorno registrado',
      message: 'O histórico original foi preservado e a proposta foi recalculada.' }); onClose();
  };

  return <Modal opened={receipt !== null} onClose={onClose}
    title={action === 'DECIDE' ? 'Analisar recebimento' : 'Estornar recebimento'} centered>
    <Stack>
      {error && <Alert color="red" title={error.problem.title}>{error.problem.detail}</Alert>}
      <Text size="sm">{receipt ? `#${receipt.id} · ${receipt.customer_name}` : ''}</Text>
      {action === 'REVERSE' && <Group grow>
        <TextInput label="Valor do estorno" withAsterisk value={amount}
          onChange={(event) => setAmount(event.currentTarget.value)} />
        <TextInput type="date" label="Data do estorno" withAsterisk max={TODAY}
          value={date} onChange={(event) => setDate(event.currentTarget.value)} />
      </Group>}
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
          disabled={reason.trim().length < 3 || !amount} loading={reverse.isPending}>Confirmar estorno</Button>}
      </Group>
    </Stack>
  </Modal>;
}
