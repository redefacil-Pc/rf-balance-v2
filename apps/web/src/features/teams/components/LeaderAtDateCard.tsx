import { Badge, Card, Group, Select, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { useState } from 'react';

import { useCollaborators } from '@/features/collaborators/queries/useCollaborators';
import { useAssignmentHistory, useLeaderAtDate } from '@/features/teams/queries/useAssignments';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { TIPOS_DE_VINCULO, type TipoDeVinculo } from '@/shared/types/organization';

const HOJE = new Date().toISOString().slice(0, 10);

/**
 * Consulta histórica da seção 7.3: quem era o líder numa data, e a linha do
 * tempo completa. É a mesma pergunta que o fechamento de comissão faz.
 */
export function LeaderAtDateCard() {
  const [consultorId, setConsultorId] = useState<number | undefined>();
  const [data, setData] = useState(HOJE);
  const [assignmentType, setAssignmentType] = useState<TipoDeVinculo>('COMERCIAL');

  const colaboradores = useCollaborators({ only_active: true });
  const opcoes = (colaboradores.data?.pages ?? [])
    .flatMap((pagina) => pagina.items)
    .map((c) => ({ value: String(c.id), label: c.full_name }));

  const lider = useLeaderAtDate(consultorId, data, assignmentType);
  const historico = useAssignmentHistory(consultorId);

  return (
    <Card withBorder radius="md" padding="lg">
      <Title order={3} size="h5" mb="md">
        Consulta histórica
      </Title>

      <Group grow align="flex-start" mb="md">
        <Select
          label="Liderado"
          placeholder="Selecione"
          searchable
          data={opcoes}
          value={consultorId ? String(consultorId) : null}
          onChange={(v) => setConsultorId(v ? Number(v) : undefined)}
        />
        <TextInput
          label="Na data"
          type="date"
          value={data}
          onChange={(evento) => setData(evento.currentTarget.value)}
        />
        <Select label="Tipo de vínculo" data={TIPOS_DE_VINCULO.map((tipo) => ({
          value: tipo,
          label: tipo.replaceAll('_', ' '),
        }))} value={assignmentType}
          onChange={(value) => value && setAssignmentType(value as TipoDeVinculo)} />
      </Group>

      {!consultorId ? (
        <Text size="sm" c="dimmed">
          Selecione um colaborador para ver o líder vigente e a linha do tempo dos vínculos.
        </Text>
      ) : (
        <Stack gap="md">
          <div>
            <Text size="sm" fw={600} mb={4}>
              Líder de {assignmentType.replaceAll('_', ' ')} em {data}
            </Text>
            {lider.isPending ? (
              <Text size="sm" c="dimmed">
                Consultando...
              </Text>
            ) : lider.data ? (
              <Group gap="xs">
                <Badge variant="light">#{lider.data.leader_id}</Badge>
                <Text size="sm">{opcoes.find((item) => item.value === String(lider.data?.leader_id))?.label
                  ?? `#${lider.data.leader_id}`} · vínculo de {lider.data.start_date} a {lider.data.end_date ?? 'hoje'}</Text>
              </Group>
            ) : (
              <Text size="sm" c="dimmed">
                Nenhum líder vigente nessa data.
              </Text>
            )}
          </div>

          <div>
            <Text size="sm" fw={600} mb={4}>
              Linha do tempo
            </Text>
            <EstadoDaLista
              carregando={historico.isPending}
              erro={historico.error ?? null}
              vazio={(historico.data ?? []).length === 0}
              mensagemVazio="Este colaborador ainda não tem vínculos registrados."
            >
              <Table striped verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th scope="col">Tipo</Table.Th>
                    <Table.Th scope="col">Líder</Table.Th>
                    <Table.Th scope="col">Início</Table.Th>
                    <Table.Th scope="col">Fim</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(historico.data ?? []).map((vinculo) => (
                    <Table.Tr key={vinculo.id}>
                      <Table.Td>
                        <Badge size="sm" variant="default">
                          {vinculo.assignment_type}
                        </Badge>
                      </Table.Td>
                      <Table.Td>#{vinculo.leader_id}</Table.Td>
                      <Table.Td>{vinculo.start_date}</Table.Td>
                      <Table.Td>
                        {vinculo.end_date ?? (
                          <Badge size="sm" color="positivo" variant="light">
                            vigente
                          </Badge>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </EstadoDaLista>
          </div>
        </Stack>
      )}
    </Card>
  );
}
