import { Alert, Button, Group, Modal, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';

import { useDeactivateCollaborator } from '@/features/collaborators/mutations/useDeactivateCollaborator';
import type { Collaborator } from '@/shared/types/organization';

const HOJE = new Date().toISOString().slice(0, 10);

export function CollaboratorDeactivateModal({ collaborator, onClose }: { collaborator: Collaborator | null; onClose: () => void }) {
  const [date, setDate] = useState(HOJE); const [reason, setReason] = useState(''); const deactivate = useDeactivateCollaborator();
  useEffect(() => { setDate(HOJE); setReason(''); deactivate.reset(); }, [collaborator]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!collaborator) return null;
  return <Modal opened onClose={onClose} title={`Inativar — ${collaborator.full_name}`} centered><Stack>
    <Text size="sm">As funções e vínculos ativos serão encerrados na data informada. O histórico continuará disponível.</Text>
    {deactivate.error && <Alert color="red" title={deactivate.error.problem.title}>{deactivate.error.problem.detail}</Alert>}
    <TextInput type="date" label="Data da inativação" withAsterisk value={date} onChange={(e) => setDate(e.currentTarget.value)} />
    <Textarea label="Motivo" withAsterisk minRows={2} value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button color="red" loading={deactivate.isPending} disabled={!date || reason.trim().length < 3} onClick={() => deactivate.mutate({ id: collaborator.id, deactivated_on: date, reason: reason.trim() }, { onSuccess: (result) => { notifications.show({ color: 'positivo', title: 'Colaborador inativado', message: `${result.closed_assignments} vínculo(s) encerrado(s).` }); onClose(); } })}>Inativar</Button></Group>
  </Stack></Modal>;
}
