import { Badge, Card, Group, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core';
import { useMemo, useState } from 'react';

import { useActiveAssignments } from '@/features/teams/queries/useAssignments';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import type { ActiveTeamAssignment, TipoDeVinculo } from '@/shared/types/organization';

const LABELS: Record<TipoDeVinculo, string> = {
  COMERCIAL: 'Comercial',
  MEI_GERAL: 'MEI geral',
  FINALIZACAO: 'Finalização',
};

interface TeamGroup {
  key: string;
  leaderName: string;
  type: TipoDeVinculo;
  members: ActiveTeamAssignment[];
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

export function ActiveTeamsCard() {
  const [referenceDate, setReferenceDate] = useState(dataLocalHoje);
  const assignments = useActiveAssignments(referenceDate);
  const groups = useMemo<TeamGroup[]>(() => {
    const grouped = new Map<string, TeamGroup>();
    for (const assignment of assignments.data ?? []) {
      const key = `${assignment.leader_id}:${assignment.assignment_type}`;
      const current = grouped.get(key) ?? {
        key,
        leaderName: assignment.leader_name,
        type: assignment.assignment_type,
        members: [],
      };
      current.members.push(assignment);
      grouped.set(key, current);
    }
    return [...grouped.values()].sort((a, b) =>
      a.leaderName.localeCompare(b.leaderName, 'pt-BR') || LABELS[a.type].localeCompare(LABELS[b.type], 'pt-BR'),
    );
  }, [assignments.data]);

  return (
    <Card withBorder radius="md" padding="lg">
      <Group justify="space-between" align="flex-end" mb="md">
        <div>
          <Title order={3} size="h5">Equipes vigentes</Title>
          <Text size="sm" c="dimmed">Vínculos agrupados por líder e finalidade da equipe.</Text>
        </div>
        <TextInput
          type="date"
          label="Na data"
          value={referenceDate}
          onChange={(event) => setReferenceDate(event.currentTarget.value)}
          w={170}
        />
      </Group>

      <EstadoDaLista
        carregando={assignments.isPending}
        erro={assignments.error ?? null}
        vazio={groups.length === 0}
        onTentarNovamente={() => void assignments.refetch()}
        mensagemVazio="Nenhum vínculo de equipe vigente nessa data."
      >
        <SimpleGrid cols={{ base: 1, md: 2, xl: 3 }} spacing="md">
          {groups.map((group) => (
            <Card key={group.key} withBorder radius="md" padding="md">
              <Stack gap="sm">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Text fw={700}>{group.leaderName}</Text>
                    <Text size="xs" c="dimmed">Líder da equipe</Text>
                  </div>
                  <Badge variant="light">{LABELS[group.type]}</Badge>
                </Group>
                <Text size="xs" fw={600} tt="uppercase" c="dimmed">
                  {group.members.length} {group.members.length === 1 ? 'integrante' : 'integrantes'}
                </Text>
                <Stack gap={6}>
                  {group.members.map((member) => (
                    <Group key={member.id} justify="space-between" gap="xs" wrap="nowrap">
                      <Text size="sm">{member.member_name}</Text>
                      <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                        desde {formatDate(member.start_date)}
                      </Text>
                    </Group>
                  ))}
                </Stack>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      </EstadoDaLista>
    </Card>
  );
}
