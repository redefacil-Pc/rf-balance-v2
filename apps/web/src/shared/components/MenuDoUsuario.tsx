import { Avatar, Group, Menu, Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconLogout } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/app/providers/AuthProvider';
import { useLogout } from '@/features/auth/mutations/useLogout';
import { rotuloDoPapel } from '@/shared/types/organization';

function iniciais(nome: string): string {
  return nome
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase() ?? '')
    .join('');
}

export function MenuDoUsuario() {
  const { usuario } = useAuth();
  const logout = useLogout();
  const navigate = useNavigate();

  if (!usuario) {
    return null;
  }

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <UnstyledButton aria-label="Menu do usuário" className="rf-user-menu">
          <Group gap="xs">
            <Avatar color="marca" radius="xl" size={30}>
              {iniciais(usuario.full_name)}
            </Avatar>
            <div>
              <Text size="sm" fw={500} lh={1.1}>
                {usuario.full_name}
              </Text>
              <Text size="xs" c="dimmed" lh={1.1}>
                {usuario.roles.map(rotuloDoPapel).join(', ')}
              </Text>
            </div>
            <IconChevronDown size={14} />
          </Group>
        </UnstyledButton>
      </Menu.Target>

      <Menu.Dropdown>
        <Menu.Label>{usuario.email}</Menu.Label>
        <Menu.Item
          leftSection={<IconLogout size={16} />}
          onClick={() =>
            logout.mutate(undefined, { onSettled: () => navigate('/login', { replace: true }) })
          }
        >
          Sair
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
