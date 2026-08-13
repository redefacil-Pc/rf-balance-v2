import { AppShell, Burger, Group, NavLink, ScrollArea, Stack, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { navegacao } from '@/app/layouts/navegacao';
import { useAuth } from '@/app/providers/AuthProvider';
import { MenuDoUsuario } from '@/shared/components/MenuDoUsuario';

export function AppLayout() {
  const [aberto, { toggle }] = useDisclosure();
  const { pode } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 260, breakpoint: 'sm', collapsed: { mobile: !aberto } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={aberto} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menu" />
            <Title order={1} size="h5">
              RF Balance
            </Title>
          </Group>
          <MenuDoUsuario />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <AppShell.Section grow component={ScrollArea}>
          <Stack gap="lg">
            {navegacao.map((grupo) => {
              const visiveis = grupo.itens.filter((item) => pode(item.permissao));
              if (visiveis.length === 0) {
                return null;
              }
              return (
                <div key={grupo.titulo}>
                  <Text size="xs" fw={600} c="dimmed" tt="uppercase" px="sm" mb={4}>
                    {grupo.titulo}
                  </Text>
                  {visiveis.map((item) => (
                    <NavLink
                      key={item.caminho}
                      label={item.rotulo}
                      leftSection={<item.icone size={18} stroke={1.6} />}
                      active={pathname === item.caminho}
                      onClick={() => navigate(item.caminho)}
                    />
                  ))}
                </div>
              );
            })}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
