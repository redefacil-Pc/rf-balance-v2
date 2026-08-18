import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDeviceFloppy, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import {
  useReceivingAccounts,
  useSaveReceivingAccount,
  useSetReceivingAccountStatus,
} from '@/features/receiving-accounts/queries/useReceivingAccounts';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';

export function ReceivingAccountsPage() {
  const { pode } = useAuth();
  const podeEscrever = pode('companies:write');
  const query = useReceivingAccounts();
  const salvar = useSaveReceivingAccount();
  const status = useSetReceivingAccountStatus();

  const [nova, setNova] = useState('');
  // edição in-place, como no v1: cada linha guarda o que foi digitado até salvar
  const [rascunhos, setRascunhos] = useState<Record<number, { label: string; ordem: number }>>({});

  const adicionar = async () => {
    const label = nova.trim();
    if (label.length < 3) return;
    await salvar.mutateAsync({ label });
    setNova('');
    notifications.show({ color: 'positivo', title: 'Conta cadastrada', message: label });
  };

  const salvarLinha = async (id: number, label: string, ordem: number) => {
    await salvar.mutateAsync({ id, label: label.trim(), display_order: ordem });
    setRascunhos((atual) => {
      const { [id]: _removido, ...resto } = atual;
      return resto;
    });
    notifications.show({ color: 'positivo', title: 'Conta atualizada', message: label.trim() });
  };

  return (
    <Stack gap="lg">
      <div>
        <Title order={2} size="h3">
          Contas de banco
        </Title>
        <Text size="sm" c="dimmed">
          Contas que recebem o dinheiro do cliente. São estas que aparecem para escolha ao declarar
          um recebimento na proposta.
        </Text>
      </div>

      {salvar.error && <Alert color="red">{salvar.error.problem.detail}</Alert>}
      {status.error && <Alert color="red">{status.error.problem.detail}</Alert>}

      {podeEscrever && (
        <Card withBorder>
          <Group align="flex-end">
            <TextInput
              style={{ flex: 1 }}
              label="Nova conta bancária"
              placeholder="Ex: Conta Fábio (BANCO DO BRASIL)"
              value={nova}
              onChange={(evento) => setNova(evento.currentTarget.value)}
              onKeyDown={(evento) => {
                if (evento.key === 'Enter') void adicionar();
              }}
            />
            <Button
              leftSection={<IconPlus size={16} />}
              disabled={nova.trim().length < 3}
              loading={salvar.isPending}
              onClick={() => void adicionar()}
            >
              Adicionar
            </Button>
          </Group>
        </Card>
      )}

      <Card withBorder padding={0}>
        <EstadoDaLista
          carregando={query.isPending}
          erro={query.error ?? null}
          vazio={(query.data?.length ?? 0) === 0}
          mensagemVazio="Nenhuma conta cadastrada."
        >
          <Table striped verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Conta</Table.Th>
                <Table.Th w={120}>Ordem</Table.Th>
                <Table.Th w={110}>Situação</Table.Th>
                <Table.Th w={220}>Ações</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {query.data?.map((item) => {
                const rascunho = rascunhos[item.id];
                const label = rascunho?.label ?? item.label;
                const ordem = rascunho?.ordem ?? item.display_order;
                const alterada = label !== item.label || ordem !== item.display_order;
                const editar = (campos: { label?: string; ordem?: number }) =>
                  setRascunhos((atual) => ({
                    ...atual,
                    [item.id]: { label, ordem, ...campos },
                  }));
                return (
                  <Table.Tr key={item.id}>
                    <Table.Td>
                      <TextInput
                        value={label}
                        disabled={!podeEscrever}
                        onChange={(evento) => editar({ label: evento.currentTarget.value })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <NumberInput
                        value={ordem}
                        min={0}
                        max={9999}
                        disabled={!podeEscrever}
                        onChange={(valor) => editar({ ordem: Number(valor) || 0 })}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Badge color={item.is_active ? 'positivo' : 'gray'}>
                        {item.is_active ? 'Ativa' : 'Inativa'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {podeEscrever && (
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="default"
                            loading={status.isPending}
                            onClick={() =>
                              status.mutate({ id: item.id, is_active: !item.is_active })
                            }
                          >
                            {item.is_active ? 'Desativar' : 'Reativar'}
                          </Button>
                          <Button
                            size="xs"
                            leftSection={<IconDeviceFloppy size={14} />}
                            disabled={!alterada || label.trim().length < 3}
                            loading={salvar.isPending}
                            onClick={() => void salvarLinha(item.id, label, ordem)}
                          >
                            Salvar
                          </Button>
                        </Group>
                      )}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </EstadoDaLista>
      </Card>

      <Text size="xs" c="dimmed">
        Desativar tira a conta da escolha de novos recebimentos, mas preserva os lançamentos que já
        apontam para ela — o histórico continua dizendo onde o dinheiro caiu.
      </Text>
    </Stack>
  );
}
