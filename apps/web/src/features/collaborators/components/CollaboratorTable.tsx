import { ActionIcon, Badge, Group, Table, Text, Tooltip, UnstyledButton } from '@mantine/core';
import { IconBuildingBank, IconPencil, IconTrash } from '@tabler/icons-react';
import { rotuloDoPapel, type Collaborator } from '@/shared/types/organization';

interface Props { colaboradores: Collaborator[]; podeVerPii: boolean; podeEditar: boolean; onEditar: (item: Collaborator) => void; onInativar: (item: Collaborator) => void; onFuncoes: (item: Collaborator) => void; onContas: (item: Collaborator) => void }

export function CollaboratorTable({ colaboradores, podeVerPii, podeEditar, onEditar, onInativar, onFuncoes, onContas }: Props) {
  return <Table.ScrollContainer minWidth={780}><Table striped highlightOnHover verticalSpacing="sm">
    <Table.Thead><Table.Tr><Table.Th>Nome</Table.Th><Table.Th>{podeVerPii ? 'Documento' : 'Documento (parcial)'}</Table.Th><Table.Th>Funções vigentes</Table.Th><Table.Th>Regime</Table.Th><Table.Th>Acesso</Table.Th><Table.Th>Situação</Table.Th>{podeEditar && <Table.Th>Ações</Table.Th>}</Table.Tr></Table.Thead>
    <Table.Tbody>{colaboradores.map((item) => <Table.Tr key={item.id}>
      <Table.Td><Text size="sm" fw={500}>{item.full_name}</Text></Table.Td><Table.Td><Text size="sm" ff="monospace">{item.document}</Text></Table.Td>
      <Table.Td><Group gap={4}><Tooltip label="Ver e alterar funções"><UnstyledButton aria-label={`Funções de ${item.full_name}`} onClick={() => onFuncoes(item)}><Group gap={4}>{item.roles.length === 0 ? <Text size="xs" c="dimmed">sem função vigente</Text> : item.roles.map((role) => <Badge key={role} size="sm" variant="light" style={{ cursor: 'pointer' }}>{rotuloDoPapel(role)}</Badge>)}</Group></UnstyledButton></Tooltip></Group></Table.Td>
      <Table.Td><Badge size="sm" variant="default">{item.tax_regime}</Badge></Table.Td>
      <Table.Td>{item.user_id ? <Badge size="sm" variant="light" color="blue">Com acesso</Badge> : <Text size="xs" c="dimmed">sem conta</Text>}</Table.Td>
      <Table.Td><Badge size="sm" color={item.is_active ? 'positivo' : 'gray'} variant="light">{item.is_active ? 'Ativo' : 'Inativo'}</Badge></Table.Td>
      {podeEditar && <Table.Td><Group gap={4} wrap="nowrap"><Tooltip label="Editar cadastro"><ActionIcon variant="subtle" aria-label={`Editar ${item.full_name}`} onClick={() => onEditar(item)}><IconPencil size={16} /></ActionIcon></Tooltip>{podeVerPii && <Tooltip label="Contas bancárias"><ActionIcon variant="subtle" aria-label={`Contas de ${item.full_name}`} onClick={() => onContas(item)}><IconBuildingBank size={16} /></ActionIcon></Tooltip>}<Tooltip label="Inativar colaborador"><ActionIcon variant="subtle" color="red" disabled={!item.is_active} aria-label={`Inativar ${item.full_name}`} onClick={() => onInativar(item)}><IconTrash size={16} /></ActionIcon></Tooltip></Group></Table.Td>}
    </Table.Tr>)}</Table.Tbody>
  </Table></Table.ScrollContainer>;
}
