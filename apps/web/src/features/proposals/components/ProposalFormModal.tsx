import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Grid, Group, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useCallback, useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';

import {
  useCreateProposal,
  useCreateProposalWithReceipt,
} from '@/features/proposals/mutations/useCreateProposal';
import { useColaboradoresPorPapel } from '@/features/proposals/queries/useColaboradoresPorPapel';
import {
  proposalSchema,
  type ProposalForm,
  type ProposalFormEntrada,
} from '@/features/proposals/schemas/proposal-schema';
import { PagamentoNoCadastro, usePagamentoNoCadastro } from '@/features/proposals/components/PagamentoNoCadastro';
import { PreviaDeComissao } from '@/features/proposals/components/PreviaDeComissao';
import { useCommissionPreview } from '@/features/proposals/queries/useCommissionPreview';
import { CampoMascarado } from '@/shared/components/CampoMascarado';
import { ApiError } from '@/shared/api/problem-details';
import { formatarMoeda } from '@/shared/formatters/currency';
import { mascararDocumento } from '@/shared/formatters/document-mask';
import { mascararMoeda, moedaParaDecimal } from '@/shared/formatters/money-mask';
import { mascararPercentual, percentualParaDecimal } from '@/shared/formatters/percent-mask';

interface Props {
  aberto: boolean;
  podeDeclararPagamento: boolean;
  onFechar: () => void;
}

function formularioVazio(): ProposalFormEntrada {
  return {
    consultant_id: undefined as unknown as number,
    business_date: new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' }),
    customer_name: '',
    customer_document: '',
    operation_amount: '',
    tps_percentage: '',
    external_id: '',
    bko_collaborator_id: null,
    finalizer_collaborator_id: null,
  };
}

/** Cadastro de proposta. A alteração é outro fluxo: `ProposalEditModal`. */
export function ProposalFormModal({ aberto, podeDeclararPagamento, onFechar }: Props) {
  const criar = useCreateProposal();
  const criarComPagamento = useCreateProposalWithReceipt();
  const consultores = useColaboradoresPorPapel([
    'CONSULTOR',
    'CONSULTOR_MEI_ESCALONADO',
  ]);
  const pagamento = usePagamentoNoCadastro(podeDeclararPagamento);
  const bkos = useColaboradoresPorPapel('BKO');
  const finalizadores = useColaboradoresPorPapel('FINALIZACAO');

  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors },
  } = useForm<ProposalFormEntrada, unknown, ProposalForm>({
    resolver: zodResolver(proposalSchema),
    defaultValues: formularioVazio(),
  });

  const limparPagamento = pagamento.limpar;
  const resetarCriacao = criar.reset;
  const resetarCriacaoComPagamento = criarComPagamento.reset;
  const limparFormulario = useCallback(() => {
    reset(formularioVazio());
    limparPagamento();
    resetarCriacao();
    resetarCriacaoComPagamento();
  }, [limparPagamento, reset, resetarCriacao, resetarCriacaoComPagamento]);

  const fechar = useCallback(() => {
    limparFormulario();
    onFechar();
  }, [limparFormulario, onFechar]);

  useEffect(() => {
    if (aberto) limparFormulario();
  }, [aberto, limparFormulario]);

  // a tela não calcula dinheiro: manda os mesmos valores que gravaria e o
  // servidor responde rodando o motor de comissão de verdade
  const previa = useCommissionPreview({
    consultant_id: watch('consultant_id'),
    business_date: watch('business_date'),
    operation_amount: moedaParaDecimal(watch('operation_amount') ?? ''),
    tps_percentage: percentualParaDecimal(watch('tps_percentage') ?? ''),
  });

  const enviar = handleSubmit(async (form) => {
    let resultado;
    try {
      resultado = pagamento.receipt
        ? await criarComPagamento.mutateAsync({ form, receipt: pagamento.receipt })
        : await criar.mutateAsync(form);
    } catch (erro) {
      if (erro instanceof ApiError) {
        for (const [campo, mensagem] of Object.entries(erro.erroDeCampo)) {
          setError(campo as keyof ProposalFormEntrada, { message: mensagem });
        }
      }
      return;
    }

    notifications.show({
      color: 'positivo',
      title: 'Proposta cadastrada',
      message: `Comissão da empresa: ${formatarMoeda(resultado.company_commission_amount)}`,
    });
    fechar();
  });

  const opcoes = (dados: { items: { id: number; full_name: string }[] } | undefined) =>
    (dados?.items ?? []).map((colaborador) => ({
      value: String(colaborador.id),
      label: colaborador.full_name,
    }));

  return (
    <Modal opened={aberto} onClose={fechar} title="Nova proposta" size="lg" centered>
      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {(criar.error ?? criarComPagamento.error) && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={(criar.error ?? criarComPagamento.error)?.problem.title}
              role="alert"
            >
              <Text size="sm">{(criar.error ?? criarComPagamento.error)?.problem.detail}</Text>
            </Alert>
          )}

          <Grid>
            <Grid.Col span={{ base: 12, sm: 7 }}>
              <Controller
                control={control}
                name="consultant_id"
                render={({ field }) => (
                  <Select
                    label="Consultor"
                    placeholder="Selecione"
                    withAsterisk
                    searchable
                    data={opcoes(consultores.data)}
                    value={field.value ? String(field.value) : null}
                    onChange={(v) => field.onChange(v ? Number(v) : undefined)}
                    error={errors.consultant_id?.message}
                  />
                )}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 5 }}>
              <TextInput
                label="Data de negócio"
                type="date"
                withAsterisk
                error={errors.business_date?.message}
                {...register('business_date')}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 7 }}>
              <TextInput
                label="Cliente"
                withAsterisk
                error={errors.customer_name?.message}
                {...register('customer_name')}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 5 }}>
              <CampoMascarado
                control={control}
                name="customer_document"
                label="CPF ou CNPJ do cliente"
                placeholder="000.000.000-00"
                mascarar={mascararDocumento}
                withAsterisk
                error={errors.customer_document?.message}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 4 }}>
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

            <Grid.Col span={{ base: 12, sm: 4 }}>
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

            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput
                label="Redmine"
                placeholder="RM-1234"
                error={errors.external_id?.message}
                {...register('external_id')}
              />
            </Grid.Col>

            <Grid.Col span={12}>
              <PreviaDeComissao previa={previa} />
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

          {podeDeclararPagamento && <PagamentoNoCadastro pagamento={pagamento} />}

          <Text size="xs" c="dimmed">
            A comissão da empresa é calculada no servidor a partir do valor e do TPS. Esta tela não
            faz conta de dinheiro.
          </Text>

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={fechar}>
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={criar.isPending || criarComPagamento.isPending}
              // bloco de pagamento pela metade não cadastra: ou completa, ou zera o valor
              disabled={pagamento.preenchido && !pagamento.completo}
            >
              Cadastrar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
