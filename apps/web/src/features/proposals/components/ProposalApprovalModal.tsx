import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  Timeline,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle,
  IconCalculator,
  IconCash,
  IconCheck,
  IconClock,
  IconDownload,
} from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { ReceiptCreateModal } from '@/features/proposals/components/ReceiptCreateModal';
import { CommissionExplanationModal } from '@/features/receipts/components/CommissionExplanationModal';
import {
  ReceiptProofPreviewButton,
  ReceiptProofPreviewModal,
} from '@/features/receipts/components/ReceiptProofPreviewModal';
import { useDecideProposal } from '@/features/proposals/mutations/useDecideProposal';
import { useSubmitProposal } from '@/features/proposals/mutations/useSubmitProposal';
import { useProposal } from '@/features/proposals/queries/useProposal';
import { useProposalReceipts } from '@/features/proposals/queries/useProposalReceipts';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import {
  COR_DA_APROVACAO,
  ROTULO_DA_APROVACAO,
  type Proposal,
} from '@/shared/types/commercial';
import type { Receipt } from '@/shared/types/receipts';

interface Props {
  proposta: Proposal | null;
  onFechar: () => void;
  onDecidida?: (proposalId: number) => void;
}

const ROTULO_DO_EVENTO: Record<string, string> = {
  'proposal.created': 'Proposta cadastrada',
  'proposal.updated': 'Dados atualizados',
  'proposal.submitted': 'Enviada ao Financeiro',
  'proposal.approved': 'Proposta aprovada',
  'proposal.rejected': 'Devolvida para correção',
  'proposal.cancelled': 'Proposta cancelada',
  'proposal.attachment_added': 'Documento adicionado',
  'proposal.attachment_removed': 'Documento removido',
};

function formatarDataHora(valor: string | null): string {
  if (!valor) return 'Horário não informado';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(valor));
}

function formatarPercentual(valor: string): string {
  return `${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 6 })}%`;
}

function somarValores(valores: string[]): string {
  const centavos = valores.reduce((total, valor) => {
    const [inteiro = '0', decimal = ''] = valor.split('.');
    return total + BigInt(inteiro) * 100n + BigInt(decimal.padEnd(2, '0').slice(0, 2));
  }, 0n);
  return `${centavos / 100n}.${(centavos % 100n).toString().padStart(2, '0')}`;
}

/**
 * Fluxo cadastro → financeiro (situação de aprovação, separada do status
 * financeiro). Quem cadastrou declara os valores recebidos, cada um com o seu
 * comprovante, e envia; o financeiro confere no extrato e aprova ou devolve com
 * motivo.
 *
 * "Documentos da operação" é outra coisa: contrato e afins, sem valor
 * associado. O comprovante de pagamento mora no recebimento que ele comprova —
 * pedir o mesmo documento nos dois lugares foi o que fez a proposta chegar ao
 * financeiro com comprovante e saldo zero.
 */
export function ProposalApprovalModal({ proposta, onFechar, onDecidida }: Props) {
  const { pode, usuario } = useAuth();
  const podeEscrever = pode('proposals:write');
  const podeAprovar = pode('proposals:approve');
  const podeDeclararRecebimento =
    pode('receipts:write') && !(usuario?.roles.includes('ADMIN') ?? false);

  const [devolvendo, setDevolvendo] = useState(false);
  const [confirmandoAprovacao, setConfirmandoAprovacao] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [recebimentoAberto, recebimento] = useDisclosure(false);
  const [calculo, setCalculo] = useState<
    { receiptId: number | null; proposalId: number | null } | null
  >(null);
  const [comprovante, setComprovante] = useState<Receipt | null>(null);

  const detalhe = useProposal(proposta?.id ?? null);
  const recebimentos = useProposalReceipts(proposta?.id ?? null);
  const enviar = useSubmitProposal();
  const decidir = useDecideProposal();

  const fechar = () => {
    setDevolvendo(false);
    setConfirmandoAprovacao(false);
    setMotivo('');
    setComprovante(null);
    onFechar();
  };

  const concluirDecisao = (proposalId: number) => {
    setDevolvendo(false);
    setConfirmandoAprovacao(false);
    setMotivo('');
    setComprovante(null);
    if (onDecidida) onDecidida(proposalId);
    else onFechar();
  };

  if (!proposta) {
    return (
      <Modal opened={false} onClose={fechar} title="Aprovação da proposta">
        <div />
      </Modal>
    );
  }

  const editavel = proposta.approval_status === 'DRAFT' || proposta.approval_status === 'REJECTED';
  const podeReceber =
    editavel ||
    (proposta.approval_status === 'APPROVED' && proposta.status !== 'PAID' && proposta.status !== 'CANCELLED');
  const declarados = (recebimentos.data?.items ?? []).filter(
    (item) => item.status !== 'REJECTED' && item.net_amount !== '0.00',
  );
  // a regra "sem comprovante não envia" mora no domínio; aqui a tela apenas
  // antecipa o motivo, em vez de deixar o operador descobrir pelo 422
  const temValorDeclarado = declarados.length > 0;
  const totalDeclarado = somarValores(declarados.map((item) => item.net_amount));

  const enviarAoFinanceiro = () => {
    enviar.mutate(
      { id: proposta.id, version: proposta.version },
      {
        onSuccess: () => {
          notifications.show({
            color: 'positivo',
            title: 'Proposta enviada',
            message: 'Aguardando decisão do financeiro.',
          });
          fechar();
        },
      },
    );
  };

  const aprovar = () => {
    decidir.mutate(
      {
        id: proposta.id,
        version: detalhe.data?.version ?? proposta.version,
        decision: 'APROVAR',
      },
      {
        onSuccess: () => {
          notifications.show({
            color: 'positivo',
            title: 'Proposta aprovada',
            message: `A proposta de ${proposta.customer_name} passa a valer para recebimento e comissão.`,
          });
          concluirDecisao(proposta.id);
        },
      },
    );
  };

  const devolver = () => {
    if (motivo.trim().length < 3) {
      return;
    }
    decidir.mutate(
      {
        id: proposta.id,
        version: detalhe.data?.version ?? proposta.version,
        decision: 'DEVOLVER',
        reason: motivo.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: 'yellow',
            title: 'Proposta devolvida',
            message: 'Quem cadastrou pode corrigir e reenviar.',
          });
          concluirDecisao(proposta.id);
        },
      },
    );
  };

  const erro = enviar.error ?? decidir.error ?? null;

  return (
    <Modal
      opened={proposta !== null}
      onClose={fechar}
      title={`Aprovação — proposta de ${proposta.customer_name}`}
      size="xl"
      centered
    >
      <Stack gap="md">
        {erro && (
          <Alert
            variant="light"
            color="red"
            icon={<IconAlertTriangle size={18} />}
            title={erro.problem.title}
            role="alert"
          >
            <Text size="sm">{erro.problem.detail}</Text>
          </Alert>
        )}

        <Group gap="xs">
          <Text size="sm">Situação:</Text>
          <Badge variant="light" color={COR_DA_APROVACAO[proposta.approval_status]}>
            {ROTULO_DA_APROVACAO[proposta.approval_status]}
          </Badge>
        </Group>

        <Divider label="Dados para conferência" labelPosition="left" />

        {detalhe.error && (
          <Alert color="red" variant="light" title="Não foi possível carregar todos os dados">
            {detalhe.error.problem.detail}
          </Alert>
        )}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">Cliente</Text>
            <Text size="sm" fw={600}>{detalhe.data?.customer_name ?? proposta.customer_name}</Text>
            <Text size="xs" ff="monospace">
              {detalhe.data?.customer_document ?? proposta.customer_document}
            </Text>
          </Paper>
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">Consultor</Text>
            <Text size="sm" fw={600}>
              {detalhe.data?.consultant_name ?? proposta.consultant_name}
            </Text>
            <Text size="xs" c="dimmed">
              Finalização: {detalhe.data?.finalizer_collaborator_name ?? 'Não informada'}
            </Text>
            {detalhe.data?.bko_collaborator_name && (
              <Text size="xs" c="dimmed">BKO: {detalhe.data.bko_collaborator_name}</Text>
            )}
          </Paper>
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">Identificação</Text>
            <Text size="sm" fw={600}>
              Data: {proposta.business_date.split('-').reverse().join('/')}
            </Text>
            <Text size="xs" c="dimmed">ID externo: {proposta.external_id ?? 'Não informado'}</Text>
          </Paper>
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">Valor da operação</Text>
            <Text size="lg" fw={700}>{formatarMoeda(proposta.operation_amount)}</Text>
          </Paper>
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">TPS</Text>
            <Text size="lg" fw={700}>{formatarPercentual(proposta.tps_percentage)}</Text>
          </Paper>
          <Paper withBorder p="sm">
            <Text size="xs" c="dimmed">Comissão da empresa</Text>
            <Text size="lg" fw={700}>{formatarMoeda(proposta.company_commission_amount)}</Text>
          </Paper>
        </SimpleGrid>

        <Divider label="Valores recebidos" labelPosition="left" />

        <EstadoDaLista
          carregando={recebimentos.isPending}
          erro={recebimentos.error ?? null}
          vazio={(recebimentos.data?.items.length ?? 0) === 0}
          mensagemVazio="Nenhum recebimento declarado."
        >
          <Table.ScrollContainer minWidth={900}>
          <Table verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Data</Table.Th>
                <Table.Th>Forma</Table.Th>
                <Table.Th>Conta / referência</Table.Th>
                <Table.Th>Lançado por</Table.Th>
                <Table.Th ta="right">Valor</Table.Th>
                <Table.Th>Comprovante / cálculo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(recebimentos.data?.items ?? []).map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>{item.business_date.split('-').reverse().join('/')}</Table.Td>
                  <Table.Td>
                    <Text size="sm">{item.payment_method}</Text>
                    <Text size="xs" c="dimmed">{formatarDataHora(item.payment_datetime)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{item.receiving_account_label ?? 'Conta não informada'}</Text>
                    {item.reference && <Text size="xs" c="dimmed">{item.reference}</Text>}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{item.creator_name}</Text>
                    <Text size="xs" c="dimmed">{formatarDataHora(item.created_at)}</Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    <Stack gap={2} align="flex-end">
                      <Text size="sm">{formatarMoeda(item.net_amount)}</Text>
                      {item.reversed && (
                        <Text size="xs" c="dimmed">
                          {item.net_amount === '0.00' ? 'Estornado' : 'Estorno parcial'}
                        </Text>
                      )}
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <ReceiptProofPreviewButton onClick={() => setComprovante(item)} />
                      <ActionIcon
                        component="a"
                        href={`/api/v1/receipts/${item.id}/proof`}
                        target="_blank"
                        variant="subtle"
                        aria-label={`Baixar comprovante de ${formatarMoeda(item.amount)}`}
                      >
                        <IconDownload size={16} />
                      </ActionIcon>
                      {item.status === 'APPROVED' && pode('settlements:read') && (
                        <ActionIcon variant="subtle" aria-label="Ver cálculo da comissão"
                          onClick={() => setCalculo({ receiptId: item.id, proposalId: null })}>
                          <IconCalculator size={16} />
                        </ActionIcon>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          </Table.ScrollContainer>
          <Group justify="flex-end" mt="xs">
            {proposta.approval_status === 'APPROVED' && pode('settlements:read') && (
              <Button
                size="xs"
                variant="subtle"
                leftSection={<IconCalculator size={15} />}
                onClick={() => setCalculo({ receiptId: null, proposalId: proposta.id })}
              >
                Memória completa da proposta
              </Button>
            )}
            <Text size="sm" fw={600}>Total declarado: {formatarMoeda(totalDeclarado)}</Text>
          </Group>
        </EstadoDaLista>

        {(detalhe.data?.timeline.length ?? 0) > 0 && (
          <>
            <Divider label="Histórico da proposta" labelPosition="left" />
            <Timeline bulletSize={24} lineWidth={2} active={detalhe.data!.timeline.length}>
              {detalhe.data!.timeline.map((evento, indice) => (
                <Timeline.Item
                  key={`${evento.occurred_at}-${indice}`}
                  bullet={<IconClock size={13} />}
                  title={ROTULO_DO_EVENTO[evento.action] ?? evento.action}
                >
                  <Text size="xs" c="dimmed">
                    {formatarDataHora(evento.occurred_at)} · {evento.actor_name}
                  </Text>
                  {typeof evento.payload.reason === 'string' && (
                    <Text size="xs" mt={2}>Motivo: {evento.payload.reason}</Text>
                  )}
                </Timeline.Item>
              ))}
            </Timeline>
          </>
        )}

        {podeReceber && podeDeclararRecebimento && (
          <Button
            variant="default"
            leftSection={<IconCash size={16} />}
            onClick={recebimento.open}
          >
            Declarar recebimento
          </Button>
        )}

        {proposta.approval_status === 'REJECTED' && detalhe.data?.rejection_reason && (
          <Alert variant="light" color="red" title="Motivo da devolução">
            {detalhe.data.rejection_reason}
          </Alert>
        )}

        <Divider />

        {detalhe.data?.overpaid && (
          <Alert color="orange" title="Sobrepagamento para conferência">
            O valor recebido supera a comissão da empresa. Não há limite de negócio para o
            excedente, mas ele só passa a valer com a sua aprovação e não gera comissão acima de
            100% da base elegível.
          </Alert>
        )}

        <Group justify="space-between">
          <Button variant="default" onClick={fechar}>
            Fechar
          </Button>

          <Group gap="sm">
            {editavel && podeEscrever && (
              <Button
                onClick={enviarAoFinanceiro}
                loading={enviar.isPending}
                disabled={!temValorDeclarado}
                title={!temValorDeclarado ? 'Declare ao menos um valor recebido para enviar ao financeiro' : undefined}
              >
                Enviar para aprovação
              </Button>
            )}

            {proposta.approval_status === 'SUBMITTED' && podeAprovar && !devolvendo && (
              <>
                <Button
                  variant="outline"
                  color="red"
                  onClick={() => setDevolvendo(true)}
                >
                  Devolver
                </Button>
                <Button
                  color="positivo"
                  onClick={() => setConfirmandoAprovacao(true)}
                  loading={decidir.isPending}
                >
                  Aprovar e reconhecer valores
                </Button>
              </>
            )}
          </Group>
        </Group>

        {devolvendo && (
          <Stack gap="xs">
            <Textarea
              label="Motivo da devolução"
              placeholder="Ex.: comprovante ilegível"
              withAsterisk
              autosize
              minRows={2}
              value={motivo}
              onChange={(evento) => setMotivo(evento.currentTarget.value)}
              error={motivo.length > 0 && motivo.trim().length < 3 ? 'Motivo muito curto' : null}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setDevolvendo(false)}>
                Cancelar
              </Button>
              <Button
                color="red"
                onClick={devolver}
                loading={decidir.isPending}
                disabled={motivo.trim().length < 3}
              >
                Confirmar devolução
              </Button>
            </Group>
          </Stack>
        )}
      </Stack>
      <ReceiptCreateModal
        opened={recebimentoAberto}
        proposalId={proposta.id}
        onClose={recebimento.close}
      />
      <CommissionExplanationModal
        receiptId={calculo?.receiptId ?? null}
        proposalId={calculo?.proposalId ?? null}
        onClose={() => setCalculo(null)}
      />
      <ReceiptProofPreviewModal receipt={comprovante} onClose={() => setComprovante(null)} />
      <Modal
        opened={confirmandoAprovacao}
        onClose={() => setConfirmandoAprovacao(false)}
        title="Confirmar aprovação"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Confirma a aprovação da proposta de <strong>{proposta.customer_name}</strong> no valor
            de <strong>{formatarMoeda(proposta.operation_amount)}</strong>? Os recebimentos serão
            reconhecidos e as comissões serão calculadas.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirmandoAprovacao(false)}>
              Voltar para análise
            </Button>
            <Button
              color="positivo"
              leftSection={<IconCheck size={16} />}
              onClick={aprovar}
              loading={decidir.isPending}
            >
              Confirmar aprovação
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Modal>
  );
}
