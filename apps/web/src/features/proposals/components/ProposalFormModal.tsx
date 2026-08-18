import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, FileButton, Grid, Group, List, Modal, Select, Stack, Text, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconPaperclip, IconTrash, IconUpload } from '@tabler/icons-react';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';

import { useCreateProposal } from '@/features/proposals/mutations/useCreateProposal';
import { useUploadAttachment } from '@/features/proposals/mutations/useUploadAttachment';
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
  onFechar: () => void;
}

const HOJE = new Date().toISOString().slice(0, 10);

const VAZIO: ProposalFormEntrada = {
  consultant_id: undefined as unknown as number,
  business_date: HOJE,
  customer_name: '',
  customer_document: '',
  operation_amount: '',
  tps_percentage: '',
  external_id: '',
  bko_collaborator_id: null,
  finalizer_collaborator_id: null,
};

/** Cadastro de proposta. A alteração é outro fluxo: `ProposalEditModal`. */
export function ProposalFormModal({ aberto, onFechar }: Props) {
  const criar = useCreateProposal();
  const anexar = useUploadAttachment();
  const [arquivos, setArquivos] = useState<File[]>([]);
  const consultores = useColaboradoresPorPapel([
    'CONSULTOR',
    'CONSULTOR_MEI_ESCALONADO',
  ]);
  const pagamento = usePagamentoNoCadastro();
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
    defaultValues: VAZIO,
  });

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
      resultado = await criar.mutateAsync(form);
    } catch (erro) {
      if (erro instanceof ApiError) {
        for (const [campo, mensagem] of Object.entries(erro.erroDeCampo)) {
          setError(campo as keyof ProposalFormEntrada, { message: mensagem });
        }
      }
      return;
    }

    const limpar = () => {
      reset(VAZIO);
      setArquivos([]);
      pagamento.limpar();
      onFechar();
    };

    // A proposta já existe; o recebimento é uma segunda chamada. Se ela falhar,
    // a proposta não é desfeita — dizer isso e apontar onde completar é melhor
    // que um sucesso que esconde metade do trabalho.
    if (pagamento.preenchido) {
      try {
        await pagamento.declarar(resultado.id);
      } catch (erro) {
        notifications.show({
          color: 'yellow',
          title: 'Proposta criada, mas o pagamento não foi declarado',
          message:
            erro instanceof ApiError
              ? erro.problem.detail
              : 'Abra a proposta e declare o recebimento para concluir.',
          autoClose: false,
        });
        limpar();
        return;
      }
    }

    try {
      for (const arquivo of arquivos) {
        await anexar.mutateAsync({ proposalId: resultado.id, file: arquivo });
      }
    } catch {
      notifications.show({
        color: 'yellow',
        title: 'Proposta criada, mas faltou um documento',
        message: 'Abra a proposta para reenviar o anexo.',
      });
      limpar();
      return;
    }

    notifications.show({
      color: 'positivo',
      title: 'Proposta cadastrada',
      message: `Comissão da empresa: ${formatarMoeda(resultado.company_commission_amount)}`,
    });
    limpar();
  });

  const opcoes = (dados: { items: { id: number; full_name: string }[] } | undefined) =>
    (dados?.items ?? []).map((colaborador) => ({
      value: String(colaborador.id),
      label: colaborador.full_name,
    }));

  return (
    <Modal opened={aberto} onClose={onFechar} title="Nova proposta" size="lg" centered>
      <form onSubmit={enviar} noValidate>
        <Stack gap="md">
          {(criar.error ?? anexar.error) && (
            <Alert
              variant="light"
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title={(criar.error ?? anexar.error)?.problem.title}
              role="alert"
            >
              <Text size="sm">{(criar.error ?? anexar.error)?.problem.detail}</Text>
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

          <PagamentoNoCadastro pagamento={pagamento} />

          <Stack gap="xs">
            <Text size="sm" fw={500}>Documentos da operação</Text>
            <Text size="xs" c="dimmed">Opcional: contrato, proposta assinada e afins. O comprovante do pagamento vai no bloco acima.</Text>
            {arquivos.length > 0 && <List size="sm" icon={<IconPaperclip size={14} />}>{arquivos.map((arquivo, indice) => <List.Item key={`${arquivo.name}-${arquivo.size}`}><Group justify="space-between"><Text size="sm">{arquivo.name}</Text><Button variant="subtle" color="red" size="compact-xs" leftSection={<IconTrash size={13} />} onClick={() => setArquivos((atuais) => atuais.filter((_, i) => i !== indice))}>Remover</Button></Group></List.Item>)}</List>}
            <FileButton multiple accept="application/pdf,image/jpeg,image/png" onChange={(selecionados) => setArquivos((atuais) => [...atuais, ...selecionados].filter((arquivo) => arquivo.size <= 10 * 1024 * 1024))}>
              {(props) => <Button {...props} variant="default" leftSection={<IconUpload size={16} />} w="fit-content">Selecionar documentos</Button>}
            </FileButton>
          </Stack>

          <Text size="xs" c="dimmed">
            A comissão da empresa é calculada no servidor a partir do valor e do TPS. Esta tela não
            faz conta de dinheiro.
          </Text>

          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={onFechar}>
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={criar.isPending || anexar.isPending}
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
