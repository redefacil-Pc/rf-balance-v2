import { ActionIcon, Badge, Button, Card, Grid, Group, Modal, Select, Stack, Table, Text, TextInput, Title, Tooltip } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPencil, IconPlayerPlay, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { useCompanies, useUnits } from '@/features/collaborators/queries/useOrganization';
import { useCreateCompany, useCreateUnit, useSetCompanyStatus, useSetUnitStatus, useUpdateCompany, useUpdateUnit } from '@/features/units/mutations/useCreateCompany';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { mascararCnpj } from '@/shared/formatters/document-mask';
import type { Company, Unit } from '@/shared/types/organization';

export function UnitsPage() {
  const { pode } = useAuth();
  const podeEscrever = pode('companies:write');
  const empresas = useCompanies(false);
  const [companyId, setCompanyId] = useState<number>();
  const unidades = useUnits(companyId, false);
  const criarEmpresa = useCreateCompany(); const criarUnidade = useCreateUnit();
  const atualizarEmpresa = useUpdateCompany(); const situacaoEmpresa = useSetCompanyStatus();
  const atualizarUnidade = useUpdateUnit(); const situacaoUnidade = useSetUnitStatus();
  const [novaEmpresa, setNovaEmpresa] = useState({ legal_name: '', trade_name: '', document: '' });
  const [novaUnidade, setNovaUnidade] = useState({ code: '', name: '' });
  const [empresaEditada, setEmpresaEditada] = useState<Company | null>(null);
  const [unidadeEditada, setUnidadeEditada] = useState<Unit | null>(null);

  return <Stack gap="lg">
    <div><Title order={2} size="h3">Empresas e unidades</Title><Text c="dimmed" size="sm">Cadastros organizacionais com edição e inativação sem perda do histórico.</Text></div>
    <Grid>
      <Grid.Col span={{ base: 12, lg: 5 }}><Card withBorder radius="md" padding="lg"><Title order={3} size="h5" mb="md">Empresas</Title>
        <EstadoDaLista carregando={empresas.isPending} erro={empresas.error ?? null} vazio={(empresas.data ?? []).length === 0} mensagemVazio="Nenhuma empresa cadastrada.">
          <Table striped verticalSpacing="xs" mb="md"><Table.Thead><Table.Tr><Table.Th>Razão social</Table.Th><Table.Th>Situação</Table.Th>{podeEscrever && <Table.Th>Ações</Table.Th>}</Table.Tr></Table.Thead><Table.Tbody>{(empresas.data ?? []).map((item) => <Table.Tr key={item.id}><Table.Td><Text size="sm" fw={500}>{item.legal_name}</Text><Text size="xs" c="dimmed">{item.trade_name || '—'}</Text></Table.Td><Table.Td><Badge color={item.is_active ? 'positivo' : 'gray'} variant="light">{item.is_active ? 'Ativa' : 'Inativa'}</Badge></Table.Td>{podeEscrever && <Table.Td><Group gap={4} wrap="nowrap"><Tooltip label="Editar"><ActionIcon variant="subtle" onClick={() => setEmpresaEditada(item)}><IconPencil size={16} /></ActionIcon></Tooltip><Tooltip label={item.is_active ? 'Inativar' : 'Reativar'}><ActionIcon variant="subtle" color={item.is_active ? 'red' : 'positivo'} onClick={() => situacaoEmpresa.mutate({ id: item.id, is_active: !item.is_active })}>{item.is_active ? <IconTrash size={16} /> : <IconPlayerPlay size={16} />}</ActionIcon></Tooltip></Group></Table.Td>}</Table.Tr>)}</Table.Tbody></Table>
        </EstadoDaLista>
        {podeEscrever && <Stack gap="xs"><TextInput label="Razão social" value={novaEmpresa.legal_name} onChange={(e) => setNovaEmpresa({ ...novaEmpresa, legal_name: e.currentTarget.value })} /><TextInput label="Nome fantasia" value={novaEmpresa.trade_name} onChange={(e) => setNovaEmpresa({ ...novaEmpresa, trade_name: e.currentTarget.value })} /><TextInput label="CNPJ" value={novaEmpresa.document} onChange={(e) => setNovaEmpresa({ ...novaEmpresa, document: mascararCnpj(e.currentTarget.value) })} /><Button disabled={novaEmpresa.legal_name.trim().length < 2} loading={criarEmpresa.isPending} onClick={() => criarEmpresa.mutate(novaEmpresa, { onSuccess: () => { notifications.show({ color: 'positivo', message: 'Empresa cadastrada' }); setNovaEmpresa({ legal_name: '', trade_name: '', document: '' }); } })}>Cadastrar empresa</Button></Stack>}
      </Card></Grid.Col>
      <Grid.Col span={{ base: 12, lg: 7 }}><Card withBorder radius="md" padding="lg"><Title order={3} size="h5" mb="md">Unidades</Title><Select label="Empresa" clearable mb="md" data={(empresas.data ?? []).map((item) => ({ value: String(item.id), label: item.legal_name }))} value={companyId ? String(companyId) : null} onChange={(value) => setCompanyId(value ? Number(value) : undefined)} />
        <EstadoDaLista carregando={unidades.isPending} erro={unidades.error ?? null} vazio={(unidades.data ?? []).length === 0} mensagemVazio="Nenhuma unidade cadastrada."><Table striped verticalSpacing="xs" mb="md"><Table.Thead><Table.Tr><Table.Th>Código</Table.Th><Table.Th>Nome</Table.Th><Table.Th>Situação</Table.Th>{podeEscrever && <Table.Th>Ações</Table.Th>}</Table.Tr></Table.Thead><Table.Tbody>{(unidades.data ?? []).map((item) => <Table.Tr key={item.id}><Table.Td>{item.code}</Table.Td><Table.Td>{item.name}</Table.Td><Table.Td><Badge color={item.is_active ? 'positivo' : 'gray'} variant="light">{item.is_active ? 'Ativa' : 'Inativa'}</Badge></Table.Td>{podeEscrever && <Table.Td><Group gap={4}><ActionIcon variant="subtle" onClick={() => setUnidadeEditada(item)}><IconPencil size={16} /></ActionIcon><ActionIcon variant="subtle" color={item.is_active ? 'red' : 'positivo'} onClick={() => situacaoUnidade.mutate({ id: item.id, is_active: !item.is_active })}>{item.is_active ? <IconTrash size={16} /> : <IconPlayerPlay size={16} />}</ActionIcon></Group></Table.Td>}</Table.Tr>)}</Table.Tbody></Table></EstadoDaLista>
        {podeEscrever && <Stack gap="xs"><Group grow><TextInput label="Código" value={novaUnidade.code} onChange={(e) => setNovaUnidade({ ...novaUnidade, code: e.currentTarget.value })} /><TextInput label="Nome" value={novaUnidade.name} onChange={(e) => setNovaUnidade({ ...novaUnidade, name: e.currentTarget.value })} /></Group><Button disabled={!companyId || !novaUnidade.code || novaUnidade.name.length < 2} loading={criarUnidade.isPending} onClick={() => companyId && criarUnidade.mutate({ company_id: companyId, ...novaUnidade }, { onSuccess: () => setNovaUnidade({ code: '', name: '' }) })}>Cadastrar unidade</Button></Stack>}
      </Card></Grid.Col>
    </Grid>
    <Modal opened={empresaEditada !== null} onClose={() => setEmpresaEditada(null)} title="Editar empresa" centered><Stack><TextInput label="Razão social" value={empresaEditada?.legal_name ?? ''} onChange={(e) => setEmpresaEditada((item) => item ? { ...item, legal_name: e.currentTarget.value } : null)} /><TextInput label="Nome fantasia" value={empresaEditada?.trade_name ?? ''} onChange={(e) => setEmpresaEditada((item) => item ? { ...item, trade_name: e.currentTarget.value } : null)} /><Group justify="flex-end"><Button variant="default" onClick={() => setEmpresaEditada(null)}>Cancelar</Button><Button onClick={() => empresaEditada && atualizarEmpresa.mutate({ id: empresaEditada.id, legal_name: empresaEditada.legal_name, trade_name: empresaEditada.trade_name }, { onSuccess: () => setEmpresaEditada(null) })}>Salvar</Button></Group></Stack></Modal>
    <Modal opened={unidadeEditada !== null} onClose={() => setUnidadeEditada(null)} title="Editar unidade" centered><Stack><TextInput label="Código" value={unidadeEditada?.code ?? ''} onChange={(e) => setUnidadeEditada((item) => item ? { ...item, code: e.currentTarget.value } : null)} /><TextInput label="Nome" value={unidadeEditada?.name ?? ''} onChange={(e) => setUnidadeEditada((item) => item ? { ...item, name: e.currentTarget.value } : null)} /><Group justify="flex-end"><Button variant="default" onClick={() => setUnidadeEditada(null)}>Cancelar</Button><Button onClick={() => unidadeEditada && atualizarUnidade.mutate({ id: unidadeEditada.id, code: unidadeEditada.code, name: unidadeEditada.name }, { onSuccess: () => setUnidadeEditada(null) })}>Salvar</Button></Group></Stack></Modal>
  </Stack>;
}
