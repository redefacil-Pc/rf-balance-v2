import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Grid, Group, Modal, Select, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';

import { useUpdateProposal } from '@/features/proposals/mutations/useUpdateProposal';
import { useColaboradoresPorPapel } from '@/features/proposals/queries/useColaboradoresPorPapel';
import {
  updateProposalSchema,
  type UpdateProposalForm,
  type UpdateProposalFormEntrada,
} from '@/features/proposals/schemas/proposal-schema';
import { CampoMascarado } from '@/shared/components/CampoMascarado';
import { formatarMoeda } from '@/shared/formatters/currency';
import { decimalParaMoeda, mascararMoeda } from '@/shared/formatters/money-mask';
import { decimalParaPercentual, mascararPercentual } from '@/shared/formatters/percent-mask';
import type { Proposal } from '@/shared/types/commercial';

interface Props {
  proposta: Proposal | null;
  onFechar: () => void;
}

/**
 * Alteração de proposta. Só valor, TPS e participantes de apoio: o resto é
 * imutável por decisão de domínio (seção 7.4).
 *
 * A `version` lida ao abrir o modal vai junto na requisição. Se outra pessoa
 * alterou a proposta nesse meio tempo, o backend recusa com 409 e nada é
 * sobrescrito em silêncio.
 */
export function ProposalEditModal({ proposta, onFechar }: Props) {
  const alterar = useUpdateProposal();
  const bkos = useColaboradoresPorPapel('BKO');
  const finalizadores = useColaboradoresPorPapel('FINALIZACAO');

  const {
    control,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<UpdateProposalFormEntrada, unknown, UpdateProposalForm>({
    resolver: zodResolver(updateProposalSchema),
    defaultValues: {
      operation_amount: '',
      tps_percentage: '',
      bko_collaborator_id: null,
      finalizer_collaborator_id: null,
    },
  });

  useEffect(() => {
    if (proposta) {
      reset({
        // a API devolve decimal; o formulário trabalha mascarado
        operation_amount: decimalParaMoeda(proposta.operation_amount),
        tps_percentage: decimalParaPercentual(proposta.tps_percentage),
        bko_collaborator_id: proposta.bko_collaborator_id,
        finalizer_collaborator_id: proposta.finalizer_collaborator_id,
      });
    }
  }, [proposta, reset]);

  const enviar = handleSubmit((form) => {
    if (!proposta) {
      return;
    }
    alterar.mutate(
      { id: proposta.id, version: proposta.version, form },
      {
        onSuccess: (resultado) => {
          notifications.show({
            color: 'positivo',
            title: 'Proposta alterada',
            message: `Comissão da empresa: ${formatarMoeda(resultado.company_commission_amount)}`,
          });
          onFechar();
        },
        onError: (erro) => {
          for (const [campo, mensagem] of Object.entries(erro.erroDeCampo)) {
            setError(campo as keyof UpdateProposalFormEntrada, { message: mensagem });
          }
        },
      },
    );
  });

  const opcoes = (dados: { items: { id: number; full_name: string }[] } | undefined) =>
    (dados?.items ?? []).map((colaborador) => ({
      value: String(colaborador.id),
      label: colaborador.full_name,
    }));

  return (
    <Modal
      opened={proposta !== null}
      onClose={onFechar}
      title={proposta ? `Alterar proposta de ${proposta.customer_name}` : 'Alterar proposta'}
      size="lg"
      centered
    >
      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {alterar.isError && Object.keys(alterar.error.erroDeCampo).length === 0 && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={alterar.error.problem.title}
              role="alert"
            >
              <Text size="sm">{alterar.error.problem.detail}</Text>
            </Alert>
          )}

          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <CampoMascarado
                control={control}
                name="operation_amount"
                label="Valor da operação"
                placeholder="0,00"
                mascarar={mascararMoeda}
                inputMode="decimal"
                leftSection={<Text size="sm">R$</Text>}
                withAsterisk
                error={errors.operation_amount?.message}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <CampoMascarado
                control={control}
                name="tps_percentage"
                label="TPS (%)"
                placeholder="12,5"
                mascarar={mascararPercentual}
                inputMode="decimal"
                withAsterisk
                error={errors.tps_percentage?.message}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="bko_collaborator_id"
                render={({ field }) => (
                  <Select
                    label="BKO"
                    placeholder="Opcional"
                    clearable
                    searchable
                    data={opcoes(bkos.data)}
                    value={field.value ? String(field.value) : null}
                    onChange={(v) => field.onChange(v ? Number(v) : null)}
                  />
                )}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Controller
                control={control}
                name="finalizer_collaborator_id"
                render={({ field }) => (
                  <Select
                    label="Finalização"
                    placeholder="Opcional"
                    clearable
                    searchable
                    data={opcoes(finalizadores.data)}
                    value={field.value ? String(field.value) : null}
                    onChange={(v) => field.onChange(v ? Number(v) : null)}
                  />
                )}
              />
            </Grid.Col>
          </Grid>

          <Text size="xs" c="dimmed">
            Cliente, consultor e data de negócio não são editáveis. Em período já fechado a
            alteração é recusada: a correção certa é compensatória.
          </Text>

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={onFechar}>
              Fechar
            </Button>
            <Button type="submit" loading={alterar.isPending}>
              Salvar alteração
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
