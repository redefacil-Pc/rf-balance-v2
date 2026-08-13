import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Button,
  Code,
  Divider,
  Grid,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { IconAlertTriangle, IconCheck, IconCopy } from '@tabler/icons-react';
import { Controller, useForm } from 'react-hook-form';

import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import { useCreateUser } from '@/features/users/mutations/useCreateUser';
import { useAccessRoles } from '@/features/users/queries/useUsers';
import {
  userSchema,
  type UserForm,
  type UserFormInput,
} from '@/features/users/schemas/user-schema';
import { CampoMascarado } from '@/shared/components/CampoMascarado';
import { mascararDocumento } from '@/shared/formatters/document-mask';
import { PAPEIS, rotuloDoPapel } from '@/shared/types/organization';

const HOJE = new Date().toISOString().slice(0, 10);

export function UserFormModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const criar = useCreateUser();
  const accessRoles = useAccessRoles();
  const companies = useCompanies();
  const {
    control,
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors },
  } = useForm<UserFormInput, unknown, UserForm>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      full_name: '',
      email: '',
      roles: ['OPERACIONAL'],
      is_collaborator: true,
      company_id: null,
      unit_id: null,
      document: '',
      tax_regime: 'MEI',
      function: 'CONSULTOR',
      valid_from: HOJE,
    },
  });
  const companyId = watch('company_id');
  const ehColaborador = watch('is_collaborator');
  const units = useUnits(companyId ?? undefined);

  const close = () => {
    criar.reset();
    reset();
    onClose();
  };

  if (criar.data) {
    return (
      <Modal opened={opened} onClose={close} title="Usuário criado" centered>
        <Stack>
          <Alert
            color="positivo"
            icon={<IconCheck size={18} />}
            title={
              criar.data.collaborator_id ? 'Conta e colaborador criados' : 'Conta criada'
            }
          >
            A senha abaixo aparece somente agora. Envie-a de forma segura para o usuário.
          </Alert>
          <Text size="sm"><strong>Usuário:</strong> {criar.data.email}</Text>
          <Group justify="space-between" wrap="nowrap">
            <Code p="sm" style={{ flex: 1 }}>{criar.data.temporary_password}</Code>
            <Button
              variant="default"
              leftSection={<IconCopy size={16} />}
              onClick={() => void navigator.clipboard.writeText(criar.data.temporary_password)}
            >
              Copiar
            </Button>
          </Group>
          <Button onClick={close}>Concluir</Button>
        </Stack>
      </Modal>
    );
  }

  return (
    <Modal opened={opened} onClose={close} title="Novo usuário" size="lg" centered>
      <form onSubmit={handleSubmit((form) => criar.mutate(form))} noValidate>
        <Stack gap="md">
          {criar.isError && (
            <Alert color="red" icon={<IconAlertTriangle size={18} />} title={criar.error.problem.title}>
              {criar.error.problem.detail}
            </Alert>
          )}

          <Divider label="Conta de acesso" labelPosition="left" />
          <Grid>
            <Grid.Col span={{ base: 12, sm: 7 }}>
              <TextInput label="Nome completo" withAsterisk error={errors.full_name?.message} {...register('full_name')} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 5 }}>
              <TextInput label="E-mail" withAsterisk error={errors.email?.message} {...register('email')} />
            </Grid.Col>
            <Grid.Col span={12}>
              <Controller
                control={control}
                name="roles"
                render={({ field }) => (
                  <MultiSelect
                    label="Perfis de acesso"
                    description="Definem o que a pessoa pode fazer no sistema."
                    withAsterisk
                    data={(accessRoles.data ?? []).map((role) => ({ value: role.code, label: role.name }))}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.roles?.message}
                  />
                )}
              />
            </Grid.Col>
          </Grid>

          <Divider label="Cadastro operacional" labelPosition="left" />
          <Controller
            control={control}
            name="is_collaborator"
            render={({ field }) => (
              <Switch
                label="Esta pessoa também é colaboradora"
                description="Marque para quem participa de propostas e recebe comissão. Administração e financeiro que só usam o sistema podem ficar sem."
                checked={field.value}
                onChange={(evento) => field.onChange(evento.currentTarget.checked)}
              />
            )}
          />

          {ehColaborador && (
          <>
          <Text size="xs" c="dimmed">
            A função determina participação em propostas, hierarquia e comissão; não concede acesso.
          </Text>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="company_id"
                render={({ field }) => (
                  <Select
                    label="Empresa"
                    withAsterisk
                    data={(companies.data ?? []).map((company) => ({ value: String(company.id), label: company.legal_name }))}
                    value={field.value ? String(field.value) : null}
                    onChange={(value) => field.onChange(value ? Number(value) : undefined)}
                    error={errors.company_id?.message}
                  />
                )}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="unit_id"
                render={({ field }) => (
                  <Select
                    label="Unidade"
                    clearable
                    disabled={!companyId}
                    data={(units.data ?? []).map((unit) => ({ value: String(unit.id), label: unit.name }))}
                    value={field.value ? String(field.value) : null}
                    onChange={(value) => field.onChange(value ? Number(value) : null)}
                    error={errors.unit_id?.message}
                  />
                )}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <CampoMascarado
                control={control}
                name="document"
                label="CPF ou CNPJ"
                withAsterisk
                mascarar={mascararDocumento}
                error={errors.document?.message}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 3 }}>
              <Controller
                control={control}
                name="tax_regime"
                render={({ field }) => <Select label="Regime" withAsterisk data={['MEI', 'CLT']} {...field} />}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="function"
                render={({ field }) => (
                  <Select
                    label="Função"
                    withAsterisk
                    data={PAPEIS.map((value) => ({ value, label: rotuloDoPapel(value) }))}
                    {...field}
                  />
                )}
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput type="date" label="Vigente desde" withAsterisk error={errors.valid_from?.message} {...register('valid_from')} />
            </Grid.Col>
          </Grid>
          </>
          )}

          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancelar</Button>
            <Button type="submit" loading={criar.isPending}>Criar usuário</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
