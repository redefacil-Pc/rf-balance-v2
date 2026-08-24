import {
  AppShell,
  Badge,
  Box,
  Burger,
  Collapse,
  Group,
  NavLink,
  Paper,
  ScrollArea,
  Stack,
  Text,
  ThemeIcon,
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconChevronDown, IconShieldCheck } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { navegacao } from '@/app/layouts/navegacao';
import { useAuth } from '@/app/providers/AuthProvider';
import { preloadRoute } from '@/app/router/route-modules';
import { usePendingProposalCount } from '@/features/proposals/queries/usePendingProposalCount';
import { ColorSchemeToggle } from '@/shared/components/ColorSchemeToggle';
import { MenuDoUsuario } from '@/shared/components/MenuDoUsuario';

const STORAGE_GRUPOS_ABERTOS = 'rfbalance:navigation-open-groups';

function gruposAbertosSalvos(): Set<string> {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_GRUPOS_ABERTOS) ?? '[]');
    return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []);
  } catch {
    return new Set();
  }
}

export function AppLayout() {
  const [aberto, { close, toggle }] = useDisclosure();
  const { pode } = useAuth();
  const podeAprovar = pode('proposals:approve');
  const pendencias = usePendingProposalCount(podeAprovar);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const paginaAtual = navegacao.flatMap((grupo) => grupo.itens)
    .find((item) => item.caminho === pathname);
  const grupoDaPagina = navegacao.find((grupo) =>
    grupo.itens.some((item) => item.caminho === pathname),
  )?.titulo ?? null;
  const [gruposAbertos, setGruposAbertos] = useState<Set<string>>(() => {
    const salvos = gruposAbertosSalvos();
    if (grupoDaPagina) salvos.add(grupoDaPagina);
    return salvos;
  });

  useEffect(() => {
    if (grupoDaPagina) {
      setGruposAbertos((atuais) => {
        if (atuais.has(grupoDaPagina)) return atuais;
        return new Set([...atuais, grupoDaPagina]);
      });
    }
  }, [grupoDaPagina]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_GRUPOS_ABERTOS, JSON.stringify([...gruposAbertos]));
    } catch {
      // Navegação continua funcional em modo privado ou com storage bloqueado.
    }
  }, [gruposAbertos]);

  return (
    <AppShell
      header={{ height: 68 }}
      navbar={{ width: 284, breakpoint: 'sm', collapsed: { mobile: !aberto } }}
      padding={{ base: 'sm', sm: 'xl' }}
    >
      <AppShell.Header className="rf-shell-header">
        <Group h="100%" px={{ base: 'md', sm: 'xl' }} justify="space-between">
          <Group gap="sm">
            <Burger opened={aberto} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menu" />
            <UnstyledButton
              component={Link}
              to="/"
              className="rf-brand-link"
              aria-label="Ir para o dashboard"
              onClick={close}
              onFocus={() => preloadRoute('/')}
              onPointerEnter={() => preloadRoute('/')}
            >
              <Group gap="sm" wrap="nowrap">
                <Box className="rf-brand-mark" aria-hidden="true">RF</Box>
                <div>
                  <Text fw={750} lh={1.05} fz="md" lts="-0.02em" title={paginaAtual?.rotulo}>
                    RF Balance
                  </Text>
                  <Text size="xs" c="dimmed" lh={1.2} visibleFrom="xs">
                    {paginaAtual?.rotulo ?? 'Gestão financeira e comissões'}
                  </Text>
                </div>
              </Group>
            </UnstyledButton>
          </Group>
          <Group gap="xs">
            <ColorSchemeToggle />
            <MenuDoUsuario />
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" className="rf-shell-navbar">
        <AppShell.Section grow component={ScrollArea}>
          <Stack gap="xs">
            {navegacao.map((grupo) => {
              const visiveis = grupo.itens.filter((item) => pode(item.permissao));
              if (visiveis.length === 0) {
                return null;
              }
              const expandido = gruposAbertos.has(grupo.titulo);
              return (
                <div className="rf-nav-group" key={grupo.titulo} data-open={expandido || undefined}>
                  <UnstyledButton
                    className="rf-nav-group-trigger"
                    onClick={() => setGruposAbertos((atuais) => {
                      const proximos = new Set(atuais);
                      if (proximos.has(grupo.titulo)) proximos.delete(grupo.titulo);
                      else proximos.add(grupo.titulo);
                      return proximos;
                    })}
                    aria-expanded={expandido}
                    aria-controls={`menu-${grupo.titulo.toLowerCase().replaceAll(' ', '-')}`}
                  >
                    <Group justify="space-between" wrap="nowrap">
                      <Text size="10px" fw={800} tt="uppercase" lts="0.11em">
                        {grupo.titulo}
                      </Text>
                      <IconChevronDown
                        className="rf-nav-group-chevron"
                        size={15}
                        stroke={1.8}
                        aria-hidden="true"
                      />
                    </Group>
                  </UnstyledButton>
                  <Collapse in={expandido}>
                    <Box
                      className="rf-nav-group-items"
                      id={`menu-${grupo.titulo.toLowerCase().replaceAll(' ', '-')}`}
                    >
                      {visiveis.map((item) => (
                        <NavLink
                          className="rf-nav-link"
                          key={item.caminho}
                          label={item.rotulo}
                          leftSection={<item.icone size={18} stroke={1.6} />}
                          rightSection={
                            item.caminho === '/proposal-approvals' && (pendencias.data?.count ?? 0) > 0
                              ? <Badge size="sm" circle aria-label={`${pendencias.data?.count} propostas pendentes`}>
                                  {pendencias.data?.count}
                                </Badge>
                              : undefined
                          }
                          active={pathname === item.caminho}
                          onFocus={() => preloadRoute(item.caminho)}
                          onPointerEnter={() => preloadRoute(item.caminho)}
                          onClick={() => {
                            navigate(item.caminho);
                            close();
                          }}
                        />
                      ))}
                    </Box>
                  </Collapse>
                </div>
              );
            })}
          </Stack>
        </AppShell.Section>
        <AppShell.Section mt="md">
          <Paper className="rf-navbar-footer" p="sm" radius="lg">
            <Group gap="sm" wrap="nowrap">
              <ThemeIcon variant="light" color="teal" radius="xl" size={34}>
                <IconShieldCheck size={17} />
              </ThemeIcon>
              <div>
                <Text size="xs" fw={700}>Ambiente protegido</Text>
                <Text size="10px" c="dimmed">Sessão e auditoria ativas</Text>
              </div>
            </Group>
          </Paper>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="rf-app-main">
        <Box className="rf-content-frame">
          <Outlet />
        </Box>
      </AppShell.Main>
    </AppShell>
  );
}
