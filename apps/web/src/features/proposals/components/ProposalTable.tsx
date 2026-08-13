import { ActionIcon, Badge, Group, Table, Text, Tooltip } from '@mantine/core';
import { IconBan, IconClipboardCheck, IconPencil } from '@tabler/icons-react';

import { formatarMoeda } from '@/shared/formatters/currency';
import {
  COR_DA_APROVACAO,
  COR_DO_STATUS,
  ROTULO_DA_APROVACAO,
  ROTULO_DO_STATUS,
  type Proposal,
} from '@/shared/types/commercial';

interface Props {
  propostas: Proposal[];
  podeEscrever: boolean;
  podeVerPii: boolean;
  podeAprovar: boolean;
  onEditar: (proposta: Proposal) => void;
  onCancelar: (proposta: Proposal) => void;
  onAprovacao: (proposta: Proposal) => void;
}

function formatarData(iso: string): string {
  // a data de negócio já vem como YYYY-MM-DD; `new Date` aplicaria fuso e
  // poderia exibir o dia anterior
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

export function ProposalTable({
  propostas,
  podeEscrever,
  podeVerPii,
  podeAprovar,
  onEditar,
  onCancelar,
  onAprovacao,
}: Props) {
  const temAcoes = podeEscrever || podeAprovar;

  return (
    <Table.ScrollContainer minWidth={980}>
      <Table striped highlightOnHover verticalSpacing="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th scope="col">Data</Table.Th>
            <Table.Th scope="col">Cliente</Table.Th>
            <Table.Th scope="col">{podeVerPii ? 'Documento' : 'Documento (parcial)'}</Table.Th>
            <Table.Th scope="col">Consultor</Table.Th>
            <Table.Th scope="col" ta="right">
              Operação
            </Table.Th>
            <Table.Th scope="col" ta="right">
              TPS
            </Table.Th>
            <Table.Th scope="col" ta="right">
              Comissão
            </Table.Th>
            <Table.Th scope="col" ta="right">
              Em aberto
            </Table.Th>
            <Table.Th scope="col">Situação</Table.Th>
            <Table.Th scope="col">Aprovação</Table.Th>
            {temAcoes && <Table.Th scope="col">Ações</Table.Th>}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {propostas.map((proposta) => (
            <Table.Tr key={proposta.id}>
              <Table.Td>
                <Text size="sm">{formatarData(proposta.business_date)}</Text>
                {proposta.external_id && (
                  <Text size="xs" c="dimmed">
                    {proposta.external_id}
                  </Text>
                )}
              </Table.Td>
              <Table.Td>
                <Text size="sm" fw={500}>
                  {proposta.customer_name}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" ff="monospace">
                  {proposta.customer_document}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{proposta.consultant_name}</Text>
              </Table.Td>
              <Table.Td ta="right">
                <Text size="sm">{formatarMoeda(proposta.operation_amount)}</Text>
              </Table.Td>
              <Table.Td ta="right">
                <Text size="sm">{Number(proposta.tps_percentage).toLocaleString('pt-BR')}%</Text>
              </Table.Td>
              <Table.Td ta="right">
                <Text size="sm" fw={500}>
                  {formatarMoeda(proposta.company_commission_amount)}
                </Text>
              </Table.Td>
              <Table.Td ta="right">
                <Text size="sm">{formatarMoeda(proposta.outstanding_amount)}</Text>
              </Table.Td>
              <Table.Td>
                <Badge size="sm" variant="light" color={COR_DO_STATUS[proposta.status]}>
                  {ROTULO_DO_STATUS[proposta.status]}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge size="sm" variant="light" color={COR_DA_APROVACAO[proposta.approval_status]}>
                  {ROTULO_DA_APROVACAO[proposta.approval_status]}
                </Badge>
              </Table.Td>
              {temAcoes && (
                <Table.Td>
                  <Group gap={4} wrap="nowrap">
                    <Tooltip label="Comprovantes e aprovação">
                      <ActionIcon
                        variant="subtle"
                        aria-label={`Aprovação da proposta de ${proposta.customer_name}`}
                        disabled={proposta.status === 'CANCELLED'}
                        onClick={() => onAprovacao(proposta)}
                      >
                        <IconClipboardCheck size={16} />
                      </ActionIcon>
                    </Tooltip>
                    {podeEscrever && (
                      <>
                        <Tooltip label="Alterar valor e TPS">
                          <ActionIcon
                            variant="subtle"
                            aria-label={`Alterar proposta de ${proposta.customer_name}`}
                            disabled={proposta.status === 'CANCELLED'}
                            onClick={() => onEditar(proposta)}
                          >
                            <IconPencil size={16} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Cancelar proposta">
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            aria-label={`Cancelar proposta de ${proposta.customer_name}`}
                            disabled={proposta.status === 'CANCELLED'}
                            onClick={() => onCancelar(proposta)}
                          >
                            <IconBan size={16} />
                          </ActionIcon>
                        </Tooltip>
                      </>
                    )}
                  </Group>
                </Table.Td>
              )}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
