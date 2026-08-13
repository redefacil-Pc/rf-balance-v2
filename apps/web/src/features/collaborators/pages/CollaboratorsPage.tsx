import { Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconPlus } from '@tabler/icons-react';
import { useCallback } from 'react';
import { useState } from 'react';

import { useAuth } from '@/app/providers/AuthProvider';
import { CollaboratorFilters } from '@/features/collaborators/components/CollaboratorFilters';
import { CollaboratorDeactivateModal } from '@/features/collaborators/components/CollaboratorDeactivateModal';
import { CollaboratorBankAccountsModal } from '@/features/collaborators/components/CollaboratorBankAccountsModal';
import { CollaboratorEditModal } from '@/features/collaborators/components/CollaboratorEditModal';
import { CollaboratorFormModal } from '@/features/collaborators/components/CollaboratorFormModal';
import { CollaboratorFunctionsModal } from '@/features/collaborators/components/CollaboratorFunctionsModal';
import { CollaboratorTable } from '@/features/collaborators/components/CollaboratorTable';
import {
  useCollaborators,
  type CollaboratorFilters as Filtros,
} from '@/features/collaborators/queries/useCollaborators';
import { EstadoDaLista } from '@/shared/components/EstadoDaLista';
import { useFiltrosNaUrl } from '@/shared/hooks/useFiltrosNaUrl';
import type { Collaborator } from '@/shared/types/organization';

function lerFiltros(params: URLSearchParams): Filtros {
  const numero = (chave: string) => {
    const valor = params.get(chave);
    return valor ? Number(valor) : undefined;
  };
  const ativo = params.get('only_active');

  return {
    company_id: numero('company_id'),
    unit_id: numero('unit_id'),
    role: params.get('role') ?? undefined,
    tax_regime: params.get('tax_regime') ?? undefined,
    only_active: ativo === null ? undefined : ativo === 'true',
    name: params.get('name') ?? undefined,
  };
}

export function CollaboratorsPage() {
  const { pode } = useAuth();
  const [filtros, aplicarFiltros] = useFiltrosNaUrl<Filtros>(useCallback(lerFiltros, []));
  const [modalAberto, modal] = useDisclosure(false);
  const [editing, setEditing] = useState<Collaborator | null>(null);
  const [deactivating, setDeactivating] = useState<Collaborator | null>(null);
  const [managingFunctions, setManagingFunctions] = useState<Collaborator | null>(null);
  const [managingAccounts, setManagingAccounts] = useState<Collaborator | null>(null);

  const consulta = useCollaborators(filtros);
  const colaboradores = (consulta.data?.pages ?? []).flatMap((pagina) => pagina.items);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2} size="h3">
            Colaboradores
          </Title>
          <Text c="dimmed" size="sm">
            Cadastro operacional e financeiro. Funções têm vigência — o histórico é preservado.
          </Text>
        </div>

        {pode('collaborators:write') && (
          <Button leftSection={<IconPlus size={16} />} onClick={modal.open}>
            Novo colaborador
          </Button>
        )}
      </Group>

      <Card withBorder radius="md" padding="md">
        <CollaboratorFilters valor={filtros} onChange={aplicarFiltros} />
      </Card>

      <Card withBorder radius="md" padding={0}>
        <EstadoDaLista
          carregando={consulta.isPending}
          erro={consulta.error ?? null}
          vazio={colaboradores.length === 0}
          onTentarNovamente={() => void consulta.refetch()}
          mensagemVazio="Nenhum colaborador encontrado. Ajuste os filtros ou cadastre o primeiro."
        >
          <CollaboratorTable
            colaboradores={colaboradores}
            podeVerPii={pode('collaborators:read_pii')}
            podeEditar={pode('collaborators:write')}
            onEditar={setEditing}
            onInativar={setDeactivating}
            onFuncoes={setManagingFunctions}
            onContas={setManagingAccounts}
          />
        </EstadoDaLista>
      </Card>

      {consulta.hasNextPage && (
        <Group justify="center">
          <Button
            variant="default"
            onClick={() => void consulta.fetchNextPage()}
            loading={consulta.isFetchingNextPage}
          >
            Carregar mais
          </Button>
        </Group>
      )}

      {colaboradores.length > 0 && (
        <Text size="xs" c="dimmed" ta="center">
          {colaboradores.length} colaborador(es) carregado(s)
          {consulta.hasNextPage ? ' — há mais registros' : ''}
        </Text>
      )}

      <CollaboratorFormModal aberto={modalAberto} onFechar={modal.close} />
      <CollaboratorEditModal collaborator={editing} onClose={() => setEditing(null)} />
      <CollaboratorDeactivateModal collaborator={deactivating} onClose={() => setDeactivating(null)} />
      <CollaboratorFunctionsModal
        colaborador={managingFunctions}
        podeEscrever={pode('collaborators:write')}
        onFechar={() => setManagingFunctions(null)}
      />
      <CollaboratorBankAccountsModal collaborator={managingAccounts} onClose={() => setManagingAccounts(null)} />
    </Stack>
  );
}
