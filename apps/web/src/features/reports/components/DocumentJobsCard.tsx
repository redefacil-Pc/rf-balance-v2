import { Alert, Badge, Button, Card, Group, Progress, Stack, Text } from '@mantine/core';
import { IconArchive, IconDownload } from '@tabler/icons-react';

import { useCreateDocumentJob, useDocumentJobs } from '@/features/reports/queries/useDocumentJobs';
import type { FinancialReportScope } from '@/features/reports/queries/useFinancialReport';
import type { Period } from '@/features/settlements/queries/useSettlements';

const statusLabel = {
  PENDING: 'Na fila',
  RUNNING: 'Gerando',
  FAILED: 'Nova tentativa agendada',
  COMPLETED: 'Concluído',
  DEAD_LETTER: 'Falha definitiva',
};

const statusColor = {
  PENDING: 'gray',
  RUNNING: 'blue',
  FAILED: 'yellow',
  COMPLETED: 'green',
  DEAD_LETTER: 'red',
};

export function DocumentJobsCard({ period, scope, scopeReady }: {
  period: Period;
  scope: FinancialReportScope;
  scopeReady: boolean;
}) {
  const jobs = useDocumentJobs();
  const create = useCreateDocumentJob();
  return <Card withBorder>
    <Group justify="space-between" align="flex-start" mb="md">
      <div><Text fw={700}>Documentos em lote</Text>
        <Text size="sm" c="dimmed">Gera um PDF por beneficiário e reúne tudo em um ZIP.</Text></div>
      <Button leftSection={<IconArchive size={16} />} loading={create.isPending}
        disabled={!scopeReady} onClick={() => create.mutate({ period, scope })}>
        Gerar lote ZIP
      </Button>
    </Group>
    {!scopeReady && <Alert color="blue" mb="md">Selecione a unidade ou o líder antes de gerar o lote.</Alert>}
    {create.error && <Alert color="red" mb="md">{create.error.message}</Alert>}
    <Stack gap="sm">
      {(jobs.data?.items ?? []).map((job) => {
        const progress = job.total_items > 0
          ? Math.round((job.processed_items / job.total_items) * 100)
          : job.status === 'COMPLETED' ? 100 : 0;
        return <Card key={job.id} withBorder padding="sm" radius="md">
          <Group justify="space-between" align="flex-start">
            <div><Group gap="xs"><Text size="sm" fw={700}>Lote #{job.id}</Text>
              <Badge variant="light" color={statusColor[job.status]}>{statusLabel[job.status]}</Badge></Group>
              <Text size="xs" c="dimmed">{job.period_start} a {job.period_end} · tentativa {job.attempt_count}/{job.max_attempts}</Text>
            </div>
            {job.archive_ready && <Button component="a" size="xs" variant="light"
              leftSection={<IconDownload size={14} />} href={`/api/v1/document-jobs/${job.id}/download`}>
              Baixar ZIP
            </Button>}
          </Group>
          <Progress value={progress} mt="sm" size="sm" animated={job.status === 'RUNNING'} />
          <Text size="xs" c="dimmed" mt={4}>{job.processed_items} de {job.total_items} PDFs gerados</Text>
          {job.error_message && <Text size="xs" c="red" mt={4}>{job.error_message}</Text>}
        </Card>;
      })}
      {!jobs.isPending && (jobs.data?.items ?? []).length === 0
        && <Text size="sm" c="dimmed">Nenhum lote solicitado ainda.</Text>}
    </Stack>
  </Card>;
}
