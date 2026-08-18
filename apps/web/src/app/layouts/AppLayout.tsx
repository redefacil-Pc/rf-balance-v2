import { AppShell, Box, Burger, Group, NavLink, ScrollArea, Stack, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { navegacao } from '@/app/layouts/navegacao';
import { useAuth } from '@/app/providers/AuthProvider';
import { ColorSchemeToggle } from '@/shared/components/ColorSchemeToggle';
import { MenuDoUsuario } from '@/shared/components/MenuDoUsuario';

export function AppLayout() {
  const [aberto, { close, toggle }] = useDisclosure();
  const { pode } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 272, breakpoint: 'sm', collapsed: { mobile: !aberto } }}
      padding={{ base: 'sm', sm: 'lg' }}
    >
      <AppShell.Header className="rf-shell-header">
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={aberto} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menu" />
            <Box className="rf-brand-mark" aria-hidden="true">RF</Box>
            <div>
              <Text fw={700} lh={1.05}>RF Balance</Text>
              <Text size="xs" c="dimmed" lh={1.2} visibleFrom="xs">Gestão financeira e comissões</Text>
            </div>
          </Group>
          <Group gap="xs">
            <ColorSchemeToggle />
            <MenuDoUsuario />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm" className="rf-shell-navbar">
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
                      className="rf-nav-link"
                      key={item.caminho}
                      label={item.rotulo}
                      leftSection={<item.icone size={18} stroke={1.6} />}
                      active={pathname === item.caminho}
                      onClick={() => {
                        navigate(item.caminho);
                        close();
                      }}
                    />
                  ))}
                </div>
              );
            })}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="rf-app-main">
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
