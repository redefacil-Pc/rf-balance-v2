import {
  Alert, Button, FileButton, Group, Modal, Select, Stack, Text, TextInput, Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPaperclip } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { useCreateReceipt } from '../mutations/useReceiptActions';
import { useProposals } from '@/features/proposals/queries/useProposals';
import { formatarMoeda } from '@/shared/formatters/currency';

interface Props { opened: boolean; onClose: () => void }

const TODAY = new Date().toISOString().slice(0, 10);

export function ReceiptCreateModal({ opened, onClose }: Props) {
  const proposals = useProposals({ approval_status: 'APPROVED' });
  const create = useCreateReceipt();
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [amount, setAmount] = useState('');
  const [businessDate, setBusinessDate] = useState(TODAY);
  const [method, setMethod] = useState<string | null>('PIX');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [proof, setProof] = useState<File | null>(null);

  useEffect(() => {
    if (!opened) return;
    setProposalId(null); setAmount(''); setBusinessDate(TODAY);
    setMethod('PIX'); setReference(''); setNotes(''); setProof(null);
  }, [opened]);

  const items = (proposals.data?.pages ?? []).flatMap((page) => page.items)
    .filter((proposal) => proposal.status !== 'CANCELLED');
  const submit = async () => {
    if (!proposalId || !amount || !method || !proof) return;
    await create.mutateAsync({ proposalId: Number(proposalId), amount: amount.replace(',', '.'),
      businessDate, paymentMethod: method, reference, notes, proof });
    notifications.show({ color: 'positivo', title: 'Recebimento enviado',
      message: 'O lançamento está aguardando aprovação do Financeiro.' });
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Lançar recebimento" centered size="lg">
      <Stack>
        {create.error && <Alert color="red" title={create.error.problem.title}>
          {create.error.problem.detail}
        </Alert>}
        <Select label="Proposta aprovada" withAsterisk searchable value={proposalId}
          onChange={setProposalId} data={items.map((proposal) => ({ value: String(proposal.id),
            label: `#${proposal.id} · ${proposal.customer_name} · saldo ${formatarMoeda(proposal.outstanding_amount)}` }))} />
        <Group grow align="flex-start">
          <TextInput label="Valor recebido" withAsterisk placeholder="0,00" value={amount}
            onChange={(event) => setAmount(event.currentTarget.value)} />
          <TextInput label="Data do recebimento" withAsterisk type="date" value={businessDate}
            onChange={(event) => setBusinessDate(event.currentTarget.value)} />
        </Group>
        <Group grow align="flex-start">
          <Select label="Forma de pagamento" withAsterisk value={method} onChange={setMethod}
            data={['PIX', 'TED', 'BOLETO', 'DINHEIRO', 'OUTRO']} />
          <TextInput label="Referência" placeholder="NSU, ID ou descrição" value={reference}
            onChange={(event) => setReference(event.currentTarget.value)} />
        </Group>
        <Textarea label="Observações" value={notes}
          onChange={(event) => setNotes(event.currentTarget.value)} />
        <div>
          <Text size="sm" fw={500}>Comprovante <Text component="span" c="red">*</Text></Text>
          <FileButton onChange={setProof} accept="application/pdf,image/jpeg,image/png">
            {(props) => <Button {...props} variant="default" leftSection={<IconPaperclip size={16} />}>
              {proof?.name ?? 'Selecionar PDF, JPG ou PNG'}
            </Button>}
          </FileButton>
          <Text size="xs" c="dimmed" mt={4}>Obrigatório, até 10 MB.</Text>
        </div>
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancelar</Button>
          <Button onClick={() => void submit()} loading={create.isPending}
            disabled={!proposalId || !amount || !businessDate || !method || !proof}>
            Enviar para aprovação
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
