import { Alert, Badge, Card, Grid, Group, Stack, Text, Title } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

import { useAuth } from '@/app/providers/AuthProvider';
import { rotuloDoPapel } from '@/shared/types/organization';

/**
 * Dashboard da F1: confirma sessão, papéis e permissões efetivas.
 * Os indicadores da seção 7.14 do blueprint entram na F6, lendo read models —
 * até então não há número para mostrar, e número inventado aqui seria pior que
 * tela vazia.
 */
export function DashboardPage() {
  const { usuario } = useAuth();

  if (!usuario) {
    return null;
  }

  return (
    <Stack gap="lg">
      <div>
        <Title order={2} size="h3">
          Olá, {usuario.full_name.split(' ')[0]}
        </Title>
        <Text c="dimmed" size="sm">
          Sessão ativa em {usuario.email}
        </Text>
      </div>

      <Alert variant="light" color="blue" icon={<IconInfoCircle size={18} />} title="Fase F1">
        <Text size="sm">
          Fundação concluída: autenticação, sessão revogável, RBAC e auditoria. Os indicadores do
          dashboard entram na F6, quando os read models existirem.
        </Text>
      </Alert>

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="md" padding="lg" h="100%">
            <Text fw={600} mb="xs">
              Papéis
            </Text>
            <Group gap="xs">
              {usuario.roles.map((papel) => (
                <Badge key={papel} variant="light">
                  {rotuloDoPapel(papel)}
                </Badge>
              ))}
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder radius="md" padding="lg" h="100%">
            <Group justify="space-between" mb="xs">
              <Text fw={600}>Permissões efetivas</Text>
              <Badge variant="default">{usuario.permissions.length}</Badge>
            </Group>
            <Text size="xs" c="dimmed">
              Concedidas pelos papéis acima. A verificação vale no backend em toda requisição —
              esconder um item de menu não é autorização.
            </Text>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
