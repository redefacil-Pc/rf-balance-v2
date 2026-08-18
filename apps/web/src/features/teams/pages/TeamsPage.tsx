import { Grid, Stack, Text, Title } from '@mantine/core';

import { useAuth } from '@/app/providers/AuthProvider';
import { ActiveTeamsCard } from '@/features/teams/components/ActiveTeamsCard';
import { AssignLeaderForm } from '@/features/teams/components/AssignLeaderForm';
import { AssignmentHistoryCard } from '@/features/teams/components/AssignmentHistoryCard';
import { LeaderAtDateCard } from '@/features/teams/components/LeaderAtDateCard';

export function TeamsPage() {
  const { pode } = useAuth();

  return (
    <Stack gap="lg">
      <div>
        <Title order={2} size="h3">
          Equipes
        </Title>
        <Text c="dimmed" size="sm">
          Vínculos consultor-líder com vigência. O líder de uma data passada nunca muda por causa de
          uma alteração feita hoje.
        </Text>
      </div>

      <ActiveTeamsCard />

      <Grid>
        {pode('teams:write') && (
          <Grid.Col span={{ base: 12, lg: 6 }}>
            <AssignLeaderForm />
          </Grid.Col>
        )}
        <Grid.Col span={{ base: 12, lg: pode('teams:write') ? 6 : 12 }}>
          <LeaderAtDateCard />
        </Grid.Col>
        <Grid.Col span={12}><AssignmentHistoryCard canWrite={pode('teams:write')} /></Grid.Col>
      </Grid>
    </Stack>
  );
}
