import {
  Alert,
  Button,
  FileButton,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPaperclip } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { useCreateReceipt } from '@/features/proposals/mutations/useCreateReceipt';

interface Props {
  opened: boolean;
  proposalId: number;
  onClose: () => void;
}

const TODAY = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
const CURRENT_TIME = new Date().toLocaleTimeString('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  hour: '2-digit',
  minute: '2-digit',
});

export function ReceiptCreateModal({ opened, proposalId, onClose }: Props) {
  const create = useCreateReceipt();
  const [amount, setAmount] = useState('');
  const [businessDate, setBusinessDate] = useState(TODAY);
  const [paymentTime, setPaymentTime] = useState(CURRENT_TIME);
  const [method, setMethod] = useState<string | null>('PIX');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [proof, setProof] = useState<File | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());

  useEffect(() => {
    if (!opened) return;
    setAmount('');
    setBusinessDate(TODAY);
    setPaymentTime(CURRENT_TIME);
    setMethod('PIX');
    setReference('');
    setNotes('');
    setProof(null);
    setIdempotencyKey(crypto.randomUUID());
  }, [opened]);

  const submit = async () => {
    if (!amount || !method || !proof) return;
    await create.mutateAsync({
      proposalId,
      amount: amount.replace(',', '.'),
      businessDate,
      paymentTime,
      paymentMethod: method,
      reference,
      notes,
      proof,
      idempotencyKey,
    });
    notifications.show({
      color: 'positivo',
      title: 'Recebimento declarado',
      message: 'O valor será reconhecido após a conferência do Financeiro.',
    });
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Declarar recebimento" centered size="lg">
      <Stack>
        {create.error && (
          <Alert color="red" title={create.error.problem.title}>
            {create.error.problem.detail}
          </Alert>
        )}
        <Group grow align="flex-start">
          <TextInput
            label="Valor recebido"
            withAsterisk
            placeholder="0,00"
            value={amount}
            onChange={(event) => setAmount(event.currentTarget.value)}
          />
          <TextInput
            label="Data do recebimento"
            withAsterisk
            type="date"
            max={TODAY}
            value={businessDate}
            onChange={(event) => setBusinessDate(event.currentTarget.value)}
          />
          <TextInput
            label="Hora efetiva"
            withAsterisk
            type="time"
            value={paymentTime}
            onChange={(event) => setPaymentTime(event.currentTarget.value)}
          />
        </Group>
        <Group grow align="flex-start">
          <Select
            label="Forma de pagamento"
            withAsterisk
            value={method}
            onChange={setMethod}
            data={['PIX', 'TED', 'BOLETO', 'DINHEIRO', 'OUTRO']}
          />
          <TextInput
            label="Referência"
            placeholder="NSU, ID ou descrição"
            value={reference}
            onChange={(event) => setReference(event.currentTarget.value)}
          />
        </Group>
        <Textarea
          label="Observações"
          value={notes}
          onChange={(event) => setNotes(event.currentTarget.value)}
        />
        <div>
          <Text size="sm" fw={500}>
            Comprovante <Text component="span" c="red">*</Text>
          </Text>
          <FileButton onChange={setProof} accept="application/pdf,image/jpeg,image/png">
            {(props) => (
              <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
                {proof?.name ?? 'Selecionar PDF, JPG ou PNG'}
              </Button>
            )}
          </FileButton>
          <Text size="xs" c="dimmed" mt={4}>Obrigatório, até 10 MB.</Text>
        </div>
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancelar</Button>
          <Button
            onClick={() => void submit()}
            loading={create.isPending}
            disabled={!amount || !businessDate || !paymentTime || !method || !proof}
          >
            Declarar recebimento
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
