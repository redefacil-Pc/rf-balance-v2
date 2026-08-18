import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Divider,
  FileButton,
  Group,
  List,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconCalculator, IconCash, IconDownload, IconTrash, IconUpload } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { ReceiptCreateModal } from '@/features/proposals/components/ReceiptCreateModal';
import { CommissionExplanationModal } from '@/features/receipts/components/CommissionExplanationModal';
import { useDecideProposal } from '@/features/proposals/mutations/useDecideProposal';
import { useRemoveAttachment } from '@/features/proposals/mutations/useRemoveAttachment';
import { useSubmitProposal } from '@/features/proposals/mutations/useSubmitProposal';
import { useUploadAttachment } from '@/features/proposals/mutations/useUploadAttachment';
import { useProposalAttachments } from '@/features/proposals/queries/useProposalAttachments';
import { useProposal } from '@/features/proposals/queries/useProposal';
import { useProposalReceipts } from '@/features/proposals/queries/useProposalReceipts';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { formatarMoeda } from '@/shared/formatters/currency';
import {
  COR_DA_APROVACAO,
  ROTULO_DA_APROVACAO,
  type Proposal,
} from '@/shared/types/commercial';

interface Props {
  proposta: Proposal | null;
  onFechar: () => void;
}

const TIPOS_ACEITOS = 'application/pdf,image/jpeg,image/png';

function formatarTamanho(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${(bytes / 1024).toFixed(0)} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
export function ProposalApprovalModal({ proposta, onFechar }: Props) {
  const { pode } = useAuth();
  const podeEscrever = pode('proposals:write');
  const podeAprovar = pode('proposals:approve');
  const podeDeclararRecebimento = pode('receipts:write');

  const [devolvendo, setDevolvendo] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [recebimentoAberto, recebimento] = useDisclosure(false);
  const [calculo, setCalculo] = useState<
    { receiptId: number | null; proposalId: number | null } | null
  >(null);

  const anexos = useProposalAttachments(proposta?.id ?? null);
  const detalhe = useProposal(proposta?.id ?? null);
  const recebimentos = useProposalReceipts(proposta?.id ?? null);
  const enviar = useSubmitProposal();
  const decidir = useDecideProposal();
  const anexar = useUploadAttachment();
  const remover = useRemoveAttachment();

  const fechar = () => {
    setDevolvendo(false);
    setMotivo('');
    onFechar();
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
  const temConteudoParaEnviar = (anexos.data ?? []).length > 0 || declarados.length > 0;
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
      { id: proposta.id, version: proposta.version, decision: 'APROVAR' },
      {
        onSuccess: () => {
          notifications.show({
            color: 'positivo',
            title: 'Proposta aprovada',
            message: `A proposta de ${proposta.customer_name} passa a valer para recebimento e comissão.`,
          });
          fechar();
        },
      },
    );
  };

  const devolver = () => {
    if (motivo.trim().length < 3) {
      return;
    }
    decidir.mutate(
      { id: proposta.id, version: proposta.version, decision: 'DEVOLVER', reason: motivo.trim() },
      {
        onSuccess: () => {
          notifications.show({
            color: 'yellow',
            title: 'Proposta devolvida',
            message: 'Quem cadastrou pode corrigir e reenviar.',
          });
          fechar();
        },
      },
    );
  };

  const enviarArquivo = (arquivo: File | null) => {
    if (!arquivo) {
      return;
    }
    anexar.mutate({ proposalId: proposta.id, file: arquivo });
  };

  const erro = enviar.error ?? decidir.error ?? anexar.error ?? remover.error ?? null;

  return (
    <Modal
      opened={proposta !== null}
      onClose={fechar}
      title={`Aprovação — proposta de ${proposta.customer_name}`}
      size="lg"
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

        <Divider label="Documentos da operação" labelPosition="left" />

        <EstadoDaLista
          carregando={anexos.isPending}
          erro={anexos.error ?? null}
          vazio={(anexos.data ?? []).length === 0}
          mensagemVazio="Nenhum documento anexado."
        >
          <List spacing="xs" size="sm">
            {(anexos.data ?? []).map((anexo) => (
              <List.Item key={anexo.id}>
                <Group justify="space-between" wrap="nowrap">
                  <Text size="sm" truncate>
                    {anexo.file_name}{' '}
                    <Text span size="xs" c="dimmed">
                      ({formatarTamanho(anexo.size_bytes)})
                    </Text>
                  </Text>
                  <Group gap={4} wrap="nowrap">
                    <ActionIcon
                      component="a"
                      href={`/api/v1/proposals/${proposta.id}/attachments/${anexo.id}`}
                      target="_blank"
                      rel="noreferrer"
                      variant="subtle"
                      aria-label={`Baixar ${anexo.file_name}`}
                    >
                      <IconDownload size={16} />
                    </ActionIcon>
                    {editavel && podeEscrever && (
                      <ActionIcon
                        variant="subtle"
                        color="red"
                        aria-label={`Remover ${anexo.file_name}`}
                        loading={remover.isPending}
                        onClick={() =>
                          remover.mutate({ proposalId: proposta.id, attachmentId: anexo.id })
                        }
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    )}
                  </Group>
                </Group>
              </List.Item>
            ))}
          </List>
        </EstadoDaLista>

        {editavel && podeEscrever && (
          <FileButton onChange={enviarArquivo} accept={TIPOS_ACEITOS}>
            {(props) => (
              <Button
                {...props}
                variant="default"
                leftSection={<IconUpload size={16} />}
                loading={anexar.isPending}
              >
                Anexar documento
              </Button>
            )}
          </FileButton>
        )}

        <Divider label="Valores recebidos" labelPosition="left" />

        <EstadoDaLista
          carregando={recebimentos.isPending}
          erro={recebimentos.error ?? null}
          vazio={(recebimentos.data?.items.length ?? 0) === 0}
          mensagemVazio="Nenhum recebimento declarado."
        >
          <Table verticalSpacing="xs">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Data</Table.Th>
                <Table.Th>Forma</Table.Th>
                <Table.Th ta="right">Valor</Table.Th>
                <Table.Th>Comprovante / cálculo</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(recebimentos.data?.items ?? []).map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>{item.business_date.split('-').reverse().join('/')}</Table.Td>
                  <Table.Td>{item.payment_method}</Table.Td>
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

        <Group justify="space-between">
          <Button variant="default" onClick={fechar}>
            Fechar
          </Button>

          <Group gap="sm">
            {editavel && podeEscrever && (
              <Button
                onClick={enviarAoFinanceiro}
                loading={enviar.isPending}
                disabled={!temConteudoParaEnviar}
                title={!temConteudoParaEnviar ? 'Declare um valor recebido ou anexe um documento para enviar' : undefined}
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
                <Button color="positivo" onClick={aprovar} loading={decidir.isPending}>
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
    </Modal>
  );
}
