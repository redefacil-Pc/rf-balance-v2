import { ActionIcon, Button, Group, Modal, Paper, Text, Tooltip } from '@mantine/core';
import { IconDownload, IconEye, IconExternalLink } from '@tabler/icons-react';

import type { Receipt } from '@/shared/types/receipts';

type ReceiptProof = Pick<Receipt, 'id' | 'proof_file_name'>;

interface Props {
  receipt: ReceiptProof | null;
  onClose: () => void;
}

export function ReceiptProofPreviewModal({ receipt, onClose }: Props) {
  const proofUrl = receipt ? `/api/v1/receipts/${receipt.id}/proof` : '';
  const previewUrl = proofUrl ? `${proofUrl}?preview=true` : '';

  return (
    <Modal
      opened={receipt !== null}
      onClose={onClose}
      title={receipt ? `Comprovante — ${receipt.proof_file_name}` : 'Comprovante'}
      closeButtonProps={{ 'aria-label': 'Fechar pré-visualização' }}
      size="min(96vw, 1100px)"
      centered
    >
      {receipt && (
        <>
          <Group justify="space-between" mb="sm">
            <Text size="sm" c="dimmed">
              Confira o documento sem sair da análise.
            </Text>
            <Group gap="xs">
              <Button
                component="a"
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                variant="default"
                size="xs"
                leftSection={<IconExternalLink size={15} />}
              >
                Abrir em nova aba
              </Button>
              <Button
                component="a"
                href={proofUrl}
                size="xs"
                leftSection={<IconDownload size={15} />}
              >
                Baixar
              </Button>
            </Group>
          </Group>
          <Paper withBorder bg="gray.1" style={{ overflow: 'hidden' }}>
            <iframe
              src={previewUrl}
              title={`Pré-visualização de ${receipt.proof_file_name}`}
              style={{ display: 'block', width: '100%', height: '70vh', border: 0 }}
            />
          </Paper>
        </>
      )}
    </Modal>
  );
}

interface TriggerProps {
  onClick: () => void;
  label?: string;
}

export function ReceiptProofPreviewButton({ onClick, label = 'Visualizar comprovante' }: TriggerProps) {
  return (
    <Tooltip label={label}>
      <ActionIcon variant="subtle" aria-label={label} onClick={onClick}>
        <IconEye size={16} />
      </ActionIcon>
    </Tooltip>
  );
}
