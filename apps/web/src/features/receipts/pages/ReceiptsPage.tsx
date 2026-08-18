import { ActionIcon, Badge, Button, Card, Group, Select, Stack, Table, Text, Title, Tooltip } from '@mantine/core';
import { IconCalculator, IconDownload, IconReceiptRefund } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import { ReceiptActionModal } from '../components/ReceiptActionModal';
import { CommissionExplanationModal } from '../components/CommissionExplanationModal';
import { useReceipts } from '../queries/useReceipts';
import type { Receipt, ReceiptStatus } from '@/shared/types/receipts';

const labels: Record<ReceiptStatus, string> = {
  SUBMITTED: 'Aguardando financeiro', APPROVED: 'Aprovado', REJECTED: 'Devolvido',
};
const colors: Record<ReceiptStatus, string> = {
  SUBMITTED: 'yellow', APPROVED: 'green', REJECTED: 'red',
};

export function ReceiptsPage() {
  const { usuario, pode } = useAuth();
  const [status, setStatus] = useState<ReceiptStatus | undefined>();
  const query = useReceipts(status);
  const [selected, setSelected] = useState<Receipt | null>(null);
  const [action, setAction] = useState<'DECIDE' | 'REVERSE'>('DECIDE');
  const [explainedReceiptId, setExplainedReceiptId] = useState<number | null>(null);
  const roles = new Set(usuario?.roles ?? []);
  const isFinance = roles.has('FINANCEIRO');
  const openAction = (receipt: Receipt, next: 'DECIDE' | 'REVERSE') => {
    setSelected(receipt); setAction(next);
  };

  return <Stack gap="lg">
    <Group justify="space-between" align="flex-start">
      <div><Title order={2} size="h3">Recebimentos</Title>
        <Text c="dimmed" size="sm">Lançamentos com comprovante, aprovação financeira e histórico de estornos.</Text>
      </div>
    </Group>
    <Card withBorder><Select label="Situação" clearable w={260} value={status ?? null}
      onChange={(value) => setStatus((value as ReceiptStatus | null) ?? undefined)}
      data={Object.entries(labels).map(([value, label]) => ({ value, label }))} /></Card>
    <Card withBorder padding={0}>
      <EstadoDaLista carregando={query.isPending} erro={query.error ?? null}
        vazio={(query.data?.items.length ?? 0) === 0} onTentarNovamente={() => void query.refetch()}
        mensagemVazio="Nenhum recebimento encontrado.">
        <Table.ScrollContainer minWidth={960}><Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead><Table.Tr><Table.Th>Data</Table.Th><Table.Th>Proposta / cliente</Table.Th>
            <Table.Th>Lançado por</Table.Th><Table.Th>Forma</Table.Th><Table.Th ta="right">Valor</Table.Th>
            <Table.Th>Situação</Table.Th><Table.Th>Comprovante</Table.Th><Table.Th>Ações</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>{query.data?.items.map((receipt) => <Table.Tr key={receipt.id}>
            <Table.Td>{receipt.business_date.split('-').reverse().join('/')}</Table.Td>
            <Table.Td><Text size="sm" fw={500}>#{receipt.proposal_id} · {receipt.customer_name}</Text>
              {receipt.reference && <Text size="xs" c="dimmed">{receipt.reference}</Text>}</Table.Td>
            <Table.Td><Text size="sm">{receipt.creator_name}</Text></Table.Td>
            <Table.Td><Text size="sm">{receipt.payment_method}</Text>
              {receipt.receiving_account_label && <Text size="xs" c="dimmed" maw={200}>
                {receipt.receiving_account_label}</Text>}</Table.Td>
            <Table.Td ta="right">{formatarMoeda(receipt.amount)}</Table.Td>
            <Table.Td><Badge color={receipt.reversed ? 'gray' : colors[receipt.status]} variant="light">
              {receipt.reversed ? 'Estornado' : labels[receipt.status]}</Badge>
              {(receipt.rejection_reason || receipt.reversal_reason) && <Text size="xs" c="dimmed" maw={220}>
                {receipt.rejection_reason ?? receipt.reversal_reason}</Text>}</Table.Td>
            <Table.Td><Tooltip label={receipt.proof_file_name}><ActionIcon component="a"
              href={`/api/v1/receipts/${receipt.id}/proof`} aria-label="Baixar comprovante" variant="subtle">
              <IconDownload size={16} /></ActionIcon></Tooltip></Table.Td>
            <Table.Td><Group gap={4} wrap="nowrap">
              {receipt.status === 'APPROVED' && pode('settlements:read') &&
                <Tooltip label="Ver cálculo"><ActionIcon variant="subtle"
                  aria-label="Ver cálculo da comissão" onClick={() => setExplainedReceiptId(receipt.id)}>
                  <IconCalculator size={16} /></ActionIcon></Tooltip>}
              {isFinance && receipt.status === 'SUBMITTED' &&
                receipt.proposal_approval_status === 'APPROVED' &&
                receipt.created_by !== usuario?.id &&
                <Button size="xs" variant="light" onClick={() => openAction(receipt, 'DECIDE')}>Analisar</Button>}
              {isFinance && receipt.status === 'APPROVED' && !receipt.reversed &&
                <Tooltip label="Estornar"><ActionIcon color="red" variant="subtle"
                  aria-label="Estornar recebimento" onClick={() => openAction(receipt, 'REVERSE')}>
                  <IconReceiptRefund size={16} /></ActionIcon></Tooltip>}
            </Group></Table.Td>
          </Table.Tr>)}</Table.Tbody>
        </Table></Table.ScrollContainer>
      </EstadoDaLista>
    </Card>
    <ReceiptActionModal receipt={selected} action={action} onClose={() => setSelected(null)} />
    <CommissionExplanationModal receiptId={explainedReceiptId} onClose={() => setExplainedReceiptId(null)} />
  </Stack>;
}
