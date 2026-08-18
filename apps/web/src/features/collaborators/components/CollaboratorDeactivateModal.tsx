import { Alert, Button, Group, Modal, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useState } from 'react';

import { useActivateCollaborator, useDeactivateCollaborator } from '@/features/collaborators/mutations/useDeactivateCollaborator';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import type { Collaborator } from '@/shared/types/organization';

const HOJE = dataLocalHoje();

export function CollaboratorDeactivateModal({ collaborator, onClose }: { collaborator: Collaborator | null; onClose: () => void }) {
  const [date, setDate] = useState(HOJE); const [reason, setReason] = useState(''); const deactivate = useDeactivateCollaborator();
  const activate = useActivateCollaborator();
  useEffect(() => { setDate(HOJE); setReason(''); deactivate.reset(); activate.reset(); }, [collaborator]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!collaborator) return null;
  const inativando = collaborator.is_active;
  const error = deactivate.error ?? activate.error;
  const confirmar = () => {
    if (inativando) {
      deactivate.mutate({ id: collaborator.id, deactivated_on: date, reason: reason.trim() }, { onSuccess: (result) => { notifications.show({ color: 'positivo', title: 'Colaborador inativado', message: `${result.closed_assignments} vínculo(s) e ${result.closed_functions} função(ões) encerrados.` }); onClose(); } });
      return;
    }
    activate.mutate({ id: collaborator.id, activated_on: date, reason: reason.trim() }, { onSuccess: () => { notifications.show({ color: 'positivo', title: 'Colaborador reativado', message: 'Atribua as novas funções com a vigência correta.' }); onClose(); } });
  };
  return <Modal opened onClose={onClose} title={`${inativando ? 'Inativar' : 'Reativar'} — ${collaborator.full_name}`} centered><Stack>
    <Text size="sm">{inativando ? 'As funções e vínculos ativos serão encerrados hoje. O histórico continuará disponível.' : 'O cadastro voltará a ficar ativo. As funções encerradas não serão reabertas automaticamente.'}</Text>
    {error && <Alert color="red" title={error.problem.title}>{error.problem.detail}</Alert>}
    <TextInput type="date" label={`Data da ${inativando ? 'inativação' : 'reativação'}`} min={HOJE} max={HOJE} withAsterisk value={date} onChange={(e) => setDate(e.currentTarget.value)} />
    <Textarea label="Motivo" withAsterisk minRows={2} value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button color={inativando ? 'red' : 'positivo'} loading={deactivate.isPending || activate.isPending} disabled={date !== HOJE || reason.trim().length < 3} onClick={confirmar}>{inativando ? 'Inativar' : 'Reativar'}</Button></Group>
  </Stack></Modal>;
}
