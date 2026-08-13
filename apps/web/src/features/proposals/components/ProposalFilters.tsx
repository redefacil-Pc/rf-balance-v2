import { Button, Group, Select, TextInput } from '@mantine/core';
import { IconSearch, IconX } from '@tabler/icons-react';

import { useColaboradoresPorPapel } from '@/features/proposals/queries/useColaboradoresPorPapel';
import type { ProposalFilters as Filtros } from '@/features/proposals/queries/useProposals';
import { ROTULO_DO_STATUS, STATUS_DA_PROPOSTA } from '@/shared/types/commercial';

interface Props {
  valor: Filtros;
  onChange: (filtros: Filtros) => void;
}

/** Os filtros da seção 7.4. O estado vive na URL, não aqui. */
export function ProposalFilters({ valor, onChange }: Props) {
  const consultores = useColaboradoresPorPapel('CONSULTOR');

  const alterar = (parcial: Filtros) => onChange({ ...valor, ...parcial });

  return (
    <Group align="flex-end" gap="sm" wrap="wrap">
      <TextInput
        label="Cliente"
        placeholder="Começa com..."
        leftSection={<IconSearch size={16} />}
        value={valor.customer_name ?? ''}
        onChange={(evento) => alterar({ customer_name: evento.currentTarget.value || undefined })}
        w={220}
      />

      <TextInput
        label="Redmine"
        placeholder="ID externo"
        value={valor.external_id ?? ''}
        onChange={(evento) => alterar({ external_id: evento.currentTarget.value || undefined })}
        w={150}
      />

      <Select
        label="Consultor"
        placeholder="Todos"
        clearable
        searchable
        w={220}
        data={(consultores.data?.items ?? []).map((c) => ({
          value: String(c.id),
          label: c.full_name,
        }))}
        value={valor.consultant_id ? String(valor.consultant_id) : null}
        onChange={(v) => alterar({ consultant_id: v ? Number(v) : undefined })}
      />

      <Select
        label="Situação"
        placeholder="Todas"
        clearable
        w={180}
        data={STATUS_DA_PROPOSTA.map((status) => ({
          value: status,
          label: ROTULO_DO_STATUS[status],
        }))}
        value={valor.status ?? null}
        onChange={(v) => alterar({ status: (v as Filtros['status']) ?? undefined })}
      />

      <TextInput
        label="De"
        type="date"
        w={160}
        value={valor.business_date_from ?? ''}
        onChange={(evento) =>
          alterar({ business_date_from: evento.currentTarget.value || undefined })
        }
      />

      <TextInput
        label="Até"
        type="date"
        w={160}
        value={valor.business_date_to ?? ''}
        onChange={(evento) =>
          alterar({ business_date_to: evento.currentTarget.value || undefined })
        }
      />

      <Button
        variant="subtle"
        leftSection={<IconX size={16} />}
        onClick={() => onChange({})}
        disabled={Object.keys(valor).length === 0}
      >
        Limpar
      </Button>
    </Group>
  );
}
