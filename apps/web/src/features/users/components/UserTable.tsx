import { ActionIcon, Badge, Group, Table, Text, Tooltip } from '@mantine/core';
import { IconKey, IconPencil, IconPlayerPlay, IconTrash } from '@tabler/icons-react';

import type { SystemUser } from '@/features/users/types';

interface Props {
  users: SystemUser[]; currentUserId?: number;
  onEdit: (user: SystemUser) => void; onStatus: (user: SystemUser) => void; onResetPassword: (user: SystemUser) => void;
}

export function UserTable({ users, currentUserId, onEdit, onStatus, onResetPassword }: Props) {
  return <Table.ScrollContainer minWidth={820}><Table striped highlightOnHover verticalSpacing="sm">
    <Table.Thead><Table.Tr><Table.Th>Nome</Table.Th><Table.Th>E-mail</Table.Th><Table.Th>Perfis de acesso</Table.Th><Table.Th>Situação</Table.Th><Table.Th>Ações</Table.Th></Table.Tr></Table.Thead>
    <Table.Tbody>{users.map((user) => <Table.Tr key={user.id}>
      <Table.Td><Text size="sm" fw={500}>{user.full_name}</Text></Table.Td><Table.Td><Text size="sm">{user.email}</Text></Table.Td>
      <Table.Td><Group gap={4}>{user.roles.map((role) => <Badge key={role} variant="light">{role}</Badge>)}</Group></Table.Td>
      <Table.Td><Badge color={user.is_active ? 'positivo' : 'gray'} variant="light">{user.is_active ? 'Ativo' : 'Inativo'}</Badge></Table.Td>
      <Table.Td><Group gap={4} wrap="nowrap">
        <Tooltip label="Editar cadastro e perfis"><ActionIcon variant="subtle" aria-label={`Editar ${user.full_name}`} onClick={() => onEdit(user)}><IconPencil size={16} /></ActionIcon></Tooltip>
        <Tooltip label="Redefinir senha"><ActionIcon variant="subtle" aria-label={`Redefinir senha de ${user.full_name}`} onClick={() => onResetPassword(user)}><IconKey size={16} /></ActionIcon></Tooltip>
        <Tooltip label={user.is_active ? 'Inativar usuário' : 'Reativar usuário'}><ActionIcon variant="subtle" color={user.is_active ? 'red' : 'positivo'} disabled={user.id === currentUserId && user.is_active} aria-label={`${user.is_active ? 'Inativar' : 'Reativar'} ${user.full_name}`} onClick={() => onStatus(user)}>{user.is_active ? <IconTrash size={16} /> : <IconPlayerPlay size={16} />}</ActionIcon></Tooltip>
      </Group></Table.Td>
    </Table.Tr>)}</Table.Tbody>
  </Table></Table.ScrollContainer>;
}
