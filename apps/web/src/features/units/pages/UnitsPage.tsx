import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import { useCreateCompany, useCreateUnit } from '@/features/units/mutations/useCreateCompany';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { mascararCnpj } from '@/shared/formatters/document-mask';

export function UnitsPage() {
  const { pode } = useAuth();
  const podeEscrever = pode('companies:write');

  const empresas = useCompanies();
  const [empresaSelecionada, setEmpresaSelecionada] = useState<number | undefined>();
  const unidades = useUnits(empresaSelecionada);

  const criarEmpresa = useCreateCompany();
  const criarUnidade = useCreateUnit();

  const [novaEmpresa, setNovaEmpresa] = useState({ legal_name: '', trade_name: '', document: '' });
  const [novaUnidade, setNovaUnidade] = useState({ code: '', name: '' });

  return (
    <Stack gap="lg">
      <div>
        <Title order={2} size="h3">
          Empresas e unidades
        </Title>
        <Text c="dimmed" size="sm">
          A unidade é a fronteira de escopo mais usada pelas permissões: quem enxerga uma unidade não
          enxerga automaticamente as outras.
        </Text>
      </div>

      <Grid>
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <Card withBorder radius="md" padding="lg" h="100%">
            <Title order={3} size="h5" mb="md">
              Empresas
            </Title>

            <EstadoDaLista
              carregando={empresas.isPending}
              erro={empresas.error ?? null}
              vazio={(empresas.data ?? []).length === 0}
              onTentarNovamente={() => void empresas.refetch()}
              mensagemVazio="Nenhuma empresa cadastrada ainda."
            >
              <Table striped verticalSpacing="xs" mb="md">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th scope="col">Razão social</Table.Th>
                    <Table.Th scope="col">Nome fantasia</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(empresas.data ?? []).map((empresa) => (
                    <Table.Tr key={empresa.id}>
                      <Table.Td>{empresa.legal_name}</Table.Td>
                      <Table.Td>
                        <Text size="sm" c="dimmed">
                          {empresa.trade_name || '—'}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </EstadoDaLista>

            {podeEscrever && (
              <Stack gap="xs">
                {criarEmpresa.isError && (
                  <Alert
                    variant="light"
                    color="red"
                    icon={<IconAlertTriangle size={16} />}
                    role="alert"
                  >
                    <Text size="sm">{criarEmpresa.error.problem.detail}</Text>
                  </Alert>
                )}
                <TextInput
                  label="Razão social"
                  value={novaEmpresa.legal_name}
                  onChange={(e) =>
                    setNovaEmpresa({ ...novaEmpresa, legal_name: e.currentTarget.value })
                  }
                />
                <Group grow>
                  <TextInput
                    label="Nome fantasia"
                    value={novaEmpresa.trade_name}
                    onChange={(e) =>
                      setNovaEmpresa({ ...novaEmpresa, trade_name: e.currentTarget.value })
                    }
                  />
                  <TextInput
                    label="CNPJ"
                    placeholder="00.000.000/0000-00"
                    inputMode="numeric"
                    value={novaEmpresa.document}
                    onChange={(e) =>
                      setNovaEmpresa({
                        ...novaEmpresa,
                        document: mascararCnpj(e.currentTarget.value),
                      })
                    }
                  />
                </Group>
                <Button
                  mt="xs"
                  loading={criarEmpresa.isPending}
                  disabled={novaEmpresa.legal_name.trim().length < 2}
                  onClick={() =>
                    criarEmpresa.mutate(novaEmpresa, {
                      onSuccess: (empresa) => {
                        notifications.show({
                          color: 'positivo',
                          title: 'Empresa cadastrada',
                          message: empresa.legal_name,
                        });
                        setNovaEmpresa({ legal_name: '', trade_name: '', document: '' });
                      },
                    })
                  }
                >
                  Cadastrar empresa
                </Button>
              </Stack>
            )}
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Card withBorder radius="md" padding="lg" h="100%">
            <Title order={3} size="h5" mb="md">
              Unidades
            </Title>

            <Select
              label="Empresa"
              placeholder="Todas"
              clearable
              mb="md"
              data={(empresas.data ?? []).map((e) => ({
                value: String(e.id),
                label: e.legal_name,
              }))}
              value={empresaSelecionada ? String(empresaSelecionada) : null}
              onChange={(v) => setEmpresaSelecionada(v ? Number(v) : undefined)}
            />

            <EstadoDaLista
              carregando={unidades.isPending}
              erro={unidades.error ?? null}
              vazio={(unidades.data ?? []).length === 0}
              onTentarNovamente={() => void unidades.refetch()}
              mensagemVazio="Nenhuma unidade cadastrada para este filtro."
            >
              <Table striped verticalSpacing="xs" mb="md">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th scope="col">Código</Table.Th>
                    <Table.Th scope="col">Nome</Table.Th>
                    <Table.Th scope="col">Situação</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(unidades.data ?? []).map((unidade) => (
                    <Table.Tr key={unidade.id}>
                      <Table.Td>
                        <Text size="sm" ff="monospace">
                          {unidade.code}
                        </Text>
                      </Table.Td>
                      <Table.Td>{unidade.name}</Table.Td>
                      <Table.Td>
                        <Badge
                          size="sm"
                          variant="light"
                          color={unidade.is_active ? 'positivo' : 'gray'}
                        >
                          {unidade.is_active ? 'Ativa' : 'Inativa'}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </EstadoDaLista>

            {podeEscrever && (
              <Stack gap="xs">
                {criarUnidade.isError && (
                  <Alert
                    variant="light"
                    color="red"
                    icon={<IconAlertTriangle size={16} />}
                    role="alert"
                  >
                    <Text size="sm">{criarUnidade.error.problem.detail}</Text>
                  </Alert>
                )}
                <Group grow align="flex-end">
                  <TextInput
                    label="Código"
                    placeholder="MATRIZ"
                    value={novaUnidade.code}
                    onChange={(e) =>
                      setNovaUnidade({ ...novaUnidade, code: e.currentTarget.value })
                    }
                  />
                  <TextInput
                    label="Nome"
                    value={novaUnidade.name}
                    onChange={(e) =>
                      setNovaUnidade({ ...novaUnidade, name: e.currentTarget.value })
                    }
                  />
                </Group>
                <Button
                  mt="xs"
                  loading={criarUnidade.isPending}
                  disabled={
                    !empresaSelecionada ||
                    novaUnidade.code.trim() === '' ||
                    novaUnidade.name.trim().length < 2
                  }
                  onClick={() =>
                    criarUnidade.mutate(
                      { company_id: empresaSelecionada!, ...novaUnidade },
                      {
                        onSuccess: (unidade) => {
                          notifications.show({
                            color: 'positivo',
                            title: 'Unidade cadastrada',
                            message: `${unidade.code} — ${unidade.name}`,
                          });
                          setNovaUnidade({ code: '', name: '' });
                        },
                      },
                    )
                  }
                >
                  {empresaSelecionada
                    ? 'Cadastrar unidade'
                    : 'Selecione a empresa para cadastrar'}
                </Button>
              </Stack>
            )}
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
