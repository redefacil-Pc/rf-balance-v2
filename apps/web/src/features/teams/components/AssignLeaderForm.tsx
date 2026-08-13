import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Card, Group, Select, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';
import { Controller, useForm } from 'react-hook-form';

import { useCollaborators } from '@/features/collaborators/queries/useCollaborators';
import { useAssignLeader } from '@/features/teams/mutations/useAssignLeader';
import {
  assignmentSchema,
  type AssignmentForm,
} from '@/features/teams/schemas/assignment-schema';
import { rotuloDoPapel, TIPOS_DE_VINCULO } from '@/shared/types/organization';

const HOJE = new Date().toISOString().slice(0, 10);

export function AssignLeaderForm() {
  const vincular = useAssignLeader();
  const colaboradores = useCollaborators({ only_active: true });
  const opcoes = (colaboradores.data?.pages ?? [])
    .flatMap((pagina) => pagina.items)
    .map((c) => ({
      value: String(c.id),
      label: `${c.full_name} — ${c.roles.map(rotuloDoPapel).join(', ') || 's/ função'}`,
    }));

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AssignmentForm>({
    resolver: zodResolver(assignmentSchema),
    defaultValues: { assignment_type: 'COMERCIAL', start_date: HOJE, reason: '' },
  });

  const enviar = handleSubmit((form) => {
    vincular.mutate(form, {
      onSuccess: (vinculo) => {
        notifications.show({
          color: 'positivo',
          title: 'Vínculo registrado',
          message: vinculo.previous_closed_on
            ? `Transferência concluída. O vínculo anterior foi encerrado em ${vinculo.previous_closed_on}.`
            : 'Vínculo criado.',
          autoClose: 8000,
        });
        reset({ assignment_type: form.assignment_type, start_date: form.start_date, reason: '' });
      },
    });
  });

  return (
    <Card withBorder radius="md" padding="lg">
      <Title order={3} size="h5" mb="xs">
        Vincular ou transferir
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Se o liderado já tiver um líder ativo do mesmo tipo, o vínculo anterior é encerrado no dia
        anterior à data informada — sem sobreposição e sem dia sem líder.
      </Text>

      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {vincular.isError && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={vincular.error.problem.title}
              role="alert"
            >
              <Text size="sm">{vincular.error.problem.detail}</Text>
            </Alert>
          )}

          <Group grow align="flex-start">
            <Controller
              control={control}
              name="consultant_id"
              render={({ field }) => (
                <Select
                  label="Liderado"
                  placeholder="Selecione"
                  withAsterisk
                  searchable
                  data={opcoes}
                  value={field.value ? String(field.value) : null}
                  onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                  error={errors.consultant_id?.message}
                />
              )}
            />
            <Controller
              control={control}
              name="leader_id"
              render={({ field }) => (
                <Select
                  label="Líder"
                  placeholder="Selecione"
                  withAsterisk
                  searchable
                  data={opcoes}
                  value={field.value ? String(field.value) : null}
                  onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                  error={errors.leader_id?.message}
                />
              )}
            />
          </Group>

          <Group grow align="flex-start">
            <Controller
              control={control}
              name="assignment_type"
              render={({ field }) => (
                <Select
                  label="Tipo de vínculo"
                  withAsterisk
                  data={TIPOS_DE_VINCULO.map((tipo) => ({
                    value: tipo,
                    label: tipo.replaceAll('_', ' '),
                  }))}
                  value={field.value}
                  onChange={(v) => field.onChange(v)}
                  error={errors.assignment_type?.message}
                />
              )}
            />
            <TextInput
              label="Vigente desde"
              type="date"
              withAsterisk
              error={errors.start_date?.message}
              {...register('start_date')}
            />
          </Group>

          <TextInput
            label="Motivo"
            placeholder="Ex.: transferência para a equipe da Matriz"
            withAsterisk
            error={errors.reason?.message}
            {...register('reason')}
          />

          <Alert variant="light" color="blue" icon={<IconInfoCircle size={16} />}>
            <Text size="xs">
              O motivo fica registrado na auditoria junto com o ator e a data. Papéis incompatíveis
              e colaborador inativo são recusados pelo servidor.
            </Text>
          </Alert>

          <Group justify="flex-end">
            <Button type="submit" loading={vincular.isPending}>
              Registrar vínculo
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}
