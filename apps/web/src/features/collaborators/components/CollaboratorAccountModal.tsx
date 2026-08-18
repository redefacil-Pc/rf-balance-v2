import { Alert, Button, Group, Modal, Select, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useMemo, useState } from 'react';

import { useLinkCollaboratorAccount } from '@/features/collaborators/mutations/useLinkCollaboratorAccount';
import { useContasVinculaveis } from '@/features/collaborators/queries/useContasVinculaveis';
import type { Collaborator } from '@/shared/types/organization';

export function CollaboratorAccountModal({ collaborator, onClose }: {
  collaborator: Collaborator | null;
  onClose: () => void;
}) {
  const [userId, setUserId] = useState<number | null>(null);
  const accounts = useContasVinculaveis(collaborator !== null);
  const link = useLinkCollaboratorAccount();

  useEffect(() => {
    setUserId(collaborator?.user_id ?? null);
    link.reset();
  }, [collaborator]); // eslint-disable-line react-hooks/exhaustive-deps

  const options = useMemo(() => {
    const available = (accounts.data?.items ?? []).map((account) => ({
      value: String(account.id),
      label: `${account.full_name} — ${account.email}`,
    }));
    if (collaborator?.user_id && !available.some((item) => item.value === String(collaborator.user_id))) {
      available.unshift({
        value: String(collaborator.user_id),
        label: `${collaborator.user_full_name ?? 'Conta vinculada'} — ${collaborator.user_email ?? `#${collaborator.user_id}`}`,
      });
    }
    return available;
  }, [accounts.data, collaborator]);

  if (!collaborator) return null;
  const changed = userId !== collaborator.user_id;
  return <Modal opened onClose={onClose} title={`Conta de acesso — ${collaborator.full_name}`} centered><Stack>
    <Text size="sm">O vínculo define qual colaborador representa o usuário e quais resultados próprios ele pode consultar.</Text>
    {collaborator.user_id && collaborator.user_is_active === false && <Alert color="yellow">A conta vinculada está inativa e não consegue acessar o sistema.</Alert>}
    {link.error && <Alert color="red" title={link.error.problem.title}>{link.error.problem.detail}</Alert>}
    <Select
      label="Conta vinculada"
      placeholder="Sem conta"
      searchable
      clearable
      disabled={accounts.isPending}
      data={options}
      value={userId ? String(userId) : null}
      onChange={(value) => setUserId(value ? Number(value) : null)}
    />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancelar</Button><Button loading={link.isPending} disabled={!changed} onClick={() => link.mutate({ collaboratorId: collaborator.id, userId }, { onSuccess: () => { notifications.show({ color: 'positivo', title: userId ? 'Conta vinculada' : 'Conta desvinculada', message: collaborator.full_name }); onClose(); } })}>Salvar vínculo</Button></Group>
  </Stack></Modal>;
}
