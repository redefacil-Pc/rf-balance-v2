import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Code,
  Divider,
  Grid,
  Group,
  Modal,
  MultiSelect,
  PasswordInput,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconKey, IconLock } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import {
  useResetUserPassword,
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
  const [password, setPassword] = useState('');
  const [requireChange, setRequireChange] = useState(true);
  const accessRoles = useAccessRoles();
  const update = useUpdateUser();
  const resetPassword = useResetUserPassword();

  useEffect(() => {
    setName(user?.full_name ?? '');
    setEmail(user?.email ?? '');
    setRoles(user?.roles ?? []);
    setActive(user?.is_active ?? true);
    setPassword('');
    setRequireChange(true);
    update.reset();
    resetPassword.reset();
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) return null;
  const ownAccount = user.id === currentUserId;
  const error = update.error ?? resetPassword.error;

  const save = async () => {
    try {
      await update.mutateAsync({
        id: user.id,
        full_name: name.trim(),
        email: email.trim(),
        roles: ownAccount ? undefined : roles,
        is_active: ownAccount ? undefined : active,
      });
      notifications.show({ color: 'positivo', title: 'Usuário atualizado', message: name.trim() });
      onClose();
    } catch {
      // O Problem Details do backend é apresentado no alerta.
    }
  };

  const generatePassword = () => {
    resetPassword.mutate(
      { id: user.id },
      {
        onSuccess: () =>
          notifications.show({
            color: 'yellow',
            title: 'Senha provisória gerada',
            message: 'As sessões abertas foram encerradas.',
          }),
      },
    );
  };

  const definePassword = () => {
    resetPassword.mutate(
      { id: user.id, password, require_change: requireChange },
      {
        onSuccess: () => {
          setPassword('');
          notifications.show({
            color: 'positivo',
            title: 'Senha definida',
            message: 'As sessões abertas foram encerradas.',
          });
        },
      },
    );
  };

  // espelha `password_policy.TAMANHO_MINIMO`; o backend valida de novo — aqui é
  // só para evitar o ida-e-volta óbvio
  const passwordTooShort = password.length > 0 && password.length < 12;

  const pending = update.isPending;

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
        </Group>

        <Grid align="flex-end">
          <Grid.Col span={{ base: 12, sm: 7 }}>
            <PasswordInput
              label="Definir uma senha"
              description="Deixe em branco para o sistema gerar uma."
              placeholder="Ao menos 12 caracteres"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
              error={passwordTooShort ? 'A senha deve ter ao menos 12 caracteres' : null}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 5 }}>
            <Group gap="xs" wrap="nowrap">
              <Button
                leftSection={<IconLock size={16} />}
                loading={resetPassword.isPending && password.length > 0}
                disabled={password.length < 12}
                onClick={definePassword}
              >
                Definir
              </Button>
              <Button
                variant="default"
                leftSection={<IconKey size={16} />}
                loading={resetPassword.isPending && password.length === 0}
                onClick={generatePassword}
              >
                Gerar
              </Button>
            </Group>
          </Grid.Col>
        </Grid>

        <Checkbox
          label="Exigir troca no próximo acesso"
          description="Quem define a senha passa a conhecê-la. Desmarque apenas para conta de teste ou de serviço."
          checked={requireChange}
          onChange={(event) => setRequireChange(event.currentTarget.checked)}
        />

        {resetPassword.data?.temporary_password && (
          <Alert color="yellow" title="Senha provisória — exibida somente agora">
            <Stack gap="xs">
              <Text size="sm">Envie por um canal seguro. O usuário deverá alterá-la ao entrar.</Text>
              <Group wrap="nowrap">
                <Code p="sm" style={{ flex: 1 }}>{resetPassword.data.temporary_password}</Code>
                <Button
                  variant="default"
                  onClick={() =>
                    void navigator.clipboard.writeText(
                      resetPassword.data?.temporary_password ?? '',
                    )
                  }
                >
                  Copiar
                </Button>
              </Group>
            </Stack>
          </Alert>
        )}

        {resetPassword.data && !resetPassword.data.temporary_password && (
          <Alert color="positivo" title="Senha definida">
            A senha que você informou já está valendo. Ela não é exibida de volta — quem a definiu
            já a conhece.
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
