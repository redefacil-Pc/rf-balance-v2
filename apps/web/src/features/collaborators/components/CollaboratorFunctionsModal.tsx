import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import {
  useAddFunction,
  useCloseFunction,
} from '@/features/collaborators/mutations/useManageFunctions';
import { useUpdateCollaborator } from '@/features/collaborators/mutations/useUpdateCollaborator';
import { useCollaboratorDetail } from '@/features/collaborators/queries/useCollaboratorDetail';
import { useCollaboratorFunctions } from '@/features/collaborators/queries/useCollaboratorFunctions';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { dataLocalHoje } from '@/shared/formatters/local-date';
import {
  PAPEIS,
  rotuloDoPapel,
  type Collaborator,
  type Papel,
  type TaxRegime,
} from '@/shared/types/organization';

interface Props {
  colaborador: Collaborator | null;
  podeEscrever: boolean;
  onFechar: () => void;
}

function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

function hoje(): string {
  return dataLocalHoje();
}

/**
 * Funções operacionais do colaborador, com vigência (ADR-0013).
 *
 * Trocar de função é encerrar uma e abrir outra — a tela reflete isso: não há
 * "editar função". Sobrescrever faria uma proposta antiga parecer comissionada
 * pela função de hoje.
 */
export function CollaboratorFunctionsModal({ colaborador, podeEscrever, onFechar }: Props) {
  const [funcao, setFuncao] = useState<Papel | null>(null);
  const [inicio, setInicio] = useState(hoje);
  const [encerrando, setEncerrando] = useState<number | null>(null);
  const [fim, setFim] = useState(hoje);
  const [motivoTroca, setMotivoTroca] = useState('');

  const consulta = useCollaboratorFunctions(colaborador?.id ?? null);
  const detalhe = useCollaboratorDetail(colaborador?.id ?? null);
  const abrir = useAddFunction();
  const encerrar = useCloseFunction();
  const atualizar = useUpdateCollaborator();

  const fechar = () => {
    setFuncao(null);
    setEncerrando(null);
    setMotivoTroca('');
    onFechar();
  };

  const funcoes = consulta.data ?? [];
  const modalidadeVigente = funcoes.find(
    (item) => item.current && (item.role === 'CONSULTOR' || item.role === 'CONSULTOR_MEI_ESCALONADO'),
  )?.role;
  const modalidadeSelecionada = funcao === 'CONSULTOR' || funcao === 'CONSULTOR_MEI_ESCALONADO'
    ? funcao
    : null;
  const trocandoModalidade = Boolean(
    modalidadeVigente && modalidadeSelecionada && modalidadeSelecionada !== modalidadeVigente,
  );

  const confirmarAbertura = () => {
    if (!colaborador || !funcao) {
      return;
    }
    if (trocandoModalidade) {
      if (!detalhe.data || !modalidadeSelecionada || motivoTroca.trim().length < 3) return;
      atualizar.mutate(
        {
          id: colaborador.id,
          company_id: colaborador.company_id,
          unit_id: colaborador.unit_id,
          full_name: colaborador.full_name,
          tax_regime: colaborador.tax_regime as TaxRegime,
          email: detalhe.data.email,
          phone: detalhe.data.phone,
          consultant_modality: modalidadeSelecionada,
          modality_valid_from: inicio,
          modality_reason: motivoTroca.trim(),
        },
        {
          onSuccess: () => {
            notifications.show({
              color: 'positivo',
              title: 'Regra de comissão alterada',
              message: `${rotuloDoPapel(funcao)} vigente desde ${formatarData(inicio)}.`,
            });
            setFuncao(null);
            setMotivoTroca('');
          },
        },
      );
      return;
    }
    abrir.mutate(
      { collaboratorId: colaborador.id, function: funcao, valid_from: inicio },
      {
        onSuccess: () => {
          notifications.show({
            color: 'positivo',
            title: 'Função aberta',
            message: `${rotuloDoPapel(funcao)} vigente desde ${formatarData(inicio)}.`,
          });
          setFuncao(null);
        },
      },
    );
  };

  const confirmarEncerramento = () => {
    if (!colaborador || encerrando === null) {
      return;
    }
    encerrar.mutate(
      { collaboratorId: colaborador.id, functionId: encerrando, valid_to: fim },
      {
        onSuccess: () => {
          notifications.show({
            color: 'yellow',
            title: 'Função encerrada',
            message: 'O histórico foi preservado para o cálculo de comissão.',
          });
          setEncerrando(null);
        },
      },
    );
  };

  const erro = abrir.error ?? encerrar.error ?? atualizar.error ?? detalhe.error ?? null;
  const papeisDisponiveis = PAPEIS.filter((papel) => papel !== modalidadeVigente);

  return (
    <Modal
      opened={colaborador !== null}
      onClose={fechar}
      title={colaborador ? `Funções de ${colaborador.full_name}` : 'Funções'}
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

        <EstadoDaLista
          carregando={consulta.isPending}
          erro={consulta.error ?? null}
          vazio={funcoes.length === 0}
          mensagemVazio="Nenhuma função registrada."
        >
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th scope="col">Função</Table.Th>
                <Table.Th scope="col">Vigência</Table.Th>
                <Table.Th scope="col">Situação</Table.Th>
                {podeEscrever && <Table.Th scope="col">Ações</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {funcoes.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {rotuloDoPapel(item.role)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {formatarData(item.valid_from)}
                      {item.valid_to ? ` a ${formatarData(item.valid_to)}` : ' — sem fim previsto'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="sm" variant="light" color={item.current ? 'positivo' : 'gray'}>
                      {item.current ? 'Vigente' : 'Encerrada'}
                    </Badge>
                  </Table.Td>
                  {podeEscrever && (
                    <Table.Td>
                      {item.current && (
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          color="red"
                          onClick={() => setEncerrando(item.id)}
                        >
                          Encerrar
                        </Button>
                      )}
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </EstadoDaLista>

        {encerrando !== null && (
          <>
            <Divider label="Encerrar função" labelPosition="left" />
            <Group align="flex-end">
              <TextInput
                label="Encerrar em"
                type="date"
                value={fim}
                onChange={(evento) => setFim(evento.currentTarget.value)}
                w={180}
              />
              <Button variant="default" onClick={() => setEncerrando(null)}>
                Cancelar
              </Button>
              <Button color="red" onClick={confirmarEncerramento} loading={encerrar.isPending}>
                Confirmar
              </Button>
            </Group>
            <Text size="xs" c="dimmed">
              A função sai de vigência mas continua no histórico — é ela que responde qual era a
              função na data de uma proposta antiga.
            </Text>
          </>
        )}

        {podeEscrever && (
          <>
            <Divider label="Abrir função" labelPosition="left" />
            <Group align="flex-end">
              <Select
                label="Função"
                placeholder="Selecione"
                w={220}
                data={papeisDisponiveis.map((papel) => ({ value: papel, label: rotuloDoPapel(papel) }))}
                value={funcao}
                onChange={(valor) => setFuncao(valor as Papel | null)}
                disabled={consulta.isPending}
              />
              <TextInput
                label="A partir de"
                type="date"
                min={hoje()}
                value={inicio}
                onChange={(evento) => setInicio(evento.currentTarget.value)}
                w={180}
              />
              <Button
                leftSection={<IconPlus size={16} />}
                onClick={confirmarAbertura}
                loading={abrir.isPending || atualizar.isPending}
                disabled={!funcao || (trocandoModalidade && (!detalhe.data || motivoTroca.trim().length < 3))}
              >
                {trocandoModalidade ? 'Trocar' : 'Abrir'}
              </Button>
            </Group>
            {trocandoModalidade && <TextInput
              label="Motivo da troca"
              withAsterisk
              value={motivoTroca}
              onChange={(evento) => setMotivoTroca(evento.currentTarget.value)}
            />}
            <Text size="xs" c="dimmed">
              {trocandoModalidade
                ? 'A modalidade atual será encerrada no dia anterior. A conta, os vínculos e o histórico serão preservados.'
                : 'Acumular funções diferentes é permitido. A mesma função não pode se sobrepor a si mesma.'}
            </Text>
          </>
        )}

        <Group justify="flex-end">
          <Button variant="default" onClick={fechar}>
            Fechar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
