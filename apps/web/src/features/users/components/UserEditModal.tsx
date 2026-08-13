import {
  Alert,
  Badge,
  Button,
  Code,
  Divider,
  Grid,
  Group,
  Modal,
  MultiSelect,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconKey } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import {
  useResetUserPassword,
  useSetUserRoles,
  useSetUserStatus,
  useUpdateUser,
} from '@/features/users/mutations/useManageUser';
import { useAccessRoles } from '@/features/users/queries/useUsers';
import type { SystemUser } from '@/features/users/types';

interface Props {
  user: SystemUser | null;
  currentUserId?: number;
  onClose: () => void;
}

function formatLastLogin(value: string | null): string {
  if (!value) return 'Nunca acessou';
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(
    new Date(value),
  );
}

export function UserEditModal({ user, currentUserId, onClose }: Props) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [roles, setRoles] = useState<string[]>([]);
  const [active, setActive] = useState(true);
  const accessRoles = useAccessRoles();
  const update = useUpdateUser();
  const setUserRoles = useSetUserRoles();
  const setStatus = useSetUserStatus();
  const resetPassword = useResetUserPassword();

  useEffect(() => {
    setName(user?.full_name ?? '');
    setEmail(user?.email ?? '');
    setRoles(user?.roles ?? []);
    setActive(user?.is_active ?? true);
    update.reset();
    setUserRoles.reset();
    setStatus.reset();
    resetPassword.reset();
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) return null;
  const ownAccount = user.id === currentUserId;
  const error = update.error ?? setUserRoles.error ?? setStatus.error ?? resetPassword.error;

  const save = async () => {
    try {
      await update.mutateAsync({ id: user.id, full_name: name.trim(), email: email.trim() });
      if (!ownAccount && roles.slice().sort().join() !== user.roles.slice().sort().join()) {
        await setUserRoles.mutateAsync({ id: user.id, roles });
      }
      if (!ownAccount && active !== user.is_active) {
        await setStatus.mutateAsync({ id: user.id, is_active: active });
      }
      notifications.show({ color: 'positivo', title: 'Usuário atualizado', message: name.trim() });
      onClose();
    } catch {
      // O Problem Details do backend é apresentado no alerta.
    }
  };

  const generatePassword = () => {
    resetPassword.mutate(user.id, {
      onSuccess: () =>
        notifications.show({
          color: 'yellow',
          title: 'Senha provisória gerada',
          message: 'As sessões abertas foram encerradas.',
        }),
    });
  };

  const pending = update.isPending || setUserRoles.isPending || setStatus.isPending;

  return (
    <Modal
      opened
      onClose={onClose}
      title={`Editar usuário — ${user.full_name}`}
      size="lg"
      centered
    >
      <Stack gap="md">
        {error && (
          <Alert color="red" title={error.problem.title}>
            {error.problem.detail}
          </Alert>
        )}

        <Divider label="Dados da conta" labelPosition="left" />
        <Grid>
          <Grid.Col span={{ base: 12, sm: 7 }}>
            <TextInput
              label="Nome completo"
              withAsterisk
              value={name}
              onChange={(event) => setName(event.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 5 }}>
            <TextInput
              label="E-mail"
              withAsterisk
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
            />
          </Grid.Col>
        </Grid>

        <Divider label="Acesso ao sistema" labelPosition="left" />
        <MultiSelect
          label="Perfis de acesso"
          description={
            ownAccount
              ? 'Seus próprios perfis só podem ser alterados por outro administrador.'
              : 'Definem as permissões deste usuário no sistema.'
          }
          disabled={ownAccount}
          withAsterisk
          data={(accessRoles.data ?? []).map((role) => ({ value: role.code, label: role.name }))}
          value={roles}
          onChange={setRoles}
        />
        <Group justify="space-between" align="center">
          <div>
            <Text size="sm" fw={500}>Situação da conta</Text>
            <Text size="xs" c="dimmed">
              Ao inativar, todas as sessões abertas são encerradas.
            </Text>
          </div>
          <Switch
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
            disabled={ownAccount}
            label={active ? 'Ativo' : 'Inativo'}
          />
        </Group>

        <Divider label="Segurança" labelPosition="left" />
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Stack gap={3}>
            <Group gap="xs">
              <Text size="sm">Último acesso:</Text>
              <Text size="sm" fw={500}>{formatLastLogin(user.last_login_at)}</Text>
            </Group>
            <Group gap="xs">
              <Text size="sm">Troca de senha:</Text>
              <Badge size="sm" color={user.must_change_password || resetPassword.data ? 'yellow' : 'positivo'} variant="light">
                {user.must_change_password || resetPassword.data ? 'Obrigatória no próximo acesso' : 'Senha definida'}
              </Badge>
            </Group>
          </Stack>
          {!resetPassword.data && (
            <Button
              variant="default"
              leftSection={<IconKey size={16} />}
              loading={resetPassword.isPending}
              onClick={generatePassword}
            >
              Gerar nova senha
            </Button>
          )}
        </Group>

        {resetPassword.data && (
          <Alert color="yellow" title="Senha provisória — exibida somente agora">
            <Stack gap="xs">
              <Text size="sm">Envie por um canal seguro. O usuário deverá alterá-la ao entrar.</Text>
              <Group wrap="nowrap">
                <Code p="sm" style={{ flex: 1 }}>{resetPassword.data.temporary_password}</Code>
                <Button
                  variant="default"
                  onClick={() => void navigator.clipboard.writeText(resetPassword.data.temporary_password)}
                >
                  Copiar
                </Button>
              </Group>
            </Stack>
          </Alert>
        )}

        <Text size="xs" c="dimmed">
          Empresa, unidade, regime e função são editados em Colaboradores para preservar o histórico operacional.
        </Text>

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Cancelar</Button>
          <Button
            onClick={() => void save()}
            loading={pending}
            disabled={name.trim().length < 3 || !email.includes('@') || roles.length === 0}
          >
            Salvar alterações
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
