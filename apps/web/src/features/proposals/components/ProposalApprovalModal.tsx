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
  Text,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconDownload, IconTrash, IconUpload } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useDecideProposal } from '@/features/proposals/mutations/useDecideProposal';
import { useRemoveAttachment } from '@/features/proposals/mutations/useRemoveAttachment';
import { useSubmitProposal } from '@/features/proposals/mutations/useSubmitProposal';
import { useUploadAttachment } from '@/features/proposals/mutations/useUploadAttachment';
import { useProposalAttachments } from '@/features/proposals/queries/useProposalAttachments';
import { useProposal } from '@/features/proposals/queries/useProposal';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
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

/**
 * Fluxo cadastro → financeiro (situação de aprovação, separada do status
 * financeiro). Quem cadastrou anexa comprovante e envia; o financeiro aprova
 * ou devolve com motivo.
 */
export function ProposalApprovalModal({ proposta, onFechar }: Props) {
  const { pode } = useAuth();
  const podeEscrever = pode('proposals:write');
  const podeAprovar = pode('proposals:approve');

  const [devolvendo, setDevolvendo] = useState(false);
  const [motivo, setMotivo] = useState('');

  const anexos = useProposalAttachments(proposta?.id ?? null);
  const detalhe = useProposal(proposta?.id ?? null);
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
  const temAnexos = (anexos.data ?? []).length > 0;

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

        <Divider label="Comprovantes de pagamento" labelPosition="left" />

        <EstadoDaLista
          carregando={anexos.isPending}
          erro={anexos.error ?? null}
          vazio={(anexos.data ?? []).length === 0}
          mensagemVazio="Nenhum comprovante anexado."
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
                Anexar comprovante
              </Button>
            )}
          </FileButton>
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
                disabled={!temAnexos}
                title={!temAnexos ? 'Anexe ao menos um comprovante para enviar' : undefined}
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
                  Aprovar
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
    </Modal>
  );
}
