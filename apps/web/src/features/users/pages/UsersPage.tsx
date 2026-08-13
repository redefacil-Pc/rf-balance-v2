import { Alert, Button, Card, Code, Group, Modal, Stack, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { UserEditModal } from '@/features/users/components/UserEditModal';
import { UserFormModal } from '@/features/users/components/UserFormModal';
import { UserTable } from '@/features/users/components/UserTable';
import { useResetUserPassword, useSetUserStatus } from '@/features/users/mutations/useManageUser';
import { useUsers } from '@/features/users/queries/useUsers';
import type { SystemUser } from '@/features/users/types';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';

export function UsersPage() {
  const [opened, modal] = useDisclosure(false);
  const users = useUsers();
  const { usuario } = useAuth();
  const [editing, setEditing] = useState<SystemUser | null>(null);
  const [changingStatus, setChangingStatus] = useState<SystemUser | null>(null);
  const [resettingPassword, setResettingPassword] = useState<SystemUser | null>(null);
  const statusMutation = useSetUserStatus();
  const passwordMutation = useResetUserPassword();

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2} size="h3">Usuários e acessos</Title>
          <Text c="dimmed" size="sm">
            Crie a conta, os perfis de acesso e a função operacional em uma única operação.
          </Text>
        </div>
        <Button leftSection={<IconPlus size={16} />} onClick={modal.open}>Novo usuário</Button>
      </Group>
      <Card withBorder radius="md" padding={0}>
        <EstadoDaLista
          carregando={users.isPending}
          erro={users.error ?? null}
          vazio={(users.data?.items ?? []).length === 0}
          onTentarNovamente={() => void users.refetch()}
          mensagemVazio="Nenhum usuário cadastrado."
        >
          <UserTable
            users={users.data?.items ?? []}
            currentUserId={usuario?.id}
            onEdit={setEditing}
            onStatus={(user) => { statusMutation.reset(); setChangingStatus(user); }}
            onResetPassword={(user) => { passwordMutation.reset(); setResettingPassword(user); }}
          />
        </EstadoDaLista>
      </Card>
      <UserFormModal opened={opened} onClose={modal.close} />
      <UserEditModal user={editing} currentUserId={usuario?.id} onClose={() => setEditing(null)} />

      <Modal opened={changingStatus !== null} onClose={() => setChangingStatus(null)} title={changingStatus?.is_active ? 'Inativar usuário' : 'Reativar usuário'} centered>
        <Stack>
          <Text size="sm">{changingStatus?.is_active ? 'O acesso será bloqueado e as sessões abertas serão encerradas. O histórico será preservado.' : 'O usuário voltará a poder acessar o sistema.'}</Text>
          {statusMutation.error && <Alert color="red">{statusMutation.error.problem.detail}</Alert>}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setChangingStatus(null)}>Cancelar</Button>
            <Button color={changingStatus?.is_active ? 'red' : 'positivo'} loading={statusMutation.isPending} onClick={() => changingStatus && statusMutation.mutate({ id: changingStatus.id, is_active: !changingStatus.is_active }, { onSuccess: () => { notifications.show({ color: 'positivo', title: changingStatus.is_active ? 'Usuário inativado' : 'Usuário reativado', message: changingStatus.full_name }); setChangingStatus(null); } })}>Confirmar</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={resettingPassword !== null} onClose={() => setResettingPassword(null)} title="Redefinir senha" centered>
        <Stack>
          {!passwordMutation.data && <Text size="sm">Será criada uma senha provisória para {resettingPassword?.full_name} e todas as sessões serão encerradas.</Text>}
          {passwordMutation.error && <Alert color="red">{passwordMutation.error.problem.detail}</Alert>}
          {passwordMutation.data && <><Alert color="yellow" title="Senha exibida somente agora">Envie-a por um canal seguro.</Alert><Code p="sm">{passwordMutation.data.temporary_password}</Code></>}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setResettingPassword(null)}>{passwordMutation.data ? 'Concluir' : 'Cancelar'}</Button>
            {!passwordMutation.data && <Button loading={passwordMutation.isPending} onClick={() => resettingPassword && passwordMutation.mutate(resettingPassword.id)}>Gerar senha provisória</Button>}
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
