import {
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDatabaseExport, IconRefresh, IconShieldCheck } from '@tabler/icons-react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useOperationsStatus, useRunBackup } from '@/features/operations/queries/useOperations';

function timestamp(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'medium',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(value));
}

function bytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

const nomes: Record<string, string> = {
  team_assignment_overlaps: 'Sobreposição de equipes',
  proposal_receipt_cache_divergences: 'Saldo de propostas e recebimentos',
};

export function OperationsPage() {
  const { pode } = useAuth();
  const status = useOperationsStatus();
  const backup = useRunBackup();
  const data = status.data;

  const executarBackup = () => backup.mutate(undefined, {
    onSuccess: (result) => notifications.show({
      color: 'positivo',
      title: 'Backup concluído e verificado',
      message: `${bytes(result.compressed_bytes)} armazenados com integridade confirmada.`,
    }),
  });

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2} size="h3">Operações administrativas</Title>
          <Text size="sm" c="dimmed">
            Continuidade do banco, retenção e verificações automáticas de integridade.
          </Text>
        </div>
        <Button variant="default" leftSection={<IconRefresh size={16} />}
          loading={status.isFetching} onClick={() => void status.refetch()}>
          Atualizar
        </Button>
      </Group>

      {status.error && <Alert color="red" title="Não foi possível consultar as operações">
        {status.error.problem.detail}
      </Alert>}
      {backup.error && <Alert color="red" title="O backup manual falhou">
        {backup.error.problem.detail}
      </Alert>}

      {status.isPending ? <Skeleton height={230} radius="md" /> : data && <>
        <Card withBorder padding="lg">
          <Group justify="space-between" align="flex-start" mb="lg">
            <Group gap="sm">
              <IconDatabaseExport size={24} />
              <div>
                <Title order={3} size="h4">Backup do banco</Title>
                <Text size="sm" c="dimmed">
                  Diário às {String((data.backup.schedule_hour_utc + 21) % 24).padStart(2, '0')}:00,
                  horário de Brasília · retenção de {data.backup.retention_days} dias
                </Text>
              </div>
            </Group>
            <Badge color={data.backup.enabled ? 'green' : 'red'} variant="light">
              {data.backup.enabled ? 'Ativo' : 'Desativado'}
            </Badge>
          </Group>

          {data.backup.last_backup ? <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
            <div><Text size="xs" c="dimmed">Última execução</Text>
              <Text fw={600}>{timestamp(data.backup.last_backup.created_at)}</Text></div>
            <div><Text size="xs" c="dimmed">Tamanho compactado</Text>
              <Text fw={600}>{bytes(data.backup.last_backup.compressed_bytes)}</Text></div>
            <div><Text size="xs" c="dimmed">Integridade</Text>
              <Badge color={data.backup.last_backup.verified ? 'green' : 'red'}>
                {data.backup.last_backup.verified ? 'Verificado após envio' : 'Não verificado'}
              </Badge></div>
            <div><Text size="xs" c="dimmed">Namespace</Text>
              <Code>{data.backup.prefix}</Code></div>
          </SimpleGrid> : <Alert color="yellow">Nenhum backup foi encontrado.</Alert>}

          <Group gap="xs" mt="md">
            <Badge color={data.backup.versioning_enabled ? 'green' : 'red'} variant="light">
              Versionamento {data.backup.versioning_enabled ? 'ativo' : 'inativo'}
            </Badge>
            <Badge color={data.backup.local_replica_enabled ? 'green' : 'red'} variant="light">
              Réplica local {data.backup.local_replica_enabled ? 'ativa' : 'inativa'}
            </Badge>
          </Group>

          {pode('backups:run') && <Group justify="flex-end" mt="lg">
            <Button leftSection={<IconDatabaseExport size={16} />} loading={backup.isPending}
              disabled={!data.backup.enabled} onClick={executarBackup}>
              Executar backup agora
            </Button>
          </Group>}
        </Card>

        <Card withBorder padding="lg">
          <Group gap="sm" mb="lg"><IconShieldCheck size={24} />
            <div><Title order={3} size="h4">Integridade dos dados</Title>
              <Text size="sm" c="dimmed">Último resultado gravado pelo scheduler.</Text></div>
          </Group>
          {data.integrity_checks.length ? <SimpleGrid cols={{ base: 1, md: 2 }}>
            {data.integrity_checks.map((check) => <Card withBorder key={check.check_type} padding="md">
              <Group justify="space-between"><Text fw={600}>{nomes[check.check_type] ?? check.check_type}</Text>
                <Badge color={check.status === 'PASS' ? 'green' : 'red'}>
                  {check.status === 'PASS' ? 'Íntegro' : `${check.count} divergência(s)`}
                </Badge></Group>
              <Text size="xs" c="dimmed" mt="xs">Verificado em {timestamp(check.checked_at)}</Text>
            </Card>)}
          </SimpleGrid> : <Alert color="yellow">O scheduler ainda não registrou uma verificação.</Alert>}
        </Card>
      </>}
    </Stack>
  );
}
