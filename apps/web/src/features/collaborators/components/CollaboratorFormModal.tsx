import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Button,
  Divider,
  Grid,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconPlus, IconTrash } from '@tabler/icons-react';
import { Controller, useFieldArray, useForm } from 'react-hook-form';

import { useCreateCollaborator } from '@/features/collaborators/mutations/useCreateCollaborator';
import { useContasVinculaveis } from '@/features/collaborators/queries/useContasVinculaveis';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import {
  collaboratorSchema,
  type CollaboratorForm,
  type CollaboratorFormEntrada,
} from '@/features/collaborators/schemas/collaborator-schema';
import { CampoMascarado } from '@/shared/components/CampoMascarado';
import { mascararDocumento } from '@/shared/formatters/document-mask';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import {
  mascararChavePix,
  placeholderDaChavePix,
  type TipoDeChavePix,
} from '@/shared/formatters/pix-mask';
import { PAPEIS, rotuloDoPapel } from '@/shared/types/organization';

interface Props {
  aberto: boolean;
  onFechar: () => void;
}

const HOJE = dataLocalHoje();

export function CollaboratorFormModal({ aberto, onFechar }: Props) {
  const criar = useCreateCollaborator();
  const empresas = useCompanies();

  const {
    control,
    register,
    handleSubmit,
    watch,
    reset,
    setError,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<CollaboratorFormEntrada, unknown, CollaboratorForm>({
    resolver: zodResolver(collaboratorSchema),
    defaultValues: {
      company_id: undefined,
      unit_id: null,
      full_name: '',
      document: '',
      tax_regime: 'MEI',
      roles: [{ role: 'CONSULTOR', valid_from: HOJE }],
      email: '',
      user_id: null,
    },
  });

  const companyId = watch('company_id');
  const funcoes = watch('roles');
  const tipoDaChave = watch('payment_key_type');
  const unidades = useUnits(companyId);
  const contas = useContasVinculaveis(aberto);
  const papeis = useFieldArray({ control, name: 'roles' });

  const enviar = handleSubmit((form) => {
    criar.mutate(form, {
      onSuccess: (colaborador) => {
        notifications.show({
          color: 'positivo',
          title: 'Colaborador cadastrado',
          message: `${colaborador.full_name} — documento ${colaborador.document}`,
        });
        reset();
        onFechar();
      },
      onError: (erro) => {
        // erro de campo vindo do backend cai no campo certo
        for (const [campo, mensagem] of Object.entries(erro.erroDeCampo)) {
          setError(campo as keyof CollaboratorFormEntrada, { message: mensagem });
        }
      },
    });
  });

  return (
    <Modal opened={aberto} onClose={onFechar} title="Novo colaborador" size="lg" centered>
      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {criar.isError && Object.keys(criar.error.erroDeCampo).length === 0 && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={criar.error.problem.title}
              role="alert"
            >
              <Text size="sm">{criar.error.problem.detail}</Text>
            </Alert>
          )}

          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="company_id"
                render={({ field }) => (
                  <Select
                    label="Empresa"
                    placeholder="Selecione"
                    withAsterisk
                    data={(empresas.data ?? []).map((e) => ({
                      value: String(e.id),
                      label: e.legal_name,
                    }))}
                    value={field.value ? String(field.value) : null}
                    onChange={(v) => {
                      field.onChange(v ? Number(v) : undefined);
                      setValue('unit_id', null);
                    }}
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
                    placeholder={companyId ? 'Selecione' : 'Escolha a empresa primeiro'}
                    clearable
                    disabled={!companyId}
                    data={(unidades.data ?? []).map((u) => ({
                      value: String(u.id),
                      label: u.name,
                    }))}
                    value={field.value ? String(field.value) : null}
                    onChange={(v) => field.onChange(v ? Number(v) : null)}
                    error={errors.unit_id?.message}
                  />
                )}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 7 }}>
              <TextInput
                label="Nome completo"
                withAsterisk
                error={errors.full_name?.message}
                {...register('full_name')}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 5 }}>
              <CampoMascarado
                control={control}
                name="document"
                label="CPF ou CNPJ"
                placeholder="000.000.000-00"
                mascarar={mascararDocumento}
                withAsterisk
                error={errors.document?.message}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 4 }}>
              <Controller
                control={control}
                name="tax_regime"
                render={({ field }) => (
                  <Select
                    label="Regime"
                    description="Define somente o vínculo do colaborador."
                    withAsterisk
                    data={['MEI', 'CLT']}
                    value={field.value}
                    onChange={(v) => field.onChange(v)}
                    error={errors.tax_regime?.message}
                  />
                )}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 8 }}>
              <TextInput label="E-mail" error={errors.email?.message} {...register('email')} />
            </Grid.Col>
          </Grid>

          <Stack gap={2}>
            <Divider label="Conta de acesso (opcional)" labelPosition="left" />
            <Text size="xs" c="dimmed">
              Vincule uma conta já criada para esta pessoa acompanhar os próprios resultados.
              Quem não usa o sistema — o BKO, por exemplo — fica sem conta.
            </Text>
            <Controller
              control={control}
              name="user_id"
              render={({ field }) => (
                <Select
                  label="Conta"
                  placeholder={
                    contas.data && contas.data.items.length === 0
                      ? 'Nenhuma conta disponível para vínculo'
                      : 'Sem conta'
                  }
                  clearable
                  searchable
                  disabled={contas.isPending || contas.data?.items.length === 0}
                  data={(contas.data?.items ?? []).map((conta) => ({
                    value: String(conta.id),
                    label: `${conta.full_name} — ${conta.email}`,
                  }))}
                  value={field.value ? String(field.value) : null}
                  onChange={(valor) => field.onChange(valor ? Number(valor) : null)}
                  error={errors.user_id?.message}
                />
              )}
            />
          </Stack>

          <Stack gap={2}>
            <Divider label="Funções e vigência" labelPosition="left" />
            <Text size="xs" c="dimmed">
              Uma pessoa pode acumular funções; cada uma tem a sua vigência.
            </Text>
          </Stack>

          <Stack gap="xs">
            {papeis.fields.map((campo, indice) => (
              <Group key={campo.id} align="flex-end" gap="xs" wrap="nowrap">
                <Controller
                  control={control}
                  name={`roles.${indice}.role`}
                  render={({ field }) => (
                    <Select
                      label={indice === 0 ? 'Função' : undefined}
                      data={PAPEIS.filter((papel) => {
                        const ehModalidade = papel === 'CONSULTOR' || papel === 'CONSULTOR_MEI_ESCALONADO';
                        if (!ehModalidade) return true;
                        return !funcoes.some((item, outroIndice) => outroIndice !== indice
                          && (item.role === 'CONSULTOR' || item.role === 'CONSULTOR_MEI_ESCALONADO'));
                      }).map((papel) => ({
                        value: papel,
                        label: rotuloDoPapel(papel),
                      }))}
                      value={field.value}
                      onChange={(v) => field.onChange(v)}
                      flex={1}
                    />
                  )}
                />
                <TextInput
                  label={indice === 0 ? 'Vigente desde' : undefined}
                  type="date"
                  w={170}
                  error={errors.roles?.[indice]?.valid_from?.message}
                  {...register(`roles.${indice}.valid_from`)}
                />
                <Button
                  variant="subtle"
                  color="red"
                  onClick={() => papeis.remove(indice)}
                  disabled={papeis.fields.length === 1}
                  aria-label="Remover função"
                >
                  <IconTrash size={16} />
                </Button>
              </Group>
            ))}

            <Button
              variant="light"
              size="xs"
              leftSection={<IconPlus size={14} />}
              onClick={() => papeis.append({ role: 'CONSULTOR', valid_from: HOJE })}
              w="fit-content"
            >
              Adicionar função
            </Button>
            {errors.roles?.message && (
              <Text size="xs" c="red">
                {errors.roles.message}
              </Text>
            )}
          </Stack>

          <Stack gap={2}>
            <Divider label="Chave PIX (opcional)" labelPosition="left" />
            <Text size="xs" c="dimmed">
              Dado sensível: depois de salva, só quem tem permissão financeira consegue vê-la.
            </Text>
          </Stack>

          <Group grow align="flex-start">
            <Controller
              control={control}
              name="payment_key_type"
              render={({ field }) => (
                <Select
                  label="Tipo"
                  placeholder="Selecione"
                  clearable
                  data={['CPF', 'CNPJ', 'EMAIL', 'TELEFONE', 'ALEATORIA']}
                  value={field.value ?? null}
                  onChange={(v) => {
                    const tipo = (v ?? undefined) as TipoDeChavePix | undefined;
                    field.onChange(tipo);
                    // a chave já digitada é remascarada no formato do novo tipo
                    setValue('payment_key', mascararChavePix(tipo)(getValues('payment_key') ?? ''));
                  }}
                  error={errors.payment_key_type?.message}
                />
              )}
            />
            <CampoMascarado
              control={control}
              name="payment_key"
              label="Chave"
              placeholder={placeholderDaChavePix(tipoDaChave)}
              mascarar={mascararChavePix(tipoDaChave)}
              inputMode={tipoDaChave === 'EMAIL' || tipoDaChave === 'ALEATORIA' ? 'text' : 'numeric'}
              error={errors.payment_key?.message}
            />
          </Group>

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={onFechar}>
              Cancelar
            </Button>
            <Button type="submit" loading={criar.isPending}>
              Cadastrar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
